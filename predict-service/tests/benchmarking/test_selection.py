from __future__ import annotations

from pathlib import Path

from benchmarking.cli import main
from benchmarking.selection import build_selected_benchmark_explanations


def test_selected_benchmark_explanations_prefers_best_leaderboard_row(tmp_path: Path) -> None:
    output_dir = tmp_path / "benchmark-output"

    exit_code = main(["--fixture-only", "--output-dir", str(output_dir)])

    assert exit_code == 0
    payload, warnings = build_selected_benchmark_explanations(output_dir)

    assert warnings == []
    assert payload is not None
    assert payload["selected_arm"] == "A"
    assert payload["selected_semantic_level"] is None
    assert payload["selected_condition"] != ""
    assert payload["selection_method"] == "best_leaderboard_row"
    assert "metrics_overview" in payload["assets"]
    assert "model_comparison_table" in payload["assets"]
    assert "table1_incremental_results" in payload["assets"]
    assert "gra_ranking" in payload["assets"]
    assert "fig5_model_comparison" in payload["assets"]
    assert "feature_importance" in payload["assets"]
    assert payload["overview"]["en"] != ""
