from __future__ import annotations

from typing import Any

from .schemas import GoldArtifact, GroundTruthFact

BENCHMARK_VARIABLE_FACT_TYPES: tuple[str, ...] = (
    "best_model",
    "metric_value",
    "ranking",
    "top_feature",
    "feature_subset_optimum",
    "plateau",
    "rank_score",
    "best_r2",
    "best_mse",
)

FACT_TYPE_TO_CLAIM_TYPE: dict[str, str] = {
    "best_model": "best_model",
    "metric_value": "metric_value",
    "ranking": "ranking",
    "top_feature": "top_feature",
    "feature_subset_optimum": "feature_subset_optimum",
    "plateau": "plateau",
    "rank_score": "rank_score",
    "best_r2": "metric_value",
    "best_mse": "metric_value",
}


def is_benchmarkable_fact(fact: GroundTruthFact) -> bool:
    return fact.fact_type in BENCHMARK_VARIABLE_FACT_TYPES


def benchmarkable_facts(
    gold: GoldArtifact,
    semantic_level: str | None = None,
) -> list[GroundTruthFact]:
    facts = [fact for fact in gold.ground_truth_facts if is_benchmarkable_fact(fact)]
    if semantic_level and semantic_level != "L1L2L3":
        facts = [fact for fact in facts if fact.semantic_level == semantic_level]
    return facts


def allowed_variable_facts(
    gold: GoldArtifact,
    semantic_level: str | None = None,
) -> list[GroundTruthFact]:
    allowed_ids = set(gold.salient_facts)
    facts: list[GroundTruthFact] = []
    for fact in benchmarkable_facts(gold, semantic_level=semantic_level):
        if fact.fact_id in allowed_ids or fact.importance >= 2:
            facts.append(fact)
    facts.sort(key=lambda fact: (-fact.importance, fact.fact_id))
    return facts


def _value_kind(fact: GroundTruthFact) -> str:
    if fact.fact_type == "ranking":
        return "ordered_items"
    if fact.fact_type in {"best_model", "top_feature"}:
        return "entity"
    if fact.fact_type in {"feature_subset_optimum", "plateau"}:
        return "feature_count"
    return "numeric"


def _metric_name(fact: GroundTruthFact) -> str | None:
    if fact.fact_type in {"best_model", "feature_subset_optimum", "plateau"}:
        return None
    return fact.predicate


def _slot_label(fact: GroundTruthFact) -> str:
    if fact.fact_type == "best_model":
        return "best_model"
    if fact.fact_type == "ranking":
        return f"ranking::{fact.predicate}"
    if fact.fact_type in {"top_feature", "rank_score", "metric_value", "best_r2", "best_mse"}:
        return f"{fact.subject}::{fact.predicate}"
    if fact.fact_type in {"feature_subset_optimum", "plateau"}:
        return f"{fact.subject}::{fact.fact_type}"
    return fact.fact_id


def build_variable_catalog(
    gold: GoldArtifact,
    semantic_level: str | None = None,
) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for fact in allowed_variable_facts(gold, semantic_level=semantic_level):
        catalog.append(
            {
                "source_variable_id": fact.fact_id,
                "slot_label": _slot_label(fact),
                "fact_type": fact.fact_type,
                "claim_type": FACT_TYPE_TO_CLAIM_TYPE[fact.fact_type],
                "subject": fact.subject,
                "predicate": fact.predicate,
                "metric": _metric_name(fact),
                "value_kind": _value_kind(fact),
                "unit": fact.unit,
                "importance": fact.importance,
                "semantic_level": fact.semantic_level,
            }
        )
    return catalog
