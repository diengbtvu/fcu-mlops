from __future__ import annotations

import json
from pathlib import Path

from benchmarking.chart_reporting import write_per_chart_benchmark_outputs
from benchmarking.cli import main


def test_per_chart_benchmark_outputs_include_chart_level_breakdown(tmp_path: Path) -> None:
    output_dir = tmp_path / "benchmark-output"

    exit_code = main(
        [
            "--fixture-only",
            "--output-dir",
            str(output_dir),
            "--conditions",
            "image_table_summary",
        ]
    )

    assert exit_code == 0
    payload = write_per_chart_benchmark_outputs(output_dir)

    assert payload["artifact_count"] >= 10
    assert payload["chart_count"] > 0
    assert payload["row_count"] >= payload["artifact_count"]
    assert payload["coverage_gaps"] == []

    correlation_entry = next(
        item
        for item in payload["artifacts"]
        if item["artifact_id"].endswith(":chart:correlation_heatmap")
    )
    assert correlation_entry["artifact_scope"] == "chart"
    assert correlation_entry["best_row"] is not None
    assert "baseline_row" not in correlation_entry
    assert correlation_entry["rows"][0]["supported_claim_count"] >= 0
    assert "top_reason" in correlation_entry["rows"][0]

    disk_payload = json.loads((output_dir / "scores" / "per_chart_benchmark.json").read_text())
    assert disk_payload["artifact_count"] == payload["artifact_count"]
