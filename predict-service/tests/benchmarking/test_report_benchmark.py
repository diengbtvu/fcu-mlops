from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_report_benchmark_module():
    module_path = Path(__file__).resolve().parents[2] / "app" / "utils" / "report_benchmark.py"
    spec = importlib.util.spec_from_file_location("test_report_benchmark_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_staged_runtime_bundle_uses_full_report_dir_by_default(tmp_path: Path, monkeypatch) -> None:
    report_benchmark = _load_report_benchmark_module()
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    (report_dir / "summary.json").write_text(json.dumps({"files": {"summary": "summary.json"}}), encoding="utf-8")
    (report_dir / "asset_evidence.json").write_text(json.dumps({"assets": []}), encoding="utf-8")

    monkeypatch.setattr(report_benchmark, "BENCHMARK_RUNTIME_SCOPE", "full_bundle")

    with report_benchmark._staged_runtime_bundle(report_dir) as staged_dir:
        assert staged_dir == report_dir
        assert (staged_dir / "asset_evidence.json").exists()


def test_staged_runtime_bundle_can_still_limit_to_phase1_core(tmp_path: Path, monkeypatch) -> None:
    report_benchmark = _load_report_benchmark_module()
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    for name in (
        "summary.json",
        "bundle_manifest.json",
        "llm_explanations.json",
        "table_model_comparison.csv",
        "table1_incremental_results.csv",
        "gra_ranking.json",
        "asset_evidence.json",
    ):
        (report_dir / name).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(report_benchmark, "BENCHMARK_RUNTIME_SCOPE", "phase1_core")

    with report_benchmark._staged_runtime_bundle(report_dir) as staged_dir:
        assert staged_dir != report_dir
        assert (staged_dir / "summary.json").exists()
        assert (staged_dir / "table_model_comparison.csv").exists()
        assert not (staged_dir / "asset_evidence.json").exists()


def test_clear_report_benchmark_snapshot_removes_stale_summary_and_files(tmp_path: Path) -> None:
    report_benchmark = _load_report_benchmark_module()
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    summary_path = report_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "files": {
                    "summary": "summary.json",
                    "benchmark_manifest": "benchmark_eval/manifest.jsonl",
                    "benchmark_leaderboard_json": "benchmark_eval/scores/leaderboard.json",
                    "benchmark_per_chart_json": "benchmark_eval/scores/per_chart_benchmark.json",
                    "benchmark_selected_explanations": "benchmark_eval/selected_explanations.json",
                },
                "benchmark_summary": {"generated_at": "2026-04-16T00:00:00Z"},
                "selected_benchmark_explanations": {"overview": {"en": "stale"}},
            }
        ),
        encoding="utf-8",
    )
    report_info = {
        "report_id": report_dir.name,
        "files": {
            "benchmark_manifest": "benchmark_eval/manifest.jsonl",
            "benchmark_per_chart_json": "benchmark_eval/scores/per_chart_benchmark.json",
            "benchmark_selected_explanations": "benchmark_eval/selected_explanations.json",
        },
        "benchmark_summary": {"generated_at": "2026-04-16T00:00:00Z"},
        "selected_benchmark_explanations": {"overview": {"en": "stale"}},
    }

    report_benchmark._clear_report_benchmark_snapshot(report_info, report_root=tmp_path)

    updated = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "benchmark_summary" not in updated
    assert "selected_benchmark_explanations" not in updated
    assert "benchmark_manifest" not in updated["files"]
    assert "benchmark_per_chart_json" not in updated["files"]
    assert "benchmark_selected_explanations" not in updated["files"]
    assert "benchmark_summary" not in report_info
    assert "selected_benchmark_explanations" not in report_info


def test_reset_benchmark_output_dir_removes_stale_outputs(tmp_path: Path) -> None:
    report_benchmark = _load_report_benchmark_module()
    benchmark_dir = tmp_path / "benchmark_eval"
    (benchmark_dir / "generations").mkdir(parents=True)
    (benchmark_dir / "generations" / "old.json").write_text("{}", encoding="utf-8")

    report_benchmark._reset_benchmark_output_dir(benchmark_dir)

    assert benchmark_dir.exists()
    assert list(benchmark_dir.iterdir()) == []


def test_running_progress_payload_uses_live_file_counts(tmp_path: Path) -> None:
    report_benchmark = _load_report_benchmark_module()
    benchmark_dir = tmp_path / "benchmark_eval"
    for name in ("gold", "generations", "extracted_claims", "verifications", "scores"):
        (benchmark_dir / name).mkdir(parents=True, exist_ok=True)
    (benchmark_dir / "manifest.jsonl").write_text("{}", encoding="utf-8")
    for idx in range(3):
        (benchmark_dir / "gold" / f"gold_{idx}.json").write_text("{}", encoding="utf-8")
    for idx in range(5):
        (benchmark_dir / "generations" / f"generation_{idx}.json").write_text("{}", encoding="utf-8")
    for idx in range(4):
        (benchmark_dir / "extracted_claims" / f"claims_{idx}.json").write_text("{}", encoding="utf-8")
        (benchmark_dir / "verifications" / f"verification_{idx}.json").write_text("{}", encoding="utf-8")

    payload = report_benchmark._running_progress_payload(
        benchmark_dir=benchmark_dir,
        expected_generation_count=10,
    )

    assert payload["progress"] > 40
    assert "4/10" in payload["message"]
    assert payload["current_items"][0] == "generated 5/10"
    assert payload["current_items"][1] == "processed 4/10"
    assert payload["current_items"][-1].startswith("latest verification:")


def test_effective_benchmark_timeout_scales_with_expected_runs(monkeypatch) -> None:
    report_benchmark = _load_report_benchmark_module()
    monkeypatch.setattr(report_benchmark, "BENCHMARK_TIMEOUT_SECONDS", 3600)
    monkeypatch.setattr(report_benchmark, "BENCHMARK_SECONDS_PER_GENERATION", 45)

    assert report_benchmark._effective_benchmark_timeout(120) == 5400
    assert report_benchmark._effective_benchmark_timeout(None) == 3600


def test_benchmark_client_name_accepts_groq_override() -> None:
    report_benchmark = _load_report_benchmark_module()

    assert report_benchmark._benchmark_client_name("groq") == "groq"
