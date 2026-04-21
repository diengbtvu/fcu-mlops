from __future__ import annotations

from pathlib import Path

from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest
from benchmarking.schemas import Claim
from benchmarking.verifier import verify_claims

FIXTURE_BUNDLE = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"


def _gold_map():
    records = build_manifest(FIXTURE_BUNDLE)
    gold_artifacts = build_gold_artifacts(FIXTURE_BUNDLE, records)
    return {item.artifact_type: item for item in gold_artifacts}


def test_verifier_supports_and_contradicts_numeric_claims() -> None:
    gold = _gold_map()["model_comparison/main"]
    claims = [
        Claim(
            claim_id="supported",
            claim_text="KNN achieved R2=0.92.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.9,
            subject="KNN",
            metric="r2_score",
            value=0.92,
        ),
        Claim(
            claim_id="contradicted",
            claim_text="KNN achieved R2=0.70.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.9,
            subject="KNN",
            metric="r2_score",
            value=0.70,
        ),
    ]

    verifications = verify_claims(gold, claims, arm="A", input_condition="table_only")

    assert verifications[0].status == "supported"
    assert verifications[1].status == "contradicted"


def test_verifier_supports_ranking_and_marks_unsupported_claims() -> None:
    gold = _gold_map()["feature_ranking/gra"]
    claims = [
        Claim(
            claim_id="ranking",
            claim_text="The top ordering is pH > Propionate > VFA.",
            claim_type="ranking",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.9,
            ordered_items=["pH", "Propionate", "VFA"],
        ),
        Claim(
            claim_id="unsupported",
            claim_text="Temperature is the top feature.",
            claim_type="top_feature",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.6,
            object="Temperature",
        ),
    ]

    verifications = verify_claims(gold, claims, arm="A", input_condition="table_only")

    assert verifications[0].status == "supported"
    assert verifications[1].status == "contradicted"


def test_verifier_supports_phase_two_chart_metrics_and_top_features() -> None:
    gold = _gold_map()["chart/correlation_heatmap"]
    claims = [
        Claim(
            claim_id="top-target",
            claim_text="pH is the top feature by target_correlation.",
            claim_type="top_feature",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.8,
            object="pH",
            metric="target_correlation",
        ),
        Claim(
            claim_id="pair-correlation",
            claim_text="pH vs VFA has correlation=0.86.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.8,
            subject="pH vs VFA",
            metric="correlation",
            value=0.86,
        ),
        Claim(
            claim_id="bad-top-target",
            claim_text="VSS is the top feature by target_correlation.",
            claim_type="top_feature",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.6,
            object="VSS",
            metric="target_correlation",
        ),
    ]

    verifications = verify_claims(gold, claims, arm="A", input_condition="table_only")

    assert verifications[0].status == "supported"
    assert verifications[1].status == "supported"
    assert verifications[2].status == "contradicted"
