from __future__ import annotations

import json
from typing import Any

from .schemas import ArtifactInputs, CANONICAL_CLAIM_TYPES

PROMPT_CONTEXT_START = "BEGIN_CONTEXT_JSON"
PROMPT_CONTEXT_END = "END_CONTEXT_JSON"
CLAIM_EXTRACTION_CONTEXT_START = "BEGIN_CLAIM_EXTRACTION_JSON"
CLAIM_EXTRACTION_CONTEXT_END = "END_CLAIM_EXTRACTION_JSON"

ARM_INSTRUCTIONS = {
    "A": (
        "Direct chart-to-text. State the strongest directly grounded findings with "
        "minimal interpretation."
    ),
    "B": (
        "Layered explanation. Present observations first, then interpretation, then a "
        "brief caveat about uncertainty or scope."
    ),
    "C": (
        "Generate, self-check, and revise. Remove unsupported claims before returning "
        "the final explanation."
    ),
    "D": (
        "Scaffold only. Keep the explanation conservative and explicitly avoid dense "
        "reasoning that is not directly grounded."
    ),
}


def _truncate_text(value: Any, max_chars: int = 2400) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def _compact_text_payloads(text_payloads: dict[str, Any]) -> dict[str, str]:
    compact: dict[str, str] = {}
    for key, value in text_payloads.items():
        clipped = _truncate_text(value)
        if clipped:
            compact[str(key)] = clipped
    return compact


def _compact_summary_payload(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}

    compact: dict[str, Any] = {}
    for key in (
        "report_id",
        "model_name",
        "model_label",
        "selected_model_metrics",
        "benchmark_models",
        "selected_model_features",
        "selected_sheet",
        "data_shape",
    ):
        value = summary.get(key)
        if value not in (None, "", [], {}):
            compact[key] = value

    benchmark_summary = summary.get("benchmark_summary")
    if isinstance(benchmark_summary, dict):
        compact["benchmark_summary"] = {
            key: benchmark_summary.get(key)
            for key in ("best_overall", "selected_explanations")
            if benchmark_summary.get(key) not in (None, "", [], {})
        }

    return compact


def _compact_json_payloads(json_payloads: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in json_payloads.items():
        normalized_key = str(key)
        if normalized_key == "summary.json":
            summary_payload = _compact_summary_payload(value)
            if summary_payload:
                compact[normalized_key] = summary_payload
            continue
        compact[normalized_key] = value
    return compact


def _artifact_context(inputs: ArtifactInputs) -> dict[str, Any]:
    record = inputs.record
    context: dict[str, Any] = {
        "artifact_id": record.artifact_id,
        "artifact_type": record.artifact_type,
        "primary_entities": record.primary_entities,
    }

    if record.asset_key and inputs.asset_payload:
        asset_payload = inputs.asset_payload
        context["chart_asset"] = {
            "asset_key": record.asset_key,
            "asset_title": record.asset_title,
            "asset_family": record.asset_family,
            "result_text": asset_payload.get("result_text"),
            "evidence": asset_payload.get("evidence"),
            "source_files": record.source_files,
        }
        context["asset_tables"] = inputs.tables
        context["asset_json_payloads"] = _compact_json_payloads(inputs.json_payloads)
        context["asset_text_payloads"] = _compact_text_payloads(inputs.text_payloads)
    elif record.artifact_type == "model_comparison/main":
        context["table_model_comparison"] = inputs.tables.get("table_model_comparison.csv", [])
        summary = inputs.json_payloads.get("summary.json", {})
        if isinstance(summary, dict):
            context["summary"] = {
                "model_label": summary.get("model_label"),
                "selected_model_metrics": summary.get("selected_model_metrics"),
                "benchmark_models": summary.get("benchmark_models"),
            }
    elif record.artifact_type == "incremental_feature_analysis/main":
        context["table1_incremental_results"] = inputs.tables.get(
            "table1_incremental_results.csv",
            [],
        )
    elif record.artifact_type == "feature_ranking/gra":
        context["gra_ranking"] = inputs.json_payloads.get("gra_ranking.json", [])

    return context


def build_prompt_context(inputs: ArtifactInputs, arm: str, condition: str) -> dict[str, Any]:
    payload = _artifact_context(inputs)
    payload["arm"] = arm
    payload["input_condition"] = condition
    payload["source_priority"] = ["table/json", "chart", "summary_text"]

    if condition in {"image_table", "image_table_summary", "image_only"}:
        payload["chart_files"] = inputs.chart_files
    else:
        payload["chart_files"] = []

    if condition in {"image_table_summary"}:
        payload["summary_text"] = _compact_text_payloads(inputs.text_payloads)
    else:
        payload["summary_text"] = {}

    if condition == "image_only":
        payload.pop("summary", None)
        payload.pop("table_model_comparison", None)
        payload.pop("table1_incremental_results", None)
        payload.pop("gra_ranking", None)
        payload.pop("asset_tables", None)
        payload.pop("asset_json_payloads", None)

    return payload


def build_generation_prompt(inputs: ArtifactInputs, arm: str, condition: str) -> str:
    return build_explanation_prompt(inputs=inputs, arm=arm, condition=condition)


def build_explanation_prompt(inputs: ArtifactInputs, arm: str, condition: str) -> str:
    context = build_prompt_context(inputs=inputs, arm=arm, condition=condition)
    arm_instruction = ARM_INSTRUCTIONS.get(arm, ARM_INSTRUCTIONS["A"])

    return (
        "You are generating artifact-grounded ML explanations for offline benchmarking.\n"
        "Return strict JSON with keys: artifact_id, arm, input_condition, "
        "explanation_short, explanation_full.\n"
        "Rules:\n"
        "- Table/json evidence outranks chart evidence.\n"
        "- Chart evidence outranks summary text.\n"
        "- Omission is better than speculation.\n"
        f"- Arm instruction: {arm_instruction}\n"
        f"{PROMPT_CONTEXT_START}\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n"
        f"{PROMPT_CONTEXT_END}\n"
    )


def extract_prompt_context(prompt: str) -> dict[str, Any]:
    start_index = prompt.find(PROMPT_CONTEXT_START)
    end_index = prompt.find(PROMPT_CONTEXT_END)
    if start_index == -1 or end_index == -1:
        raise ValueError("Prompt does not contain context markers.")
    payload = prompt[start_index + len(PROMPT_CONTEXT_START) : end_index].strip()
    return json.loads(payload)


def build_claim_extraction_prompt(
    *,
    artifact_id: str,
    arm: str,
    input_condition: str,
    explanation_short: str,
    explanation_full: str,
    primary_entities: list[str],
    variable_catalog: list[dict[str, Any]],
) -> str:
    payload = {
        "artifact_id": artifact_id,
        "arm": arm,
        "input_condition": input_condition,
        "primary_entities": primary_entities,
        "allowed_variables": variable_catalog,
        "explanation": {
            "explanation_short": explanation_short,
            "explanation_full": explanation_full,
        },
    }
    return (
        "You are extracting standardized benchmark variables from one ML explanation.\n"
        "Return strict JSON with keys: artifact_id, arm, input_condition, claims.\n"
        "Each claim must include: claim_id, claim_text, claim_type, span_category, "
        "is_numeric, requires_grounding_from, confidence, source_variable_id.\n"
        f"Allowed claim_type values: {', '.join(CANONICAL_CLAIM_TYPES)}.\n"
        "Rules:\n"
        "- Extract only variables listed in allowed_variables.\n"
        "- Use the exact source_variable_id from allowed_variables for every extracted claim.\n"
        "- Emit a claim only when the explanation explicitly states it or states an unambiguous paraphrase.\n"
        "- Do not invent values from the variable catalog.\n"
        "- If a variable is absent from the explanation, omit it.\n"
        "- Prefer omission over guesswork.\n"
        f"{CLAIM_EXTRACTION_CONTEXT_START}\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
        f"{CLAIM_EXTRACTION_CONTEXT_END}\n"
    )


def extract_claim_extraction_context(prompt: str) -> dict[str, Any]:
    start_index = prompt.find(CLAIM_EXTRACTION_CONTEXT_START)
    end_index = prompt.find(CLAIM_EXTRACTION_CONTEXT_END)
    if start_index == -1 or end_index == -1:
        raise ValueError("Claim extraction prompt does not contain context markers.")
    payload = prompt[start_index + len(CLAIM_EXTRACTION_CONTEXT_START) : end_index].strip()
    return json.loads(payload)
