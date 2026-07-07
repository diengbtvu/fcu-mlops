from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from benchmarking.manifest import build_manifest

FIXTURE_BUNDLE = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"


def test_build_manifest_detects_phase_one_units() -> None:
    records = build_manifest(FIXTURE_BUNDLE)

    artifact_types = {record.artifact_type for record in records}
    assert {
        "model_comparison/main",
        "incremental_feature_analysis/main",
        "feature_ranking/gra",
    }.issubset(artifact_types)
    assert "chart/fig3b_shap_analysis" in artifact_types
    assert "chart/predicted_vs_actual" in artifact_types
    assert "chart/time_series" in artifact_types

    model_comparison = next(
        record for record in records if record.artifact_type == "model_comparison/main"
    )
    assert model_comparison.primary_entities == ["KNN", "RF", "SVM"]
    assert "table_model_comparison.csv" in model_comparison.source_files

    chart_record = next(record for record in records if record.asset_key == "feature_importance")
    assert chart_record.asset_family == "feature_story_importance"
    assert "table_feature_importance.csv" in chart_record.source_files


def test_build_manifest_fails_on_missing_required_file(tmp_path: Path) -> None:
    copied_bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURE_BUNDLE, copied_bundle)
    (copied_bundle / "gra_ranking.json").unlink()

    with pytest.raises(FileNotFoundError):
        build_manifest(copied_bundle)
