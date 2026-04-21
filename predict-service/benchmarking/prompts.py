from __future__ import annotations

import json
from typing import Any

from .schemas import ArtifactInputs

PROMPT_CONTEXT_START = "BEGIN_CONTEXT_JSON"
PROMPT_CONTEXT_END = "END_CONTEXT_JSON"

ARM_INSTRUCTIONS = {
    "A": (
        "Chart-to-text baseline. State the strongest directly grounded findings with "
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
        context["asset_json_payloads"] = inputs.json_payloads
        context["asset_text_payloads"] = inputs.text_payloads
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
        payload["summary_text"] = inputs.text_payloads
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
    context = build_prompt_context(inputs=inputs, arm=arm, condition=condition)
    arm_instruction = ARM_INSTRUCTIONS.get(arm, ARM_INSTRUCTIONS["A"])

    return (
        "You are generating artifact-grounded ML explanations for offline benchmarking.\n"
        "Return strict JSON with keys: artifact_id, arm, input_condition, "
        "explanation_short, explanation_full, claims.\n"
        "Each claim must include: claim_id, claim_text, claim_type, span_category, "
        "is_numeric, requires_grounding_from, confidence.\n"
        "You may add optional normalization fields such as subject, metric, value, "
        "ordered_items, feature_count, and hedged.\n"
        "Rules:\n"
        "- Table/json evidence outranks chart evidence.\n"
        "- Chart evidence outranks summary text.\n"
        "- Omission is better than speculation.\n"
        "- Unsupported claims are worse than short answers.\n"
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
