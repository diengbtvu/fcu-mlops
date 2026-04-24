from __future__ import annotations

import json
from typing import Any

from .schemas import ArtifactInputs, CANONICAL_CLAIM_TYPES

PROMPT_CONTEXT_START = "BEGIN_CONTEXT_JSON"
PROMPT_CONTEXT_END = "END_CONTEXT_JSON"
CLAIM_EXTRACTION_CONTEXT_START = "BEGIN_CLAIM_EXTRACTION_JSON"
CLAIM_EXTRACTION_CONTEXT_END = "END_CLAIM_EXTRACTION_JSON"

JSON_ONLY_CONTRACT = (
    "JSON OUTPUT CONTRACT:\n"
    "- Return exactly one JSON object and nothing else.\n"
    "- The first character must be { and the last character must be }.\n"
    "- Do not write analysis, reasoning, markdown, headings, or commentary.\n"
    "- Do not put the answer in hidden thinking; the final assistant content must be the JSON object.\n"
)

SEMANTIC_LEVEL_PREFIXES: dict[str, str] = {
    "L1": (
        "SEMANTIC LEVEL: L1 - Structural description only.\n"
        "Describe ONLY the chart/table structure: artifact type, chart type, axis labels, "
        "column names, entity names, metric names, value ranges, units, and scale.\n"
        "Do NOT include comparisons, trends, rankings, best/worst judgments, or takeaways."
    ),
    "L2L3": (
        "SEMANTIC LEVEL: L2/L3 - Analytical description only.\n"
        "Describe ONLY the analytical insights: best/worst entities, rankings, trends, patterns, "
        "extremes, comparisons, plateaus, caveats, and takeaways.\n"
        "Do NOT repeat structural details like chart type, axis labels, or column names."
    ),
    "L1L2L3": (
        "SEMANTIC LEVEL: L1+L2/L3 - Full layered explanation.\n"
        "Briefly describe the structure first, then provide the main analytical findings, "
        "comparisons, trends, extremes, and takeaways."
    ),
}

ARM_INSTRUCTIONS = {
    "A": (
        "Direct chart-to-text. State the strongest directly grounded findings with "
        "minimal interpretation."
    ),
    "B": (
        "Layered explanation with semantic level control. Follow the SEMANTIC LEVEL "
        "prefix to determine what content to include."
    ),
    "C": (
        "Multi-stage draft, validate, and correct pipeline. Use a validator pass and "
        "a separate correction pass rather than a single self-check instruction."
    ),
    "D": (
        "Scaffold only. Keep the explanation conservative and explicitly avoid dense "
        "reasoning that is not directly grounded."
    ),
}

ARM_C_DRAFT_INSTRUCTION = (
    "Draft a grounded explanation from the artifact context. "
    "Do not claim that you validated or corrected anything. "
    "State the strongest evidence-backed findings only."
)

ARM_C_VALIDATOR_INSTRUCTION = (
    "Act as an adversarial evidence validator, not as a friendly reviewer. "
    "Validate each structured claim against the evidence packet only. "
    "Do not trust extracted source_variable_id values. For every claim, decide whether it is "
    "supported, partially supported, contradicted, or unverifiable by independently comparing "
    "entities, predicates, rankings, objects, and numeric values. Recommend keep only for fully "
    "grounded claims; otherwise recommend edit or drop and provide a short grounded fact summary "
    "that the corrector can use."
)

ARM_C_CORRECTOR_INSTRUCTION = (
    "Revise the draft explanation using the validator records and validated facts. "
    "Keep supported content, fix contradicted content, drop unverifiable content, "
    "and make the smallest factual edits that produce a faithful final explanation."
)


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


def build_prompt_context(
    inputs: ArtifactInputs,
    arm: str,
    condition: str,
    semantic_level: str | None = None,
) -> dict[str, Any]:
    payload = _artifact_context(inputs)
    payload["arm"] = arm
    payload["input_condition"] = condition
    if semantic_level:
        payload["semantic_level"] = semantic_level
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


def build_generation_prompt(
    inputs: ArtifactInputs,
    arm: str,
    condition: str,
    semantic_level: str | None = None,
) -> str:
    return build_explanation_prompt(
        inputs=inputs,
        arm=arm,
        condition=condition,
        semantic_level=semantic_level,
    )


def build_explanation_prompt(
    inputs: ArtifactInputs,
    arm: str,
    condition: str,
    semantic_level: str | None = None,
) -> str:
    context = build_prompt_context(
        inputs=inputs,
        arm=arm,
        condition=condition,
        semantic_level=semantic_level,
    )
    arm_instruction = ARM_INSTRUCTIONS.get(arm, ARM_INSTRUCTIONS["A"])
    prefix_block = ""
    if arm == "B" and semantic_level in SEMANTIC_LEVEL_PREFIXES:
        prefix_block = f"{SEMANTIC_LEVEL_PREFIXES[semantic_level]}\n"

    return (
        "You are generating artifact-grounded ML explanations for offline benchmarking.\n"
        "Return strict JSON with keys: artifact_id, arm, input_condition, "
        "explanation_short, explanation_full, semantic_level.\n"
        f"{prefix_block}"
        "Rules:\n"
        "- Table/json evidence outranks chart evidence.\n"
        "- Chart evidence outranks summary text.\n"
        "- Omission is better than speculation.\n"
        f"- Arm instruction: {arm_instruction}\n"
        f"{PROMPT_CONTEXT_START}\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n"
        f"{PROMPT_CONTEXT_END}\n"
    )


def build_arm_c_draft_prompt(
    inputs: ArtifactInputs,
    condition: str,
) -> str:
    context = build_prompt_context(
        inputs=inputs,
        arm="C",
        condition=condition,
        semantic_level=None,
    )
    context["arm_c_stage"] = "draft"
    return (
        "You are generating the draft stage of a multi-step factual correction pipeline "
        "for artifact-grounded ML explanations.\n"
        f"{JSON_ONLY_CONTRACT}"
        "Return strict JSON with keys: artifact_id, arm, input_condition, "
        "explanation_short, explanation_full, semantic_level.\n"
        "Rules:\n"
        "- This is only the draft stage.\n"
        "- Do not mention self-checking, validation, or correction in the output.\n"
        "- Table/json evidence outranks chart evidence.\n"
        "- Chart evidence outranks summary text.\n"
        "- Omission is better than speculation.\n"
        f"- Arm C draft instruction: {ARM_C_DRAFT_INSTRUCTION}\n"
        f"{PROMPT_CONTEXT_START}\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n"
        f"{PROMPT_CONTEXT_END}\n"
    )


def build_arm_c_corrector_prompt(
    *,
    artifact_id: str,
    input_condition: str,
    evidence_packet: dict[str, Any],
    draft_explanation_short: str,
    draft_explanation_full: str,
    draft_claims: list[dict[str, Any]] | None = None,
    validation_records: list[dict[str, Any]] | None = None,
) -> str:
    payload = {
        "artifact_id": artifact_id,
        "arm": "C",
        "input_condition": input_condition,
        "semantic_level": None,
        "arm_c_stage": "corrector",
        "evidence_packet": evidence_packet,
        "draft_explanation": {
            "explanation_short": draft_explanation_short,
            "explanation_full": draft_explanation_full,
        },
        "draft_claims": draft_claims or [],
        "validation_records": validation_records or [],
    }
    return (
        "You are the corrector stage of a multi-step factual correction pipeline for "
        "artifact-grounded ML explanations.\n"
        f"{JSON_ONLY_CONTRACT}"
        "Return strict JSON with keys: artifact_id, arm, input_condition, "
        "explanation_short, explanation_full, semantic_level, claims.\n"
        "Rules:\n"
        "- Use validation_records and evidence_packet as the source of truth.\n"
        "- Treat validation_records as the validator output; use grounded_fact_summary when editing.\n"
        "- Keep supported statements whenever possible.\n"
        "- Revise contradicted statements to match the validated facts.\n"
        "- Drop unverifiable statements when no grounded replacement exists.\n"
        "- Make minimal factual edits rather than rewriting everything.\n"
        "- Do not introduce facts outside the evidence_packet.\n"
        "- Return structured claims that match the corrected explanation.\n"
        "- Use only source_variable_id values that appear in evidence_packet.allowed_variables.\n"
        "- If a draft claim is dropped, omit it from claims.\n"
        f"- Arm C corrector instruction: {ARM_C_CORRECTOR_INSTRUCTION}\n"
        f"{PROMPT_CONTEXT_START}\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
        f"{PROMPT_CONTEXT_END}\n"
    )


def build_arm_c_validator_prompt(
    *,
    artifact_id: str,
    input_condition: str,
    evidence_packet: dict[str, Any],
    explanation_short: str,
    explanation_full: str,
    claims: list[dict[str, Any]],
    validation_pass: str,
) -> str:
    def _norm(value: Any) -> str:
        return str(value or "").strip().lower()

    def _compact_fact(fact: dict[str, Any]) -> dict[str, Any]:
        return {
            "fact_id": fact.get("fact_id"),
            "fact_type": fact.get("fact_type"),
            "subject": fact.get("subject"),
            "predicate": fact.get("predicate"),
            "object": fact.get("object"),
            "value": fact.get("value"),
            "unit": fact.get("unit"),
            "semantic_level": fact.get("semantic_level"),
            "evidence": fact.get("evidence"),
        }

    facts = [
        dict(item)
        for item in list(evidence_packet.get("validated_facts") or [])
        if isinstance(item, dict)
    ]

    validation_targets: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        source_variable_id = str(claim.get("source_variable_id") or "").strip()
        claim_type = _norm(claim.get("claim_type"))
        claim_subject = _norm(claim.get("subject"))
        claim_metric = _norm(claim.get("metric") or claim.get("predicate"))
        claim_object = _norm(claim.get("object"))
        claim_predicate = _norm(claim.get("predicate"))

        candidates: list[dict[str, Any]] = []
        seen_fact_ids: set[str] = set()
        for fact in facts:
            fact_id = str(fact.get("fact_id") or "").strip()
            if not fact_id or fact_id in seen_fact_ids:
                continue
            fact_type = _norm(fact.get("fact_type"))
            fact_subject = _norm(fact.get("subject"))
            fact_predicate = _norm(fact.get("predicate"))
            fact_object = _norm(fact.get("object"))
            exact_source_match = source_variable_id and fact_id == source_variable_id
            type_subject_metric_match = (
                claim_type
                and fact_type == claim_type
                and (not claim_subject or fact_subject == claim_subject)
                and (not claim_metric or fact_predicate == claim_metric)
            )
            subject_metric_match = (
                claim_subject
                and fact_subject == claim_subject
                and claim_metric
                and fact_predicate == claim_metric
            )
            object_match = claim_object and fact_object == claim_object
            predicate_match = claim_predicate and fact_predicate == claim_predicate
            if exact_source_match or type_subject_metric_match or subject_metric_match or object_match or predicate_match:
                candidates.append(_compact_fact(fact))
                seen_fact_ids.add(fact_id)
            if len(candidates) >= 8:
                break

        validation_targets.append(
            {
                "claim_id": claim.get("claim_id"),
                "claim_type": claim.get("claim_type"),
                "claim_text": claim.get("claim_text"),
                "source_variable_id": claim.get("source_variable_id"),
                "subject": claim.get("subject"),
                "predicate": claim.get("predicate"),
                "object": claim.get("object"),
                "metric": claim.get("metric"),
                "value": claim.get("value"),
                "ordered_items": claim.get("ordered_items"),
                "feature_count": claim.get("feature_count"),
                "candidate_facts": candidates,
            }
        )

    payload = {
        "artifact_id": artifact_id,
        "arm": "C",
        "input_condition": input_condition,
        "semantic_level": None,
        "arm_c_stage": "validator",
        "validation_pass": validation_pass,
        "evidence_packet": evidence_packet,
        "explanation": {
            "explanation_short": explanation_short,
            "explanation_full": explanation_full,
        },
        "claims": claims,
        "validation_targets": validation_targets,
    }
    return (
        "You are the validator stage of a multi-step factual correction pipeline for "
        "artifact-grounded ML explanations.\n"
        f"{JSON_ONLY_CONTRACT}"
        "Return strict JSON with keys: artifact_id, arm, input_condition, validation_records.\n"
        "STRICT VALIDATOR MODE:\n"
        "- Your job is to find factual errors before the corrector stage. Do not rubber-stamp the draft.\n"
        "- Do NOT trust claim.source_variable_id, claim_type, or confidence; these may be wrong.\n"
        "- For each claim, compare the claim_text and structured fields against validation_targets.candidate_facts first, then evidence_packet.validated_facts.\n"
        "- A claim is supported only when the subject/entity, metric/predicate, object/ranking, and numeric value all match grounded evidence.\n"
        "- If the claim points to the wrong source_variable_id but a correct candidate fact exists, mark partially_supported or contradicted and recommended_action=edit.\n"
        "- If a numeric value differs from the grounded value beyond normal displayed rounding, mark contradicted and recommended_action=edit.\n"
        "- If only part of a multi-fact claim is grounded, mark partially_supported and recommended_action=edit.\n"
        "- If no candidate/evidence fact grounds the claim, mark unverifiable and recommended_action=drop.\n"
        "- Use keep only for claims that can be published without correction.\n"
        "Rules:\n"
        "- Validate each claim only against evidence_packet.\n"
        "- Do not assume facts that are absent from evidence_packet.\n"
        "- Use status supported, partially_supported, contradicted, or unverifiable.\n"
        "- Use recommended_action keep, edit, or drop.\n"
        "- grounded_fact_summary must be short and factual.\n"
        f"- Arm C validator instruction: {ARM_C_VALIDATOR_INSTRUCTION}\n"
        f"{PROMPT_CONTEXT_START}\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
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
    semantic_level: str | None = None,
) -> str:
    payload = {
        "artifact_id": artifact_id,
        "arm": arm,
        "input_condition": input_condition,
        "semantic_level": semantic_level,
        "primary_entities": primary_entities,
        "allowed_variables": variable_catalog,
        "explanation": {
            "explanation_short": explanation_short,
            "explanation_full": explanation_full,
        },
    }
    return (
        "You are extracting standardized benchmark variables from one ML explanation.\n"
        f"{JSON_ONLY_CONTRACT}"
        "- If no claims are present, return a valid JSON object with claims: [].\n"
        "Required top-level keys: artifact_id, arm, input_condition, semantic_level, claims.\n"
        "Each claim must include: claim_id, claim_text, claim_type, span_category, "
        "is_numeric, requires_grounding_from, confidence, source_variable_id.\n"
        f"Allowed claim_type values: {', '.join(CANONICAL_CLAIM_TYPES)}.\n"
        "Output shape:\n"
        "{\n"
        '  "artifact_id": "...",\n'
        '  "arm": "...",\n'
        '  "input_condition": "...",\n'
        '  "semantic_level": null,\n'
        '  "claims": []\n'
        "}\n"
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
