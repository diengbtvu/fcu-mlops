from __future__ import annotations

import re
from typing import Any

from .schemas import Claim, ClaimVerification, GoldArtifact, GroundTruthFact

STATUS_SUPPORTED = "supported"
STATUS_PARTIAL = "partially_supported"
STATUS_CONTRADICTED = "contradicted"
STATUS_UNVERIFIABLE = "unverifiable"
PAIR_SUBJECT_PATTERN = re.compile(r"^(?P<left>.+?)\s+vs\s+(?P<right>.+?)$", re.IGNORECASE)


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _metric_alias(metric: str | None) -> str | None:
    if not metric:
        return None
    lowered = metric.strip().lower()
    lowered = lowered.replace("–", "-").replace("—", "-")
    lowered = re.sub(r"[_-]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return {
        "r2": "r2_score",
        "r²": "r2_score",
        "r2 score": "r2_score",
        "r squared": "r2_score",
        "r-squared": "r2_score",
        "r2_score": "r2_score",
        "best_r2": "r2_score",
        "mse": "mse",
        "best_mse": "mse",
        "rmse": "rmse",
        "mae": "mae",
        "mean absolute error": "mae",
        "score": "gra_score",
        "gra score": "gra_score",
        "gra_score": "gra_score",
        "importance": "importance",
        "feature importance": "importance",
        "mean_abs_shap": "mean_abs_shap",
        "mean abs shap": "mean_abs_shap",
        "shap": "mean_abs_shap",
        "target_correlation": "target_correlation",
        "target correlation": "target_correlation",
        "top feature correlation": "target_correlation",
        "correlation": "correlation",
        "correlation strength": "correlation",
        "correlation coefficient": "correlation",
        "corr(pred,actual)": "pred_actual_correlation",
        "corr(pred, actual)": "pred_actual_correlation",
        "pred actual correlation": "pred_actual_correlation",
        "predicted vs actual correlation": "pred_actual_correlation",
        "predicted-vs-actual correlation": "pred_actual_correlation",
        "correlation between predicted and actual values": "pred_actual_correlation",
        "pred_actual_correlation": "pred_actual_correlation",
        "sequence correlation": "sequence_correlation",
        "sequence_correlation": "sequence_correlation",
        "slope": "linear_fit_slope",
        "linear fit slope": "linear_fit_slope",
        "linear_fit_slope": "linear_fit_slope",
        "intercept": "linear_fit_intercept",
        "linear_fit_intercept": "linear_fit_intercept",
        "residual_mean": "residual_mean",
        "residual std": "residual_std",
        "residual standard deviation": "residual_std",
        "residual_std": "residual_std",
        "mean abs residual": "mean_abs_residual",
        "mean_abs_residual": "mean_abs_residual",
        "max abs residual": "max_abs_residual",
        "max absolute residual": "max_abs_residual",
        "max_abs_residual": "max_abs_residual",
        "p95_abs_residual": "p95_abs_residual",
        "p95 abs residual": "p95_abs_residual",
        "actual_peak_index": "actual_peak_index",
        "actual_peak_value": "actual_peak_value",
        "predicted_peak_index": "predicted_peak_index",
        "predicted_peak_value": "predicted_peak_value",
        "mean abs gap": "mean_abs_gap",
        "mean_abs_gap": "mean_abs_gap",
        "max abs gap": "max_abs_gap",
        "max_abs_gap": "max_abs_gap",
        "mean": "mean",
        "average": "mean",
        "standard deviation": "std",
        "std": "std",
    }.get(lowered, lowered)


def _canonical_model_name(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if "random forest" in lowered or re.search(r"\brf\b", text, re.IGNORECASE):
        return "RF"
    if "xgboost" in lowered or "xg boost" in lowered:
        return "XGBoost"
    if "support vector" in lowered or re.search(r"\bsvm\b", text, re.IGNORECASE):
        return "SVM"
    if "decision tree" in lowered or "deep tree" in lowered or re.search(r"\bdt\b", text, re.IGNORECASE):
        return "DT"
    if "k nearest" in lowered or re.search(r"\bknn\b", text, re.IGNORECASE):
        return "KNN"
    return None


def _canonical_subject(value: Any) -> str | None:
    text = str(value or "").strip().strip(".,;:")
    if not text:
        return None
    model_name = _canonical_model_name(text)
    if model_name:
        return model_name
    text = re.sub(r"^\s*the\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+model\b", "", text, flags=re.IGNORECASE).strip()
    return text or None


def _subject_candidates(claim: Claim) -> list[str]:
    candidates: list[str] = []
    for raw_value in (claim.subject, claim.object):
        subject = _canonical_subject(raw_value)
        if subject and subject not in candidates:
            candidates.append(subject)

    match = PAIR_SUBJECT_PATTERN.match(str(claim.subject or "").strip())
    if match:
        left = _canonical_subject(match.group("left"))
        right = _canonical_subject(match.group("right"))
        if left and right:
            reversed_pair = f"{right} vs {left}"
            if reversed_pair not in candidates:
                candidates.append(reversed_pair)

    return candidates


def _metric_candidates(claim: Claim) -> list[str]:
    candidates: list[str] = []
    primary_metric = _metric_alias(claim.metric)
    if primary_metric:
        candidates.append(primary_metric)

    context = " ".join(part for part in (claim.metric, claim.predicate, claim.claim_text) if part).lower()
    if "sequence correlation" in context and "sequence_correlation" not in candidates:
        candidates.append("sequence_correlation")
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
    ) and "pred_actual_correlation" not in candidates:
        candidates.append("pred_actual_correlation")
    if any(
        token in context
        for token in (
            "target correlation",
            "top feature correlation",
            "correlation with hpr",
            "with hpr",
            "target variable",
        )
    ) and "target_correlation" not in candidates:
        candidates.append("target_correlation")

    return candidates


def _numeric_status(
    claim_value: float,
    truth_value: float,
    hedged: bool,
) -> tuple[str, float]:
    delta = abs(claim_value - truth_value)
    tight_tolerance = max(abs(truth_value) * 0.001, 1e-4)
    loose_tolerance = max(abs(truth_value) * 0.02, 0.005)

    if delta <= tight_tolerance:
        return STATUS_SUPPORTED, delta
    if hedged and delta <= loose_tolerance:
        return STATUS_PARTIAL, delta
    return STATUS_CONTRADICTED, delta


def _verification(
    gold: GoldArtifact,
    claim: Claim,
    status: str,
    matched_fact_ids: list[str] | None = None,
    reason: str = "",
    numeric_delta: float | None = None,
) -> ClaimVerification:
    return ClaimVerification(
        artifact_id=gold.artifact_id,
        arm="",
        input_condition="",
        claim_id=claim.claim_id,
        claim_text=claim.claim_text,
        status=status,
        matched_fact_ids=matched_fact_ids or [],
        reason=reason,
        numeric_delta=numeric_delta,
    )


def _fact_by_source_variable_id(
    gold: GoldArtifact,
    claim: Claim,
    compatible_fact_types: set[str] | None = None,
) -> list[GroundTruthFact]:
    source_variable_id = str(claim.source_variable_id or "").strip()
    if not source_variable_id:
        return []
    facts = [fact for fact in gold.ground_truth_facts if fact.fact_id == source_variable_id]
    if compatible_fact_types is not None:
        facts = [fact for fact in facts if fact.fact_type in compatible_fact_types]
    return facts


def _verify_best_model(gold: GoldArtifact, claim: Claim) -> ClaimVerification:
    candidate = str(claim.object or claim.subject or "").strip()
    if not candidate:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Best-model claim lacks a model name.")
    facts = _fact_by_source_variable_id(gold, claim, {"best_model"}) or [
        fact for fact in gold.ground_truth_facts if fact.fact_type == "best_model"
    ]
    if not facts:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="No best-model fact found.")
    fact = facts[0]
    status = STATUS_SUPPORTED if candidate == fact.object else STATUS_CONTRADICTED
    reason = f"Gold best model is {fact.object}."
    return _verification(gold, claim, status, [fact.fact_id], reason)


def _verify_metric_value(gold: GoldArtifact, claim: Claim) -> ClaimVerification:
    metrics = _metric_candidates(claim)
    subjects = _subject_candidates(claim)
    claim_value = _as_float(claim.value)
    if claim_value is None:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Numeric claim is missing a numeric value.")

    candidate_facts = _fact_by_source_variable_id(
        gold,
        claim,
        {"metric_value", "rank_score", "best_r2", "best_mse"},
    )
    if candidate_facts:
        candidate_facts = [
            fact
            for fact in candidate_facts
            if fact.value is not None
            and fact.fact_type in {"metric_value", "rank_score", "best_r2", "best_mse"}
            and (not subjects or fact.subject in subjects)
            and (not metrics or _metric_alias(fact.predicate) in metrics)
        ]
    if not candidate_facts:
        candidate_facts = [
            fact
            for fact in gold.ground_truth_facts
            if fact.subject in subjects
            and fact.value is not None
            and fact.fact_type in {"metric_value", "rank_score", "best_r2", "best_mse"}
            and _metric_alias(fact.predicate) in metrics
        ]

    if not candidate_facts:
        return _verification(
            gold,
            claim,
            STATUS_UNVERIFIABLE,
            reason="No matching numeric fact was found for this claim.",
        )

    fact = candidate_facts[0]
    truth_value = _as_float(fact.value)
    if truth_value is None:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Matched fact has no numeric value.")
    status, delta = _numeric_status(claim_value=claim_value, truth_value=truth_value, hedged=claim.hedged)
    return _verification(
        gold,
        claim,
        status,
        [fact.fact_id],
        reason=f"Gold value for {fact.subject} {fact.predicate} is {truth_value}.",
        numeric_delta=delta,
    )


def _verify_ranking(gold: GoldArtifact, claim: Claim) -> ClaimVerification:
    ordered_items = [item for item in claim.ordered_items if item]
    if len(ordered_items) < 2:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Ranking claim needs at least two ordered items.")

    metric = _metric_alias(claim.metric)
    candidate_facts = _fact_by_source_variable_id(gold, claim, {"ranking"}) or [
        fact for fact in gold.ground_truth_facts if fact.fact_type == "ranking"
    ]
    if metric:
        metric_candidates = [fact for fact in candidate_facts if _metric_alias(fact.predicate) == metric]
        if metric_candidates:
            candidate_facts = metric_candidates

    if not candidate_facts:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="No ranking fact found.")

    fact = candidate_facts[0]
    ranking = list(fact.object or [])
    positions = {item: index for index, item in enumerate(ranking)}
    if any(item not in positions for item in ordered_items):
        return _verification(
            gold,
            claim,
            STATUS_UNVERIFIABLE,
            [fact.fact_id],
            reason="At least one ranked item is absent from the gold ranking.",
        )

    for left_index in range(len(ordered_items) - 1):
        left = ordered_items[left_index]
        right = ordered_items[left_index + 1]
        if positions[left] >= positions[right]:
            return _verification(
                gold,
                claim,
                STATUS_CONTRADICTED,
                [fact.fact_id],
                reason=f"Gold ranking orders {left} after {right}.",
            )

    return _verification(
        gold,
        claim,
        STATUS_SUPPORTED,
        [fact.fact_id],
        reason="Claimed ordering is consistent with the gold ranking.",
    )


def _verify_top_feature(gold: GoldArtifact, claim: Claim) -> ClaimVerification:
    candidate = str(claim.object or claim.subject or "").strip()
    if not candidate:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Top-feature claim lacks a feature name.")
    metric = _metric_alias(claim.metric or claim.predicate)
    facts = _fact_by_source_variable_id(gold, claim, {"top_feature"}) or [
        fact for fact in gold.ground_truth_facts if fact.fact_type == "top_feature"
    ]
    if metric:
        metric_facts = [fact for fact in facts if _metric_alias(fact.predicate) == metric]
        if metric_facts:
            facts = metric_facts
    if not facts:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="No top-feature fact found.")
    fact = facts[0]
    status = STATUS_SUPPORTED if candidate == fact.object else STATUS_CONTRADICTED
    return _verification(
        gold,
        claim,
        status,
        [fact.fact_id],
        reason=f"Gold top feature for {fact.predicate} is {fact.object}.",
    )


def _verify_feature_count_fact(
    gold: GoldArtifact,
    claim: Claim,
    fact_type: str,
) -> ClaimVerification:
    if claim.feature_count is None:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Claim lacks a feature count.")
    facts = _fact_by_source_variable_id(gold, claim, {fact_type}) or [
        fact
        for fact in gold.ground_truth_facts
        if fact.fact_type == fact_type and (claim.subject is None or fact.subject == claim.subject)
    ]
    if not facts:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason=f"No {fact_type} fact found.")
    fact = facts[0]
    truth_value = int(_as_float(fact.value) or 0)
    status = STATUS_SUPPORTED if claim.feature_count == truth_value else STATUS_CONTRADICTED
    return _verification(
        gold,
        claim,
        status,
        [fact.fact_id],
        reason=f"Gold {fact_type} count is {truth_value}.",
        numeric_delta=abs(claim.feature_count - truth_value),
    )


def verify_claims(
    gold: GoldArtifact,
    claims: list[Claim],
    arm: str,
    input_condition: str,
    semantic_level: str | None = None,
) -> list[ClaimVerification]:
    verifications: list[ClaimVerification] = []
    for claim in claims:
        if claim.claim_type == "best_model":
            verification = _verify_best_model(gold, claim)
        elif claim.claim_type in {"metric_value", "rank_score"}:
            verification = _verify_metric_value(gold, claim)
        elif claim.claim_type == "ranking":
            verification = _verify_ranking(gold, claim)
        elif claim.claim_type == "top_feature":
            verification = _verify_top_feature(gold, claim)
        elif claim.claim_type == "feature_subset_optimum":
            verification = _verify_feature_count_fact(gold, claim, "feature_subset_optimum")
        elif claim.claim_type == "plateau":
            verification = _verify_feature_count_fact(gold, claim, "plateau")
        else:
            verification = _verification(
                gold,
                claim,
                STATUS_UNVERIFIABLE,
                reason=f"Claim type '{claim.claim_type}' is not yet rule-verified.",
            )

        verifications.append(
            ClaimVerification(
                artifact_id=verification.artifact_id,
                arm=arm,
                input_condition=input_condition,
                semantic_level=semantic_level,
                claim_id=verification.claim_id,
                claim_text=verification.claim_text,
                status=verification.status,
                matched_fact_ids=verification.matched_fact_ids,
                reason=verification.reason,
                numeric_delta=verification.numeric_delta,
            )
        )
    return verifications
