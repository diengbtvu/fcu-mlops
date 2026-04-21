from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchmarking.cli import main
from benchmarking.schemas import BASELINE_ARM


def test_cli_fixture_only_run_writes_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "benchmark-output"

    exit_code = main(["--fixture-only", "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "manifest.jsonl").exists()
    assert (output_dir / "gold").is_dir()
    assert (output_dir / "generations").is_dir()
    assert (output_dir / "extracted_claims").is_dir()
    assert (output_dir / "verifications").is_dir()
    assert (output_dir / "scores" / "leaderboard.json").exists()
    assert (output_dir / "scores" / "leaderboard.csv").exists()
    assert (output_dir / "run_metadata.json").exists()
    assert any(f"_{BASELINE_ARM.lower()}_" in path.name for path in (output_dir / "generations").iterdir())

    leaderboard_payload = json.loads((output_dir / "scores" / "leaderboard.json").read_text())
    assert any(row["arm"] == BASELINE_ARM for row in leaderboard_payload["leaderboard"])
    metadata = json.loads((output_dir / "run_metadata.json").read_text())
    assert metadata["artifact_count"] > 3
    assert metadata["client"] == "fixture"
    assert metadata["client_model"] is None


def test_cli_skips_baseline_when_llm_explanations_is_missing(tmp_path: Path) -> None:
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
    assert metadata["baseline_arm"] is None
    assert BASELINE_ARM not in metadata["arms"]

    leaderboard_payload = json.loads((output_dir / "scores" / "leaderboard.json").read_text())
    assert all(row["arm"] != BASELINE_ARM for row in leaderboard_payload["leaderboard"])


def test_cli_fails_clearly_on_legacy_baseline_payload(tmp_path: Path) -> None:
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

    assert exit_code == 2
