from __future__ import annotations

from benchmarking.metrics import compute_artifact_scores
from benchmarking.schemas import ArtifactScore, Claim, ClaimVerification, GoldArtifact, GroundTruthFact


def test_metric_calculations_cover_precision_recall_and_rates() -> None:
    gold = GoldArtifact(
        artifact_id="fixture:model_comparison/main",
        artifact_type="model_comparison/main",
        source_files=["table_model_comparison.csv"],
        chart_type="bar_chart",
        primary_entities=["KNN", "RF"],
        ground_truth_facts=[
            GroundTruthFact(
                fact_id="fact-1",
                fact_type="best_model",
                subject="model_comparison",
                predicate="best_model",
                object="KNN",
                importance=3,
            ),
            GroundTruthFact(
                fact_id="fact-2",
                fact_type="metric_value",
                subject="KNN",
                predicate="r2_score",
                value=0.92,
                importance=2,
            ),
        ],
        salient_facts=["fact-1"],
    )
    claims = [
        Claim(
            claim_id="c1",
            claim_text="KNN is the best model.",
            claim_type="best_model",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.9,
        ),
        Claim(
            claim_id="c2",
            claim_text="KNN achieved around R2=0.918.",
            claim_type="metric_value",
            span_category="sentence",
            is_numeric=True,
            requires_grounding_from="table/json",
            confidence=0.8,
            subject="KNN",
            metric="r2_score",
            value=0.918,
            hedged=True,
        ),
        Claim(
            claim_id="c3",
            claim_text="RF is the best model.",
            claim_type="best_model",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.6,
        ),
        Claim(
            claim_id="c4",
            claim_text="The model is causal.",
            claim_type="freeform",
            span_category="sentence",
            is_numeric=False,
            requires_grounding_from="table/json",
            confidence=0.4,
        ),
    ]
    verifications = [
        ClaimVerification(
            artifact_id=gold.artifact_id,
            arm="A",
            input_condition="table_only",
            claim_id="c1",
            claim_text=claims[0].claim_text,
            status="supported",
            matched_fact_ids=["fact-1"],
        ),
        ClaimVerification(
            artifact_id=gold.artifact_id,
            arm="A",
            input_condition="table_only",
            claim_id="c2",
            claim_text=claims[1].claim_text,
            status="partially_supported",
            matched_fact_ids=["fact-2"],
        ),
        ClaimVerification(
            artifact_id=gold.artifact_id,
            arm="A",
            input_condition="table_only",
            claim_id="c3",
            claim_text=claims[2].claim_text,
            status="contradicted",
            matched_fact_ids=["fact-1"],
        ),
        ClaimVerification(
            artifact_id=gold.artifact_id,
            arm="A",
            input_condition="table_only",
            claim_id="c4",
            claim_text=claims[3].claim_text,
            status="unverifiable",
        ),
    ]

    score = compute_artifact_scores(
        gold=gold,
        claims=claims,
        verifications=verifications,
        arm="A",
        input_condition="table_only",
    )
    metrics = score.metrics

    assert metrics["fact_precision"] == 0.375
    assert metrics["fact_recall"] == 0.75
    assert round(metrics["fact_f1"], 3) == 0.5
    assert metrics["unsupported_claim_rate"] == 0.25
    assert metrics["contradiction_rate"] == 0.25
    assert metrics["coverage_of_salient_facts"] == 1.0
    assert metrics["numeric_accuracy"] == 0.0
    assert metrics["numeric_tolerance_accuracy"] == 1.0
