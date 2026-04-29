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
            claim_id="pair-correlation-reversed",
            claim_text="VFA vs pH has correlation=0.86.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.8,
            subject="VFA vs pH",
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
    assert verifications[2].status == "supported"
    assert verifications[3].status == "contradicted"


def test_verifier_maps_prediction_correlation_aliases() -> None:
    gold = _gold_map()["chart/model_rf_scatter"]
    claims = [
        Claim(
            claim_id="pred-actual",
            claim_text="The correlation between predicted and actual values for Random Forest (RF) was 0.86.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.8,
            subject="Random Forest (RF)",
            predicate="correlation between predicted and actual values",
            metric="correlation",
            value=0.86,
        )
    ]

    verifications = verify_claims(gold, claims, arm="A", input_condition="table_only")

    assert verifications[0].status == "supported"


def test_verifier_ignores_incompatible_source_variable_id_for_numeric_claims() -> None:
    gold = _gold_map()["model_comparison/main"]
    artifact_id = gold.artifact_id
    claims = [
        Claim(
            claim_id="svm-r2",
            claim_text="SVM achieved R2=0.84.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.9,
            source_variable_id=f"{artifact_id}:metric:KNN:r2_score",
            subject="SVM",
            metric="r2_score",
            value=0.84,
        ),
        Claim(
            claim_id="knn-r2-via-ranking-source",
            claim_text="KNN achieved R2=0.92.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.9,
            source_variable_id=f"{artifact_id}:ranking:r2_score",
            subject="KNN",
            metric="r2_score",
            value=0.92,
        ),
    ]

    verifications = verify_claims(gold, claims, arm="A", input_condition="table_only")

    assert verifications[0].matched_fact_ids == [f"{artifact_id}:metric:SVM:r2_score"]
    assert verifications[0].status == "supported"
    assert verifications[1].matched_fact_ids == [f"{artifact_id}:metric:KNN:r2_score"]
    assert verifications[1].status == "supported"
