from __future__ import annotations

from benchmarking.claim_alignment import alignment_metrics, build_claims_from_mentions
from benchmarking.schemas import ExtractedVariableMention


def test_claim_alignment_builds_one_claim_per_variable_mention() -> None:
    catalog = [
        {
            "source_variable_id": "artifact:model_comparison/main:best_model",
            "fact_type": "best_model",
            "claim_type": "best_model",
            "subject": "model_comparison",
            "predicate": "best_model",
            "value_kind": "entity",
        },
        {
            "source_variable_id": "artifact:model_comparison/main:metric:KNN:r2_score",
            "fact_type": "metric_value",
            "claim_type": "metric_value",
            "subject": "KNN",
            "predicate": "r2_score",
            "metric": "r2_score",
            "value_kind": "numeric",
        },
    ]
    mentions = [
        ExtractedVariableMention(
            mention_id="m1",
            source_variable_id="artifact:model_comparison/main:best_model",
            evidence_span="KNN is the best model.",
            stated_object="KNN",
        ),
        ExtractedVariableMention(
            mention_id="m2",
            source_variable_id="artifact:model_comparison/main:metric:KNN:r2_score",
            evidence_span="KNN achieved R2=0.92.",
            stated_value=0.92,
        ),
    ]

    claims, issues = build_claims_from_mentions(
        mentions=mentions,
        variable_catalog=catalog,
        artifact_id="artifact",
    )

    assert issues == []
    assert [claim.claim_type for claim in claims] == ["best_model", "metric_value"]
    assert claims[0].object == "KNN"
    assert claims[1].subject == "KNN"
    assert claims[1].metric == "r2_score"
    assert claims[1].value == 0.92


def test_claim_alignment_uses_catalog_type_over_text_shape() -> None:
    catalog = [
        {
            "source_variable_id": "artifact:feature_ranking/gra:top_feature",
            "fact_type": "top_feature",
            "claim_type": "top_feature",
            "subject": "gra",
            "predicate": "top_feature",
            "value_kind": "entity",
        }
    ]
    mentions = [
        ExtractedVariableMention(
            mention_id="m1",
            source_variable_id="artifact:feature_ranking/gra:top_feature",
            evidence_span="The best subset uses 5 features.",
            stated_feature_count=5,
        )
    ]

    claims, issues = build_claims_from_mentions(
        mentions=mentions,
        variable_catalog=catalog,
        artifact_id="artifact",
    )

    assert len(claims) == 1
    assert claims[0].claim_type == "top_feature"
    assert claims[0].feature_count is None
    assert {issue.issue_type for issue in issues} == {"missing_object"}


def test_claim_alignment_drops_rank_position_as_rank_score() -> None:
    catalog = [
        {
            "source_variable_id": "artifact:feature_ranking/gra:rank_score:pH",
            "fact_type": "rank_score",
            "claim_type": "rank_score",
            "subject": "pH",
            "predicate": "gra_score",
            "metric": "gra_score",
            "value_kind": "numeric",
        }
    ]
    mentions = [
        ExtractedVariableMention(
            mention_id="m1",
            source_variable_id="artifact:feature_ranking/gra:rank_score:pH",
            evidence_span="pH is ranked 2.",
            stated_value=2,
        )
    ]

    claims, issues = build_claims_from_mentions(
        mentions=mentions,
        variable_catalog=catalog,
        artifact_id="artifact",
    )

    diagnostics = alignment_metrics(issues, claim_count=len(claims), mention_count=len(mentions))
    assert claims == []
    assert [(issue.issue_type, issue.action) for issue in issues] == [("rank_position_not_score", "drop")]
    assert diagnostics["extraction_drop_rate"] == 1.0
