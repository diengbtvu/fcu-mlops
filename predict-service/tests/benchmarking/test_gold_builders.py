from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest

FIXTURE_BUNDLE = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"


def _find_gold(*, artifact_type: str | None = None, asset_key: str | None = None):
    records = build_manifest(FIXTURE_BUNDLE)
    gold_artifacts = build_gold_artifacts(FIXTURE_BUNDLE, records)
    for item in gold_artifacts:
        if artifact_type is not None and item.artifact_type == artifact_type:
            return item
        if asset_key is not None and item.artifact_id.endswith(f":chart:{asset_key}"):
            return item
    raise AssertionError("Gold artifact not found.")


def test_model_comparison_gold_extracts_best_model_and_metrics() -> None:
    gold = _find_gold(artifact_type="model_comparison/main")

    best_fact = next(fact for fact in gold.ground_truth_facts if fact.fact_type == "best_model")
    metric_fact = next(
        fact
        for fact in gold.ground_truth_facts
        if fact.fact_type == "metric_value"
        and fact.subject == "KNN"
        and fact.predicate == "r2_score"
    )

    assert best_fact.object == "KNN"
    assert metric_fact.value == 0.92
    assert best_fact.semantic_level == "L2L3"
    assert metric_fact.semantic_level == "L1"


def test_incremental_gold_detects_optimum_and_plateau() -> None:
    gold = _find_gold(artifact_type="incremental_feature_analysis/main")

    optimum_fact = next(
        fact for fact in gold.ground_truth_facts if fact.fact_type == "feature_subset_optimum"
    )
    plateau_fact = next(fact for fact in gold.ground_truth_facts if fact.fact_type == "plateau")

    assert optimum_fact.subject == "KNN"
    assert optimum_fact.value == 6
    assert plateau_fact.value == 6


def test_feature_ranking_gold_extracts_top_ranked_feature() -> None:
    gold = _find_gold(artifact_type="feature_ranking/gra")

    top_feature_fact = next(
        fact for fact in gold.ground_truth_facts if fact.fact_type == "top_feature"
    )
    ranking_fact = next(
        fact for fact in gold.ground_truth_facts if fact.fact_type == "ranking"
    )

    assert top_feature_fact.object == "pH"
    assert ranking_fact.object[:3] == ["pH", "Propionate", "VFA"]


def test_chart_gold_extracts_phase_two_correlation_and_distribution_facts() -> None:
    correlation_gold = _find_gold(asset_key="correlation_heatmap")
    distribution_gold = _find_gold(asset_key="feature_distributions")

    top_target = next(
        fact
        for fact in correlation_gold.ground_truth_facts
        if fact.fact_type == "top_feature" and fact.predicate == "target_correlation"
    )
    top_mean = next(
        fact
        for fact in distribution_gold.ground_truth_facts
        if fact.fact_type == "top_feature" and fact.predicate == "mean"
    )

    assert top_target.object == "pH"
    assert top_mean.object == "Ethanol"


def test_chart_gold_extracts_prediction_sequence_metrics() -> None:
    gold = _find_gold(asset_key="time_series")

    sequence_correlation = next(
        fact
        for fact in gold.ground_truth_facts
        if fact.fact_type == "metric_value" and fact.predicate == "sequence_correlation"
    )
    actual_peak = next(
        fact
        for fact in gold.ground_truth_facts
        if fact.fact_type == "metric_value" and fact.predicate == "actual_peak_index"
    )

    assert sequence_correlation.value == 0.89
    assert actual_peak.value == 15.0
    assert sequence_correlation.semantic_level == "L1"


def test_gold_facts_are_tagged_with_semantic_levels() -> None:
    gold = _find_gold(artifact_type="feature_ranking/gra")

    top_feature_fact = next(
        fact for fact in gold.ground_truth_facts if fact.fact_type == "top_feature"
    )
    rank_score_fact = next(
        fact for fact in gold.ground_truth_facts if fact.fact_type == "rank_score"
    )

    assert top_feature_fact.semantic_level == "L2L3"
    assert rank_score_fact.semantic_level == "L1"


def test_prediction_diagnostics_skip_none_values(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    shutil.copytree(FIXTURE_BUNDLE, bundle_dir)

    asset_evidence_path = bundle_dir / "asset_evidence.json"
    asset_evidence_payload = json.loads(asset_evidence_path.read_text())
    asset_evidence = (
        asset_evidence_payload.get("assets")
        if isinstance(asset_evidence_payload, dict)
        else asset_evidence_payload
    )
    for item in asset_evidence:
        if item.get("key") != "model_svm_scatter":
            continue
        diagnostics = item["evidence"]["prediction_story"]["diagnostics"]
        diagnostics["pred_actual_correlation"] = None
        diagnostics["linear_fit_slope"] = "None"
        break
    else:
        raise AssertionError("Fixture asset model_svm_scatter not found.")
    if isinstance(asset_evidence_payload, dict):
        asset_evidence_payload["assets"] = asset_evidence
        output_payload = asset_evidence_payload
    else:
        output_payload = asset_evidence
    asset_evidence_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2))

    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    scatter_gold = next(item for item in gold_artifacts if item.artifact_id.endswith(":chart:model_svm_scatter"))

    predicates = {fact.predicate for fact in scatter_gold.ground_truth_facts}
    assert "pred_actual_correlation" not in predicates
    assert "linear_fit_slope" not in predicates
