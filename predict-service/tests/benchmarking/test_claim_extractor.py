from __future__ import annotations

import pytest

from benchmarking.claim_extractor import normalize_generation


def test_claim_extractor_canonicalizes_metric_and_model_aliases() -> None:
    generation = normalize_generation(
        payload={
            "artifact_id": "fixture:chart/model_rf_scatter",
            "arm": "C",
            "input_condition": "image_table_summary",
            "explanation_short": "RF diagnostics are strong.",
            "explanation_full": "RF diagnostics are strong.",
            "claims": [
                {
                    "claim_id": "claim-1",
                    "claim_text": "The Random Forest (RF) model had an RMSE of 0.1254.",
                    "claim_type": "Metric Comparison",
                    "span_category": "model_metrics",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 1.0,
                    "subject": "Random Forest (RF)",
                    "predicate": "has RMSE",
                    "metric": "rmse",
                    "value": 0.1254,
                    "ordered_items": [],
                    "feature_count": None,
                    "hedged": False,
                }
            ],
        },
        artifact_id="fixture:chart/model_rf_scatter",
        arm="C",
        input_condition="image_table_summary",
    )

    claim = generation.claims[0]
    assert claim.claim_type == "metric_value"
    assert claim.subject == "RF"
    assert claim.metric == "rmse"


def test_claim_extractor_maps_correlation_subject_and_metric_aliases() -> None:
    generation = normalize_generation(
        payload={
            "artifact_id": "fixture:chart/correlation_heatmap",
            "arm": "B",
            "input_condition": "image_table_summary",
            "explanation_short": "Correlation findings.",
            "explanation_full": "Correlation findings.",
            "claims": [
                {
                    "claim_id": "pair",
                    "claim_text": "Butyrate vs VFA correlation is 0.9601.",
                    "claim_type": "Correlation Strength",
                    "span_category": "correlation",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 1.0,
                    "subject": "Butyrate",
                    "predicate": "vs VFA correlation",
                    "metric": "correlation",
                    "value": 0.9601,
                    "ordered_items": [],
                    "feature_count": None,
                    "hedged": False,
                },
                {
                    "claim_id": "target",
                    "claim_text": "VFA has the strongest correlation with HPR (0.7984).",
                    "claim_type": "Top Feature Correlation",
                    "span_category": "correlation",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 1.0,
                    "subject": "VFA",
                    "predicate": "correlation with HPR",
                    "metric": "correlation",
                    "value": 0.7984,
                    "ordered_items": [],
                    "feature_count": None,
                    "hedged": False,
                },
                {
                    "claim_id": "diagnostic",
                    "claim_text": "The correlation between predicted and actual values for SVM was 0.86576.",
                    "claim_type": "Metric Value",
                    "span_category": "prediction_story",
                    "is_numeric": True,
                    "requires_grounding_from": "chart",
                    "confidence": 1.0,
                    "subject": "SVM",
                    "predicate": "correlation between predicted and actual values",
                    "metric": "correlation",
                    "value": 0.86576,
                    "ordered_items": [],
                    "feature_count": None,
                    "hedged": False,
                },
            ],
        },
        artifact_id="fixture:chart/correlation_heatmap",
        arm="B",
        input_condition="image_table_summary",
    )

    pair_claim, target_claim, diagnostic_claim = generation.claims
    assert pair_claim.claim_type == "metric_value"
    assert pair_claim.subject == "Butyrate vs VFA"
    assert pair_claim.metric == "correlation"

    assert target_claim.claim_type == "metric_value"
    assert target_claim.subject == "VFA"
    assert target_claim.metric == "target_correlation"

    assert diagnostic_claim.claim_type == "metric_value"
    assert diagnostic_claim.subject == "SVM"
    assert diagnostic_claim.metric == "pred_actual_correlation"


def test_normalize_generation_keeps_manifest_metadata() -> None:
    payload = {
        "artifact_id": "hallucinated-artifact-id",
        "arm": "hallucinated-arm",
        "input_condition": "hallucinated-condition",
        "semantic_level": "L1",
        "explanation_short": "KNN has R2=0.81.",
        "claims": [
            {
                "claim_id": "claim_1",
                "claim_text": "KNN has R2=0.81.",
                "claim_type": "metric value",
                "metric": "r2",
                "value": 0.81,
            }
        ],
    }

    generation = normalize_generation(
        payload,
        artifact_id="fixture:model_comparison/main",
        arm="A",
        input_condition="image_table_summary",
    )

    assert generation.artifact_id == "fixture:model_comparison/main"
    assert generation.arm == "A"
    assert generation.input_condition == "image_table_summary"
    assert generation.semantic_level is None


def test_normalize_generation_requires_structured_claims_array() -> None:
    with pytest.raises(ValueError, match="structured 'claims' array"):
        normalize_generation(
            {
                "artifact_id": "fixture:model_comparison/main",
                "arm": "A",
                "input_condition": "image_table_summary",
                "explanation_short": "KNN leads.",
                "explanation_full": "KNN leads.",
            },
            artifact_id="fixture:model_comparison/main",
            arm="A",
            input_condition="image_table_summary",
        )
