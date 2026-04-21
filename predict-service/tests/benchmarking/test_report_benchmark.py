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
    assert "benchmark_selected_explanations" not in updated["files"]
    assert "benchmark_summary" not in report_info
    assert "selected_benchmark_explanations" not in report_info
