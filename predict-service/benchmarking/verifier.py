from __future__ import annotations

from typing import Any

from .schemas import Claim, ClaimVerification, GoldArtifact

STATUS_SUPPORTED = "supported"
STATUS_PARTIAL = "partially_supported"
STATUS_CONTRADICTED = "contradicted"
STATUS_UNVERIFIABLE = "unverifiable"


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _metric_alias(metric: str | None) -> str | None:
    if not metric:
        return None
    lowered = metric.strip().lower()
    return {
        "r2": "r2_score",
        "r²": "r2_score",
        "r2_score": "r2_score",
        "best_r2": "r2_score",
        "mse": "mse",
        "best_mse": "mse",
        "rmse": "rmse",
        "mae": "mae",
        "score": "gra_score",
        "gra_score": "gra_score",
        "importance": "importance",
        "mean_abs_shap": "mean_abs_shap",
        "target_correlation": "target_correlation",
        "correlation": "correlation",
        "corr(pred,actual)": "pred_actual_correlation",
        "corr(pred, actual)": "pred_actual_correlation",
        "pred_actual_correlation": "pred_actual_correlation",
        "sequence_correlation": "sequence_correlation",
        "slope": "linear_fit_slope",
        "linear_fit_slope": "linear_fit_slope",
        "intercept": "linear_fit_intercept",
        "linear_fit_intercept": "linear_fit_intercept",
        "residual_mean": "residual_mean",
        "residual_std": "residual_std",
        "mean_abs_residual": "mean_abs_residual",
        "max_abs_residual": "max_abs_residual",
        "p95_abs_residual": "p95_abs_residual",
        "actual_peak_index": "actual_peak_index",
        "actual_peak_value": "actual_peak_value",
        "predicted_peak_index": "predicted_peak_index",
        "predicted_peak_value": "predicted_peak_value",
        "mean_abs_gap": "mean_abs_gap",
        "max_abs_gap": "max_abs_gap",
        "mean": "mean",
        "std": "std",
    }.get(lowered, lowered)


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


def _verify_best_model(gold: GoldArtifact, claim: Claim) -> ClaimVerification:
    candidate = str(claim.object or claim.subject or "").strip()
    if not candidate:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Best-model claim lacks a model name.")
    facts = [fact for fact in gold.ground_truth_facts if fact.fact_type == "best_model"]
    if not facts:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="No best-model fact found.")
    fact = facts[0]
    status = STATUS_SUPPORTED if candidate == fact.object else STATUS_CONTRADICTED
    reason = f"Gold best model is {fact.object}."
    return _verification(gold, claim, status, [fact.fact_id], reason)


def _verify_metric_value(gold: GoldArtifact, claim: Claim) -> ClaimVerification:
    metric = _metric_alias(claim.metric)
    claim_value = _as_float(claim.value)
    if claim_value is None:
        return _verification(gold, claim, STATUS_UNVERIFIABLE, reason="Numeric claim is missing a numeric value.")

    candidate_facts = [
        fact
        for fact in gold.ground_truth_facts
        if fact.subject == claim.subject
        and fact.value is not None
        and fact.fact_type in {"metric_value", "rank_score", "best_r2", "best_mse"}
        and _metric_alias(fact.predicate) == metric
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
    candidate_facts = [
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
    facts = [fact for fact in gold.ground_truth_facts if fact.fact_type == "top_feature"]
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
    facts = [
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


def verify_claims(gold: GoldArtifact, claims: list[Claim], arm: str, input_condition: str) -> list[ClaimVerification]:
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
                claim_id=verification.claim_id,
                claim_text=verification.claim_text,
                status=verification.status,
                matched_fact_ids=verification.matched_fact_ids,
                reason=verification.reason,
                numeric_delta=verification.numeric_delta,
            )
        )
    return verifications
