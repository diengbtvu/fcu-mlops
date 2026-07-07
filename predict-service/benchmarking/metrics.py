from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .claim_alignment import alignment_metrics
from .schemas import ArtifactScore, Claim, ClaimAlignmentIssue, ClaimVerification, GoldArtifact
from .variable_catalog import allowed_variable_facts

STATUS_WEIGHT = {
    "supported": 1.0,
    "partially_supported": 0.5,
    "contradicted": 0.0,
    "unverifiable": 0.0,
}


def _harmonic_mean(left: float, right: float) -> float:
    if left == 0.0 or right == 0.0:
        return 0.0
    return 2 * left * right / (left + right)


def compute_artifact_scores(
    gold: GoldArtifact,
    claims: list[Claim],
    verifications: list[ClaimVerification],
    arm: str,
    input_condition: str,
    semantic_level: str | None = None,
    alignment_issues: list[ClaimAlignmentIssue] | None = None,
    mention_count: int | None = None,
) -> ArtifactScore:
    diagnostic_metrics = alignment_metrics(
        alignment_issues or [],
        claim_count=len(claims),
        mention_count=mention_count,
    )
    claim_count = len(verifications)
    if claim_count == 0:
        metrics = {
            "fact_precision": 0.0,
            "fact_recall": 0.0,
            "fact_f1": 0.0,
            "unsupported_claim_rate": 0.0,
            "contradiction_rate": 0.0,
            "coverage_of_salient_facts": 0.0,
            "numeric_accuracy": None,
            "numeric_tolerance_accuracy": None,
            **diagnostic_metrics,
        }
        return ArtifactScore(
            artifact_id=gold.artifact_id,
            arm=arm,
            input_condition=input_condition,
            claim_count=0,
            metrics=metrics,
            semantic_level=semantic_level,
        )

    precision_numerator = sum(STATUS_WEIGHT[verification.status] for verification in verifications)
    fact_precision = precision_numerator / claim_count

    benchmark_facts = allowed_variable_facts(gold, semantic_level=semantic_level)
    fact_coverage = {fact.fact_id: 0.0 for fact in benchmark_facts}
    for verification in verifications:
        weight = STATUS_WEIGHT[verification.status]
        for fact_id in verification.matched_fact_ids:
            if fact_id in fact_coverage:
                fact_coverage[fact_id] = max(fact_coverage[fact_id], weight)

    fact_recall = (
        sum(fact_coverage.values()) / len(fact_coverage) if fact_coverage else 0.0
    )
    fact_f1 = _harmonic_mean(fact_precision, fact_recall)

    unsupported_claim_rate = (
        sum(1 for verification in verifications if verification.status == "unverifiable")
        / claim_count
    )
    contradiction_rate = (
        sum(1 for verification in verifications if verification.status == "contradicted")
        / claim_count
    )

    salient_fact_ids = [fact_id for fact_id in gold.salient_facts if fact_id in fact_coverage]
    salient_denominator = len(salient_fact_ids)
    coverage_of_salient_facts = (
        sum(fact_coverage.get(fact_id, 0.0) for fact_id in salient_fact_ids) / salient_denominator
        if salient_denominator
        else 0.0
    )

    numeric_claim_ids = {claim.claim_id for claim in claims if claim.is_numeric}
    numeric_verifications = [
        verification for verification in verifications if verification.claim_id in numeric_claim_ids
    ]
    if numeric_verifications:
        numeric_accuracy = (
            sum(1 for verification in numeric_verifications if verification.status == "supported")
            / len(numeric_verifications)
        )
        numeric_tolerance_accuracy = (
            sum(
                1
                for verification in numeric_verifications
                if verification.status in {"supported", "partially_supported"}
            )
            / len(numeric_verifications)
        )
    else:
        numeric_accuracy = None
        numeric_tolerance_accuracy = None

    return ArtifactScore(
        artifact_id=gold.artifact_id,
        arm=arm,
        input_condition=input_condition,
        claim_count=claim_count,
        metrics={
            "fact_precision": fact_precision,
            "fact_recall": fact_recall,
            "fact_f1": fact_f1,
            "unsupported_claim_rate": unsupported_claim_rate,
            "contradiction_rate": contradiction_rate,
            "coverage_of_salient_facts": coverage_of_salient_facts,
            "numeric_accuracy": numeric_accuracy,
            "numeric_tolerance_accuracy": numeric_tolerance_accuracy,
            **diagnostic_metrics,
        },
        semantic_level=semantic_level,
    )


def build_leaderboard(scores: list[ArtifactScore]) -> list[dict[str, float | int | str | None]]:
    grouped: dict[tuple[str, str, str | None], list[ArtifactScore]] = defaultdict(list)
    for score in scores:
        grouped[(score.arm, score.input_condition, score.semantic_level)].append(score)

    leaderboard_rows: list[dict[str, float | int | str | None]] = []
    metric_names = [
        "fact_precision",
        "fact_recall",
        "fact_f1",
        "unsupported_claim_rate",
        "contradiction_rate",
        "coverage_of_salient_facts",
        "numeric_accuracy",
        "numeric_tolerance_accuracy",
        "claim_alignment_error_rate",
        "missing_value_rate",
        "unknown_variable_rate",
        "extraction_drop_rate",
    ]
    for (arm, condition, semantic_level), entries in grouped.items():
        row: dict[str, float | int | str | None] = {
            "arm": arm,
            "input_condition": condition,
            "semantic_level": semantic_level,
            "artifact_count": len(entries),
            "claim_count": sum(entry.claim_count for entry in entries),
        }
        for metric_name in metric_names:
            values = [
                entry.metrics.get(metric_name)
                for entry in entries
                if entry.metrics.get(metric_name) is not None
            ]
            row[metric_name] = mean(values) if values else None
        leaderboard_rows.append(row)

    leaderboard_rows.sort(
        key=lambda row: (
            -(row.get("fact_f1") or 0.0),
            row.get("unsupported_claim_rate") or 0.0,
            row.get("contradiction_rate") or 0.0,
            row.get("arm") or "",
            row.get("input_condition") or "",
            row.get("semantic_level") or "",
        )
    )
    return leaderboard_rows
