from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchmarking.cli import main


def test_cli_fixture_only_run_writes_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "benchmark-output"

    exit_code = main(["--fixture-only", "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "manifest.jsonl").exists()
    assert (output_dir / "gold").is_dir()
    assert (output_dir / "generations").is_dir()
    assert (output_dir / "extracted_claims").is_dir()
    assert (output_dir / "verifications").is_dir()
    assert (output_dir / "arm_c_traces").is_dir()
    assert (output_dir / "scores" / "leaderboard.json").exists()
    assert (output_dir / "scores" / "leaderboard.csv").exists()
    assert (output_dir / "scores" / "per_chart_benchmark.json").exists()
    assert (output_dir / "scores" / "per_chart_benchmark.csv").exists()
    assert (output_dir / "run_metadata.json").exists()
    assert all("_baseline_llm_" not in path.name for path in (output_dir / "generations").iterdir())

    leaderboard_payload = json.loads((output_dir / "scores" / "leaderboard.json").read_text())
    assert all(row["arm"] in {"A", "B", "C"} for row in leaderboard_payload["leaderboard"])
    per_chart_payload = json.loads((output_dir / "scores" / "per_chart_benchmark.json").read_text())
    assert per_chart_payload["artifact_count"] > 3
    assert per_chart_payload["row_count"] >= per_chart_payload["artifact_count"]
    metadata = json.loads((output_dir / "run_metadata.json").read_text())
    assert metadata["artifact_count"] > 3
    assert metadata["client"] == "fixture"
    assert metadata["client_model"] is None
    assert metadata["levels"] == ["L1", "L2L3", "L1L2L3"]
    assert "baseline_arm" not in metadata


def test_cli_ignores_llm_explanations_payload_when_missing(tmp_path: Path) -> None:
    source_bundle = (
        Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    )
    bundle_copy = tmp_path / "bundle-without-baseline"
    shutil.copytree(source_bundle, bundle_copy)
    (bundle_copy / "llm_explanations.json").unlink()

    output_dir = tmp_path / "benchmark-output"
    exit_code = main(["--bundle-path", str(bundle_copy), "--output-dir", str(output_dir)])

    assert exit_code == 0
    metadata = json.loads((output_dir / "run_metadata.json").read_text())
    assert "baseline_arm" not in metadata
    assert metadata["arms"] == ["A", "B", "C"]
    assert metadata["levels"] == ["L1", "L2L3", "L1L2L3"]

    leaderboard_payload = json.loads((output_dir / "scores" / "leaderboard.json").read_text())
    assert all(row["arm"] in {"A", "B", "C"} for row in leaderboard_payload["leaderboard"])


def test_cli_ignores_legacy_llm_explanations_payload(tmp_path: Path) -> None:
    source_bundle = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    bundle_copy = tmp_path / "bundle-with-legacy-baseline"
    shutil.copytree(source_bundle, bundle_copy)

    payload = json.loads((bundle_copy / "llm_explanations.json").read_text(encoding="utf-8"))
    del payload["assets"]["fig5_model_comparison"]["benchmark_payload"]
    (bundle_copy / "llm_explanations.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    output_dir = tmp_path / "benchmark-output"
    exit_code = main(["--bundle-path", str(bundle_copy), "--output-dir", str(output_dir)])

    assert exit_code == 0


def test_cli_keeps_compared_rows_aligned_for_requested_condition(tmp_path: Path) -> None:
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
    leaderboard_payload = json.loads((output_dir / "scores" / "leaderboard.json").read_text())
    compared_rows = [
        row
        for row in leaderboard_payload["leaderboard"]
        if row["input_condition"] == "image_table_summary"
    ]

    assert len(compared_rows) == 5
    assert compared_rows[0]["artifact_count"] > 0
    assert all(row["artifact_count"] == compared_rows[0]["artifact_count"] for row in compared_rows)
    assert {row.get("semantic_level") for row in compared_rows if row["arm"] == "B"} == {
        "L1",
        "L2L3",
        "L1L2L3",
    }


def test_cli_resume_prunes_unexpected_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "benchmark-output"

    assert main(["--fixture-only", "--output-dir", str(output_dir)]) == 0

    for folder in ("generations", "extracted_claims", "verifications", "arm_c_traces"):
        orphan_path = output_dir / folder / "orphan.json"
        orphan_path.write_text("{}", encoding="utf-8")

    exit_code = main(["--fixture-only", "--output-dir", str(output_dir), "--resume"])

    assert exit_code == 0
    assert not (output_dir / "generations" / "orphan.json").exists()
    assert not (output_dir / "extracted_claims" / "orphan.json").exists()
    assert not (output_dir / "verifications" / "orphan.json").exists()
    assert not (output_dir / "arm_c_traces" / "orphan.json").exists()
