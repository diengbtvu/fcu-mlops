from __future__ import annotations

import re
from typing import Any

from .schemas import Claim, ExplanationOutput

HEDGE_PATTERN = re.compile(r"\b(about|around|approximately|roughly|nearly|almost)\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
METRIC_PATTERN = re.compile(r"\b(R2|R²|RMSE|MSE|MAE|score)\b", re.IGNORECASE)
FEATURE_COUNT_PATTERN = re.compile(r"(\d+)\s+features?", re.IGNORECASE)
ORDERING_PATTERN = re.compile(r"([A-Za-z0-9_\- ]+(?:\s*>\s*[A-Za-z0-9_\- ]+)+)")


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_metric(metric: str | None) -> str | None:
    if not metric:
        return None
    lowered = metric.strip().lower()
    return {
        "r2": "r2_score",
        "r²": "r2_score",
        "rmse": "rmse",
        "mse": "mse",
        "mae": "mae",
        "score": "gra_score",
        "gra_score": "gra_score",
    }.get(lowered, lowered)


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _infer_claim_type(claim_text: str) -> str:
    lowered = claim_text.lower()
    if "best model" in lowered:
        return "best_model"
    if "top feature" in lowered:
        return "top_feature"
    if "plateau" in lowered:
        return "plateau"
    if "best subset" in lowered or "best at" in lowered or "best with" in lowered:
        return "feature_subset_optimum"
    if " > " in claim_text or "ranking" in lowered or "ordering" in lowered:
        return "ranking"
    if "gra score" in lowered:
        return "rank_score"
    if METRIC_PATTERN.search(claim_text):
        return "metric_value"
    return "freeform"


def _parse_ordered_items(claim_text: str) -> list[str]:
    match = ORDERING_PATTERN.search(claim_text)
    if not match:
        return []
    return [item.strip() for item in match.group(1).split(">") if item.strip()]


def _extract_claim_fields(
    claim_text: str,
    claim_type: str,
) -> dict[str, Any]:
    metric_match = METRIC_PATTERN.search(claim_text)
    metric = _normalize_metric(metric_match.group(1) if metric_match else None)
    numeric_values = NUMBER_PATTERN.findall(claim_text)
    value = _as_float(numeric_values[-1]) if numeric_values else None
    feature_count_match = FEATURE_COUNT_PATTERN.search(claim_text)
    ordered_items = _parse_ordered_items(claim_text)

    fields: dict[str, Any] = {
        "metric": metric,
        "value": value,
        "ordered_items": ordered_items,
        "feature_count": int(feature_count_match.group(1)) if feature_count_match else None,
        "hedged": bool(HEDGE_PATTERN.search(claim_text)),
    }

    if claim_type == "best_model":
        match = re.search(r"([A-Za-z0-9_\-]+)\s+is the best model", claim_text, re.IGNORECASE)
        if match:
            fields["object"] = match.group(1)
    elif claim_type == "top_feature":
        match = re.search(r"([A-Za-z0-9_\-]+)\s+is the top feature", claim_text, re.IGNORECASE)
        if match:
            fields["object"] = match.group(1)
    elif claim_type in {"metric_value", "rank_score"}:
        match = re.search(r"([A-Za-z0-9_\-]+)", claim_text)
        if match:
            fields["subject"] = match.group(1)
    elif claim_type in {"feature_subset_optimum", "plateau"}:
        match = re.search(r"([A-Za-z0-9_\-]+)", claim_text)
        if match:
            fields["subject"] = match.group(1)

    return fields


def _normalize_claim(raw_claim: dict[str, Any], claim_index: int) -> Claim:
    claim_text = str(raw_claim.get("claim_text") or "").strip()
    if not claim_text:
        raise ValueError(f"Claim at index {claim_index} is missing claim_text.")

    claim_type = str(raw_claim.get("claim_type") or _infer_claim_type(claim_text)).strip()
    inferred_fields = _extract_claim_fields(claim_text, claim_type)

    metric = _normalize_metric(raw_claim.get("metric") or inferred_fields.get("metric"))
    value = raw_claim.get("value")
    if value is None:
        value = inferred_fields.get("value")
    numeric_value = _as_float(value)

    ordered_items = raw_claim.get("ordered_items") or inferred_fields.get("ordered_items") or []
    feature_count = raw_claim.get("feature_count")
    if feature_count is None:
        feature_count = inferred_fields.get("feature_count")

    confidence = raw_claim.get("confidence", 0.75)
    try:
        confidence_value = max(0.0, min(float(confidence), 1.0))
    except (TypeError, ValueError):
        confidence_value = 0.75

    return Claim(
        claim_id=str(raw_claim.get("claim_id") or f"claim-{claim_index}"),
        claim_text=claim_text,
        claim_type=claim_type,
        span_category=str(raw_claim.get("span_category") or "sentence"),
        is_numeric=bool(
            raw_claim.get("is_numeric")
            if raw_claim.get("is_numeric") is not None
            else numeric_value is not None
        ),
        requires_grounding_from=str(
            raw_claim.get("requires_grounding_from") or "table/json"
        ),
        confidence=confidence_value,
        subject=raw_claim.get("subject") or inferred_fields.get("subject"),
        predicate=raw_claim.get("predicate"),
        object=raw_claim.get("object") or inferred_fields.get("object"),
        metric=metric,
        value=numeric_value if numeric_value is not None else value,
        unit=raw_claim.get("unit"),
        ordered_items=[str(item).strip() for item in ordered_items if str(item).strip()],
        feature_count=int(feature_count) if feature_count is not None else None,
        hedged=bool(raw_claim.get("hedged") or inferred_fields.get("hedged")),
    )


def extract_claims(payload: dict[str, Any]) -> list[Claim]:
    raw_claims = payload.get("claims")
    if isinstance(raw_claims, list):
        return [_normalize_claim(raw_claim, index) for index, raw_claim in enumerate(raw_claims, start=1)]

    explanation_full = str(payload.get("explanation_full") or payload.get("explanation_short") or "").strip()
    claims: list[Claim] = []
    for index, sentence in enumerate(_split_sentences(explanation_full), start=1):
        claims.append(
            _normalize_claim(
                {
                    "claim_id": f"claim-{index}",
                    "claim_text": sentence,
                },
                claim_index=index,
            )
        )
    return claims


def normalize_generation(
    payload: dict[str, Any],
    artifact_id: str,
    arm: str,
    input_condition: str,
) -> ExplanationOutput:
    explanation_short = str(payload.get("explanation_short") or "").strip()
    explanation_full = str(payload.get("explanation_full") or explanation_short).strip()
    return ExplanationOutput(
        artifact_id=str(payload.get("artifact_id") or artifact_id),
        arm=str(payload.get("arm") or arm),
        input_condition=str(payload.get("input_condition") or input_condition),
        explanation_short=explanation_short,
        explanation_full=explanation_full,
        claims=extract_claims(payload),
    )
