from __future__ import annotations

import re
from typing import Any

from .schemas import CANONICAL_CLAIM_TYPES, Claim, ExplanationOutput

HEDGE_PATTERN = re.compile(r"\b(about|around|approximately|roughly|nearly|almost)\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
FEATURE_COUNT_PATTERN = re.compile(r"(\d+)\s+features?", re.IGNORECASE)
ORDERING_PATTERN = re.compile(r"([A-Za-z0-9_+\-/ ]+(?:\s*>\s*[A-Za-z0-9_+\-/ ]+)+)")
PAIR_PATTERNS = (
    re.compile(r"\b(?P<left>[A-Za-z0-9_+\-/]+)\s+vs\s+(?P<right>[A-Za-z0-9_+\-/]+)\b", re.IGNORECASE),
    re.compile(
        r"\bcorrelation between\s+(?P<left>[A-Za-z0-9_+\-/]+)\s+and\s+(?P<right>[A-Za-z0-9_+\-/]+)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<left>[A-Za-z0-9_+\-/]+)\b[^.]*?\bcorrelation with\b\s+(?P<right>[A-Za-z0-9_+\-/]+)\b",
        re.IGNORECASE,
    ),
)
MODEL_MENTION_PATTERN = re.compile(
    r"\b(?P<model>KNN|RF|SVM|DT|XGBoost|Random Forest|Decision Tree|Deep Tree|K-Nearest Neighbors|K Nearest Neighbors)\b",
    re.IGNORECASE,
)
SUBJECT_PATTERN = re.compile(
    r"\b(?P<subject>[A-Za-z0-9_+\-/]+)\s+(?:achieved|had|has|reaches|recorded|shows|showed|exhibits|is|was)\b",
    re.IGNORECASE,
)
TOP_ENTITY_PATTERN = re.compile(
    r"\b(?P<subject>[A-Za-z0-9_+\-/]+)\s+(?:is|has)\s+(?:the\s+)?(?:top|strongest|highest|lowest|largest|smallest|first)\b",
    re.IGNORECASE,
)

CLAIM_TYPE_ALIASES = {
    "analysis summary": "metric_value",
    "comparative": "metric_value",
    "comparison": "metric_value",
    "comparison impact": "metric_value",
    "comparison/impact": "metric_value",
    "conclusion": "freeform",
    "correlation": "metric_value",
    "correlation coefficient": "metric_value",
    "correlation strength": "metric_value",
    "correlation/impact": "metric_value",
    "descriptive statistic": "metric_value",
    "descriptive_statistic": "metric_value",
    "diagnostic finding": "metric_value",
    "error magnitude": "metric_value",
    "factual": "freeform",
    "feature correlation": "metric_value",
    "feature importance": "metric_value",
    "feature ranking": "metric_value",
    "inference": "freeform",
    "metric": "metric_value",
    "metric comparison": "metric_value",
    "metric retrieval": "metric_value",
    "metric value": "metric_value",
    "metric_comparison": "metric_value",
    "metric_retrieval": "metric_value",
    "metric_summary": "metric_value",
    "model performance": "metric_value",
    "quantitative comparison": "metric_value",
    "r squared": "metric_value",
    "r-squared": "metric_value",
    "recommendation": "freeform",
    "sequence analysis": "metric_value",
    "slope": "metric_value",
    "specific value": "metric_value",
    "statistical comparison": "metric_value",
    "trend": "freeform",
    "top feature correlation": "metric_value",
    "value": "metric_value",
}

METRIC_ALIASES = {
    "actual max": "actual_max",
    "actual min": "actual_min",
    "actual peak occurs at index": "actual_peak_index",
    "actual peak value": "actual_peak_value",
    "actual_peak_index": "actual_peak_index",
    "actual_peak_value": "actual_peak_value",
    "average": "mean",
    "correlation": "correlation",
    "correlation coefficient": "correlation",
    "correlation between predicted and actual": "pred_actual_correlation",
    "correlation between predicted and actual values": "pred_actual_correlation",
    "corr(pred, actual)": "pred_actual_correlation",
    "corr(pred,actual)": "pred_actual_correlation",
    "feature importance": "importance",
    "gra score": "gra_score",
    "gra_score": "gra_score",
    "grey relational score": "gra_score",
    "has mae": "mae",
    "has mse": "mse",
    "has r2 score": "r2_score",
    "has rmse": "rmse",
    "hpr correlation": "target_correlation",
    "importance": "importance",
    "linear fit slope": "linear_fit_slope",
    "mae": "mae",
    "max abs gap": "max_abs_gap",
    "max abs residual": "max_abs_residual",
    "max absolute gap": "max_abs_gap",
    "max absolute residual": "max_abs_residual",
    "max_abs_gap": "max_abs_gap",
    "max_abs_residual": "max_abs_residual",
    "mean": "mean",
    "mean abs gap": "mean_abs_gap",
    "mean abs shap": "mean_abs_shap",
    "mean absolute gap": "mean_abs_gap",
    "mean absolute shap": "mean_abs_shap",
    "mean_abs_gap": "mean_abs_gap",
    "mean_abs_shap": "mean_abs_shap",
    "mse": "mse",
    "p95 abs residual": "p95_abs_residual",
    "p95_abs_residual": "p95_abs_residual",
    "pred actual correlation": "pred_actual_correlation",
    "pred_actual_correlation": "pred_actual_correlation",
    "predicted max": "predicted_max",
    "predicted min": "predicted_min",
    "predicted peak occurs later at index": "predicted_peak_index",
    "predicted peak value": "predicted_peak_value",
    "predicted vs actual correlation": "pred_actual_correlation",
    "predicted-vs-actual correlation": "pred_actual_correlation",
    "predicted_max": "predicted_max",
    "predicted_min": "predicted_min",
    "predicted_peak_index": "predicted_peak_index",
    "predicted_peak_value": "predicted_peak_value",
    "r squared": "r2_score",
    "r-squared": "r2_score",
    "r2": "r2_score",
    "r2 score": "r2_score",
    "r2_score": "r2_score",
    "r²": "r2_score",
    "r² score": "r2_score",
    "residual mean": "residual_mean",
    "residual standard deviation": "residual_std",
    "residual std": "residual_std",
    "residual_mean": "residual_mean",
    "residual_std": "residual_std",
    "rmse": "rmse",
    "score": "gra_score",
    "sequence correlation": "sequence_correlation",
    "sequence_correlation": "sequence_correlation",
    "shap": "mean_abs_shap",
    "shap importance": "mean_abs_shap",
    "slope": "linear_fit_slope",
    "standard deviation": "std",
    "std": "std",
    "target correlation": "target_correlation",
    "target_correlation": "target_correlation",
}


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    lowered = str(value).strip().lower()
    lowered = lowered.replace("–", "-").replace("—", "-")
    lowered = re.sub(r"[_-]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _canonical_model_name(value: str | None) -> str | None:
    normalized = _normalize_key(value)
    if not normalized:
        return None
    if "random forest" in normalized or re.search(r"\brf\b", str(value or ""), re.IGNORECASE):
        return "RF"
    if "xgboost" in normalized or "xg boost" in normalized:
        return "XGBoost"
    if "support vector" in normalized or re.search(r"\bsvm\b", str(value or ""), re.IGNORECASE):
        return "SVM"
    if "decision tree" in normalized or "deep tree" in normalized or re.search(r"\bdt\b", str(value or ""), re.IGNORECASE):
        return "DT"
    if "k nearest neighbors" in normalized or "k nearest neighbours" in normalized or "k nearest neighbor" in normalized:
        return "KNN"
    if re.search(r"\bknn\b", str(value or ""), re.IGNORECASE):
        return "KNN"
    return None


def _canonical_label(value: Any) -> str | None:
    text = str(value or "").strip().strip(".,;:")
    if not text:
        return None
    model_name = _canonical_model_name(text)
    if model_name:
        return model_name
    text = re.sub(r"^\s*the\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+model\b", "", text, flags=re.IGNORECASE).strip()
    return text or None


def _normalize_metric(metric: str | None) -> str | None:
    if not metric:
        return None
    normalized = _normalize_key(metric)
    if not normalized:
        return None
    return METRIC_ALIASES.get(normalized, normalized.replace(" ", "_"))


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _parse_ordered_items(claim_text: str) -> list[str]:
    candidate_text = claim_text.replace("->", " ")
    match = ORDERING_PATTERN.search(candidate_text)
    if not match:
        return []
    return [item.strip().strip(".,;:") for item in match.group(1).split(">") if item.strip()]


def _pair_subject(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        for pattern in PAIR_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            left = _canonical_label(match.group("left"))
            right = _canonical_label(match.group("right"))
            if left and right:
                return f"{left} vs {right}"
    return None


def _extract_subject_from_text(claim_text: str, predicate: str | None, metric: str | None) -> str | None:
    pair_subject = _pair_subject(claim_text, predicate)
    if pair_subject:
        return pair_subject

    for value in (predicate, claim_text):
        model_match = MODEL_MENTION_PATTERN.search(str(value or ""))
        if model_match:
            model_name = _canonical_model_name(model_match.group("model"))
            if model_name:
                return model_name

    for pattern in (TOP_ENTITY_PATTERN, SUBJECT_PATTERN):
        match = pattern.search(claim_text)
        if match:
            return _canonical_label(match.group("subject"))

    if metric == "pred_actual_correlation":
        match = re.search(r"\bfor\s+(?P<subject>[A-Za-z0-9_+\-/]+)\b", claim_text, re.IGNORECASE)
        if match:
            return _canonical_label(match.group("subject"))

    return None


def _infer_metric_from_context(
    metric: str | None,
    claim_text: str,
    predicate: str | None,
) -> str | None:
    normalized = _normalize_metric(metric)
    context = " ".join(part for part in (metric, predicate, claim_text) if part).lower()

    if normalized in {None, "correlation"}:
        if any(token in context for token in ("sequence correlation", "sequence_correlation")):
            return "sequence_correlation"
        if any(
            token in context
            for token in (
                "corr(pred,actual)",
                "corr(pred, actual)",
                "pred actual correlation",
                "predicted vs actual",
                "predicted-vs-actual",
                "predicted and actual",
                "pred_actual",
            )
        ):
            return "pred_actual_correlation"
        if any(
            token in context
            for token in (
                "target correlation",
                "target_correlation",
                "top feature correlation",
                "with hpr",
                "correlation with hpr",
                "target variable",
            )
        ):
            return "target_correlation"

    if normalized is not None:
        return normalized

    if any(token in context for token in ("gra", "grey relational", "gray relational")):
        return "gra_score"
    if "feature importance" in context or "important feature" in context:
        return "importance"
    if "shap" in context:
        return "mean_abs_shap"
    if "standard deviation" in context:
        return "std"
    if re.search(r"\bmean\b", context) or "average" in context:
        return "mean"
    return None


def _infer_claim_type(claim_text: str) -> str:
    lowered = claim_text.lower()
    if "best model" in lowered or "winning model" in lowered or "winner" in lowered:
        return "best_model"
    if "plateau" in lowered:
        return "plateau"
    if "best subset" in lowered or "best step" in lowered or "best with" in lowered:
        return "feature_subset_optimum"
    if " > " in claim_text or "ranking" in lowered or "ordering" in lowered:
        return "ranking"
    if "top feature" in lowered:
        return "top_feature"
    if "gra score" in lowered:
        return "rank_score"
    if NUMBER_PATTERN.search(claim_text):
        return "metric_value"
    return "freeform"


def _canonicalize_claim_type(
    raw_claim_type: str,
    claim_text: str,
    metric: str | None,
    numeric_value: float | None,
    ordered_items: list[str],
    feature_count: int | None,
) -> str:
    raw_key = _normalize_key(raw_claim_type)
    lowered = claim_text.lower()
    claim_type = CLAIM_TYPE_ALIASES.get(raw_key) or _infer_claim_type(claim_text)

    if feature_count is not None and any(token in lowered for token in ("best", "subset", "step", "features")):
        claim_type = "feature_subset_optimum"
    if "plateau" in lowered:
        claim_type = "plateau"

    if numeric_value is not None and metric:
        claim_type = "rank_score" if metric == "gra_score" else "metric_value"
    elif claim_type == "ranking" and len(ordered_items) < 2:
        if any(token in lowered for token in ("top", "strongest", "highest", "lowest", "largest", "smallest", "first")):
            claim_type = "top_feature"
        else:
            claim_type = "freeform"
    elif claim_type == "freeform" and metric and any(
        token in lowered for token in ("top", "strongest", "highest", "lowest", "largest", "smallest", "first")
    ):
        claim_type = "top_feature"

    if claim_type not in CANONICAL_CLAIM_TYPES:
        return "freeform"
    return claim_type


def _numeric_value(raw_claim: dict[str, Any], claim_text: str) -> float | None:
    value = raw_claim.get("value")
    if value is None and isinstance(raw_claim.get("object"), (int, float)):
        value = raw_claim.get("object")
    if value is not None:
        return _as_float(value)

    if raw_claim.get("ordered_items"):
        return None

    raw_claim_type = _normalize_key(str(raw_claim.get("claim_type") or ""))
    if raw_claim_type in {"ranking", "feature ranking", "rank ordering"}:
        return None

    numeric_values = NUMBER_PATTERN.findall(claim_text)
    if not numeric_values:
        return None
    return _as_float(numeric_values[-1])


def _top_or_best_object(
    raw_object: Any,
    raw_subject: str | None,
    claim_text: str,
    predicate: str | None,
) -> str | None:
    for candidate in (raw_object, raw_subject):
        label = _canonical_label(candidate)
        if label and not isinstance(candidate, (int, float)):
            return label

    pair_subject = _pair_subject(claim_text, predicate)
    if pair_subject:
        return pair_subject

    match = TOP_ENTITY_PATTERN.search(claim_text)
    if match:
        return _canonical_label(match.group("subject"))
    match = SUBJECT_PATTERN.search(claim_text)
    if match:
        return _canonical_label(match.group("subject"))
    return None


def _normalize_claim(raw_claim: dict[str, Any], claim_index: int) -> Claim:
    claim_text = str(raw_claim.get("claim_text") or "").strip()
    if not claim_text:
        raise ValueError(f"Claim at index {claim_index} is missing claim_text.")

    predicate = str(raw_claim.get("predicate") or "").strip() or None
    ordered_items = raw_claim.get("ordered_items") or _parse_ordered_items(claim_text)
    ordered_items = [str(item).strip().strip(".,;:") for item in ordered_items if str(item).strip()]

    feature_count = raw_claim.get("feature_count")
    if feature_count is None:
        feature_count_match = FEATURE_COUNT_PATTERN.search(claim_text)
        if feature_count_match:
            feature_count = int(feature_count_match.group(1))

    numeric_value = _numeric_value(raw_claim, claim_text)
    metric = _infer_metric_from_context(raw_claim.get("metric"), claim_text, predicate)
    subject = _canonical_label(raw_claim.get("subject"))
    if metric == "correlation":
        subject = _pair_subject(raw_claim.get("subject"), predicate, claim_text) or subject
    if not subject:
        subject = _extract_subject_from_text(claim_text, predicate, metric)

    claim_type = _canonicalize_claim_type(
        raw_claim_type=str(raw_claim.get("claim_type") or ""),
        claim_text=claim_text,
        metric=metric,
        numeric_value=numeric_value,
        ordered_items=ordered_items,
        feature_count=int(feature_count) if feature_count is not None else None,
    )

    object_value = raw_claim.get("object")
    if claim_type in {"best_model", "top_feature"}:
        object_value = _top_or_best_object(object_value, subject, claim_text, predicate)

    if claim_type == "top_feature" and subject and object_value is None:
        object_value = subject
    if claim_type == "best_model" and object_value is None:
        object_value = subject

    if claim_type == "rank_score" and metric is None:
        metric = "gra_score"

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
        requires_grounding_from=str(raw_claim.get("requires_grounding_from") or "table/json"),
        confidence=confidence_value,
        source_variable_id=str(raw_claim.get("source_variable_id") or raw_claim.get("variable_id") or "").strip() or None,
        subject=subject,
        predicate=predicate,
        object=object_value,
        metric=metric,
        value=numeric_value if numeric_value is not None else raw_claim.get("value"),
        unit=raw_claim.get("unit"),
        ordered_items=ordered_items,
        feature_count=int(feature_count) if feature_count is not None else None,
        hedged=bool(raw_claim.get("hedged") or HEDGE_PATTERN.search(claim_text)),
    )


def extract_claims(payload: dict[str, Any]) -> list[Claim]:
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        raise ValueError("Generation payload is missing a structured 'claims' array.")
    return [_normalize_claim(raw_claim, index) for index, raw_claim in enumerate(raw_claims, start=1)]


def normalize_generation(
    payload: dict[str, Any],
    artifact_id: str,
    arm: str,
    input_condition: str,
    semantic_level: str | None = None,
) -> ExplanationOutput:
    explanation_short = str(payload.get("explanation_short") or "").strip()
    explanation_full = str(payload.get("explanation_full") or explanation_short).strip()
    resolved_arm = str(arm).strip() or str(payload.get("arm") or "").strip()
    resolved_semantic_level: str | None = None
    if resolved_arm == "B":
        resolved_semantic_level = (
            semantic_level
            or str(payload.get("semantic_level") or "").strip()
            or None
        )
    return ExplanationOutput(
        artifact_id=str(artifact_id).strip() or str(payload.get("artifact_id") or "").strip(),
        arm=resolved_arm,
        input_condition=str(input_condition).strip() or str(payload.get("input_condition") or "").strip(),
        explanation_short=explanation_short,
        explanation_full=explanation_full,
        claims=extract_claims(payload),
        semantic_level=resolved_semantic_level,
        generation_stage=str(payload.get("generation_stage") or "").strip() or None,
        parent_draft_hash=str(payload.get("parent_draft_hash") or "").strip() or None,
    )
