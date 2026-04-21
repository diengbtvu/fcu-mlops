from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from benchmarking.selection import BENCHMARK_SELECTED_FILENAME, build_selected_benchmark_explanations

BENCHMARK_DIRNAME = "benchmark_eval"
BENCHMARK_TIMEOUT_SECONDS = max(300, int(os.getenv("BENCHMARK_TIMEOUT_SECONDS", "3600")))
BENCHMARK_RUNTIME_SCOPE = str(os.getenv("BENCHMARK_RUNTIME_SCOPE", "full_bundle")).strip().lower() or "full_bundle"
BENCHMARK_RUNTIME_ARMS = str(os.getenv("BENCHMARK_RUNTIME_ARMS", "A,B,C")).strip() or "A,B,C"
BENCHMARK_RUNTIME_CONDITIONS = (
    str(os.getenv("BENCHMARK_RUNTIME_CONDITIONS", "image_table_summary")).strip()
    or "image_table_summary"
)
PHASE1_CORE_BUNDLE_FILES = (
    "summary.json",
    "bundle_manifest.json",
    "llm_explanations.json",
    "results_summary.txt",
    "analysis_summary_report.txt",
    "table_model_comparison.csv",
    "table1_incremental_results.csv",
    "gra_ranking.json",
    "fig5_model_comparison.png",
    "fig_model_comparison_bars.png",
    "fig6ab_mse_r2_features.png",
    "fig3a_gra_ranking.png",
    "fig_gra_ranking.png",
)


def _report_dir(report_info: Dict[str, Any], report_root: str | Path | None = None) -> Path:
    report_id = str(report_info.get("report_id") or "").strip()
    if not report_id:
        raise RuntimeError("Training report metadata is missing report_id.")

    root = Path(report_root or Path(__file__).resolve().parents[1] / "reports")
    report_dir = root / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_report_benchmark_snapshot(
    report_info: Dict[str, Any],
    report_root: str | Path | None = None,
) -> None:
    report_dir = _report_dir(report_info, report_root)
    summary_path = report_dir / "summary.json"
    summary = _read_json(summary_path)
    if not summary:
        return

    summary.pop("benchmark_summary", None)
    summary.pop("selected_benchmark_explanations", None)

    files = dict(summary.get("files") or {})
    for key in (
        "benchmark_manifest",
        "benchmark_run_metadata",
        "benchmark_leaderboard_json",
        "benchmark_leaderboard_csv",
        "benchmark_selected_explanations",
    ):
        files.pop(key, None)
    summary["files"] = files
    _write_json(summary_path, summary)

    report_info.pop("benchmark_summary", None)
    report_info.pop("selected_benchmark_explanations", None)
    current_files = dict(report_info.get("files") or {})
    for key in (
        "benchmark_manifest",
        "benchmark_run_metadata",
        "benchmark_leaderboard_json",
        "benchmark_leaderboard_csv",
        "benchmark_selected_explanations",
    ):
        current_files.pop(key, None)
    report_info["files"] = current_files


@contextmanager
def _staged_runtime_bundle(report_dir: Path) -> Any:
    if BENCHMARK_RUNTIME_SCOPE != "phase1_core":
        yield report_dir
        return

    with tempfile.TemporaryDirectory(prefix="benchmark_runtime_phase1_") as temp_dir:
        staged_dir = Path(temp_dir)
        for name in PHASE1_CORE_BUNDLE_FILES:
            source_path = report_dir / name
            if source_path.exists():
                shutil.copy2(source_path, staged_dir / name)
        yield staged_dir


def update_report_benchmark_status(
    report_info: Dict[str, Any],
    status: str,
    message: str = "",
    report_root: str | Path | None = None,
    started_at: str | None = None,
    progress: float | None = None,
    phase: str | None = None,
    step_index: int | None = None,
    total_steps: int | None = None,
    current_items: list[str] | None = None,
    output_dir: str | None = None,
) -> Dict[str, Any]:
    report_dir = _report_dir(report_info, report_root)
    summary_path = report_dir / "summary.json"

    payload: Dict[str, Any] = {
        "status": str(status).strip() or "pending",
        "message": str(message or "").strip(),
        "updated_at": datetime.now().isoformat(),
    }

    existing: Dict[str, Any] = {}
    summary = _read_json(summary_path)
    if summary:
        existing = dict(summary.get("benchmark_status") or {})

    payload["started_at"] = started_at or existing.get("started_at") or payload["updated_at"]

    optional_fields = {
        "progress": max(0.0, min(100.0, round(float(progress), 1))) if progress is not None else existing.get("progress"),
        "phase": str(phase).strip() if phase is not None else existing.get("phase"),
        "step_index": int(step_index) if step_index is not None else existing.get("step_index"),
        "total_steps": int(total_steps) if total_steps is not None else existing.get("total_steps"),
        "current_items": list(current_items) if current_items is not None else existing.get("current_items"),
        "output_dir": str(output_dir).strip() if output_dir is not None else existing.get("output_dir"),
    }
    for key, value in optional_fields.items():
        if value is not None:
            payload[key] = value

    if summary:
        summary["benchmark_status"] = payload
        _write_json(summary_path, summary)

    report_info["benchmark_status"] = payload
    return payload


def _benchmark_file_map(report_dir: Path, benchmark_dir: Path) -> dict[str, str]:
    file_map = {
        "benchmark_manifest": str((benchmark_dir / "manifest.jsonl").relative_to(report_dir)),
        "benchmark_run_metadata": str((benchmark_dir / "run_metadata.json").relative_to(report_dir)),
        "benchmark_leaderboard_json": str((benchmark_dir / "scores" / "leaderboard.json").relative_to(report_dir)),
        "benchmark_leaderboard_csv": str((benchmark_dir / "scores" / "leaderboard.csv").relative_to(report_dir)),
    }
    selected_path = benchmark_dir / BENCHMARK_SELECTED_FILENAME
    if selected_path.exists():
        file_map["benchmark_selected_explanations"] = str(selected_path.relative_to(report_dir))
    return file_map


def publish_benchmark_results(
    report_info: Dict[str, Any],
    report_root: str | Path | None = None,
    benchmark_dirname: str = BENCHMARK_DIRNAME,
) -> Dict[str, Any]:
    report_dir = _report_dir(report_info, report_root)
    benchmark_dir = report_dir / benchmark_dirname
    summary_path = report_dir / "summary.json"
    summary = _read_json(summary_path)

    leaderboard_payload = _read_json(benchmark_dir / "scores" / "leaderboard.json")
    run_metadata = _read_json(benchmark_dir / "run_metadata.json")
    leaderboard_rows = leaderboard_payload.get("leaderboard")
    if not isinstance(leaderboard_rows, list):
        leaderboard_rows = []
    artifact_scores = leaderboard_payload.get("artifact_scores")
    if not isinstance(artifact_scores, list):
        artifact_scores = []

    selected_payload, selection_warnings = build_selected_benchmark_explanations(
        benchmark_dir,
        fallback_payload=summary.get("llm_explanations"),
    )
    selected_output_path = benchmark_dir / BENCHMARK_SELECTED_FILENAME
    if selected_payload:
        _write_json(selected_output_path, selected_payload)
        summary["selected_benchmark_explanations"] = selected_payload
        report_info["selected_benchmark_explanations"] = selected_payload
    else:
        if selected_output_path.exists():
            selected_output_path.unlink()
        summary.pop("selected_benchmark_explanations", None)
        report_info.pop("selected_benchmark_explanations", None)

    file_map = _benchmark_file_map(report_dir, benchmark_dir)
    files = dict(summary.get("files") or report_info.get("files") or {})
    files.update(file_map)
    summary["files"] = files

    benchmark_summary: Dict[str, Any] = {
        "generated_at": run_metadata.get("created_at"),
        "artifact_count": run_metadata.get("artifact_count"),
        "generation_count": run_metadata.get("generation_count"),
        "baseline_arm": run_metadata.get("baseline_arm"),
        "output_dir": benchmark_dirname,
        "leaderboard_preview": leaderboard_rows[:6],
        "row_count": len(leaderboard_rows),
        "artifact_score_count": len(artifact_scores),
        "warnings": list(run_metadata.get("warnings") or []) + selection_warnings,
        "best_overall": leaderboard_rows[0] if leaderboard_rows else None,
        "baseline_row": next(
            (
                row
                for row in leaderboard_rows
                if str(row.get("arm") or "").strip() == str(run_metadata.get("baseline_arm") or "").strip()
            ),
            None,
        ),
        "files": file_map,
        "selected_explanations": {
            "arm": selected_payload.get("selected_arm"),
            "input_condition": selected_payload.get("selected_condition"),
            "asset_count": len(selected_payload.get("assets") or {}),
            "provider": selected_payload.get("provider"),
            "model": selected_payload.get("model"),
        }
        if selected_payload
        else None,
    }
    summary["benchmark_summary"] = benchmark_summary
    _write_json(summary_path, summary)

    report_info["files"] = files
    report_info["benchmark_summary"] = benchmark_summary
    return benchmark_summary


def run_report_benchmark(
    report_info: Dict[str, Any],
    report_root: str | Path | None = None,
    benchmark_dirname: str = BENCHMARK_DIRNAME,
) -> Dict[str, Any]:
    report_dir = _report_dir(report_info, report_root)
    benchmark_dir = report_dir / benchmark_dirname
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_benchmark.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Benchmark CLI is missing: {script_path}")

    _clear_report_benchmark_snapshot(
        report_info=report_info,
        report_root=report_root,
    )

    started_at = datetime.now().isoformat()
    update_report_benchmark_status(
        report_info=report_info,
        status="pending",
        message="Benchmark evaluation is queued.",
        report_root=report_root,
        started_at=started_at,
        progress=5,
        phase="queued",
        step_index=1,
        total_steps=3,
        current_items=["bundle manifest", "gold facts", "claim verification"],
        output_dir=benchmark_dirname,
    )
    update_report_benchmark_status(
        report_info=report_info,
        status="pending",
        message="Running benchmark evaluation on the generated report bundle.",
        report_root=report_root,
        progress=20,
        phase="running",
        step_index=2,
        total_steps=3,
        current_items=["A/B/C generations", "baseline ingestion", "leaderboard scoring"],
        output_dir=benchmark_dirname,
    )

    try:
        with _staged_runtime_bundle(report_dir) as bundle_path:
            command = [
                sys.executable,
                str(script_path),
                "--bundle-path",
                str(bundle_path),
                "--output-dir",
                str(benchmark_dir),
                "--client",
                str(os.getenv("BENCHMARK_LLM_CLIENT", "openai")).strip() or "openai",
                "--arms",
                BENCHMARK_RUNTIME_ARMS,
                "--conditions",
                BENCHMARK_RUNTIME_CONDITIONS,
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=BENCHMARK_TIMEOUT_SECONDS,
            )
    except subprocess.TimeoutExpired as exc:
        message = f"Benchmark timed out after {exc.timeout} seconds."
        update_report_benchmark_status(
            report_info=report_info,
            status="error",
            message=message,
            report_root=report_root,
            progress=100,
            phase="error",
            step_index=3,
            total_steps=3,
            output_dir=benchmark_dirname,
        )
        raise RuntimeError(message) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        if detail:
            detail = detail.splitlines()[-1]
        message = detail or "Benchmark CLI exited with a non-zero status."
        update_report_benchmark_status(
            report_info=report_info,
            status="error",
            message=message,
            report_root=report_root,
            progress=100,
            phase="error",
            step_index=3,
            total_steps=3,
            output_dir=benchmark_dirname,
        )
        raise RuntimeError(message)

    update_report_benchmark_status(
        report_info=report_info,
        status="pending",
        message="Benchmark outputs generated. Saving report summary.",
        report_root=report_root,
        progress=90,
        phase="finalizing",
        step_index=3,
        total_steps=3,
        current_items=["leaderboard", "run metadata"],
        output_dir=benchmark_dirname,
    )
    benchmark_summary = publish_benchmark_results(
        report_info=report_info,
        report_root=report_root,
        benchmark_dirname=benchmark_dirname,
    )
    update_report_benchmark_status(
        report_info=report_info,
        status="success",
        message="Benchmark evaluation completed successfully.",
        report_root=report_root,
        progress=100,
        phase="completed",
        step_index=3,
        total_steps=3,
        current_items=["leaderboard", "run metadata"],
        output_dir=benchmark_dirname,
    )
    return benchmark_summary
