from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from benchmarking.chart_reporting import (
    PER_CHART_CSV_FILENAME,
    PER_CHART_JSON_FILENAME,
    write_per_chart_benchmark_outputs,
)
from groq_key_pool import parse_groq_api_keys
from benchmarking.manifest import build_manifest
from benchmarking.schemas import SUPPORTED_SEMANTIC_LEVELS
from benchmarking.selection import BENCHMARK_SELECTED_FILENAME, build_selected_benchmark_explanations

BENCHMARK_DIRNAME = "benchmark_eval"
BENCHMARK_TIMEOUT_SECONDS = max(300, int(os.getenv("BENCHMARK_TIMEOUT_SECONDS", "7200")))
BENCHMARK_SECONDS_PER_GENERATION = max(
    10,
    int(os.getenv("BENCHMARK_SECONDS_PER_GENERATION", "75")),
)
BENCHMARK_RUNTIME_RESUME = str(os.getenv("BENCHMARK_RUNTIME_RESUME", "0")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
BENCHMARK_PROGRESS_POLL_SECONDS = max(
    1.0,
    float(os.getenv("BENCHMARK_PROGRESS_POLL_SECONDS", "5")),
)
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


def _benchmark_client_name(provider_override: str | None = None) -> str:
    client_name = str(
        provider_override
        or os.getenv("BENCHMARK_LLM_CLIENT")
        or os.getenv("REPORT_LLM_PROVIDER")
        or "openai"
    ).strip().lower()
    if client_name in {"fixture", "openai", "ollama", "groq"}:
        return client_name
    return "openai"


def _parse_csv_items(raw_value: str) -> list[str]:
    return [item.strip() for item in str(raw_value or "").split(",") if item.strip()]


def _benchmark_runtime_arms() -> list[str]:
    return _parse_csv_items(BENCHMARK_RUNTIME_ARMS)


def _benchmark_runtime_conditions() -> list[str]:
    return _parse_csv_items(BENCHMARK_RUNTIME_CONDITIONS)


def _benchmark_runtime_levels() -> list[str]:
    raw_levels = str(os.getenv("BENCHMARK_RUNTIME_LEVELS", "")).strip()
    if not raw_levels:
        return list(SUPPORTED_SEMANTIC_LEVELS)
    levels = [level for level in _parse_csv_items(raw_levels) if level in SUPPORTED_SEMANTIC_LEVELS]
    return levels or list(SUPPORTED_SEMANTIC_LEVELS)


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
        "benchmark_per_chart_json",
        "benchmark_per_chart_csv",
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
        "benchmark_per_chart_json",
        "benchmark_per_chart_csv",
        "benchmark_selected_explanations",
    ):
        current_files.pop(key, None)
    report_info["files"] = current_files


def _reset_benchmark_output_dir(benchmark_dir: Path) -> None:
    if benchmark_dir.exists():
        shutil.rmtree(benchmark_dir)
    benchmark_dir.mkdir(parents=True, exist_ok=True)


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
        "benchmark_per_chart_json": str((benchmark_dir / "scores" / PER_CHART_JSON_FILENAME).relative_to(report_dir)),
        "benchmark_per_chart_csv": str((benchmark_dir / "scores" / PER_CHART_CSV_FILENAME).relative_to(report_dir)),
    }
    selected_path = benchmark_dir / BENCHMARK_SELECTED_FILENAME
    if selected_path.exists():
        file_map["benchmark_selected_explanations"] = str(selected_path.relative_to(report_dir))
    return file_map


def _count_output_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for child in path.iterdir() if child.is_file())


def _latest_output_name(path: Path) -> str | None:
    if not path.exists():
        return None
    files = [child for child in path.iterdir() if child.is_file()]
    if not files:
        return None
    files.sort(key=lambda child: (child.stat().st_mtime, child.name))
    return files[-1].name


def _read_json_any(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _verification_row_count(path: Path) -> int:
    payload = _read_json_any(path)
    if isinstance(payload, list):
        return len([item for item in payload if isinstance(item, dict)])
    if isinstance(payload, dict):
        rows = payload.get("verifications")
        if isinstance(rows, list):
            return len([item for item in rows if isinstance(item, dict)])
    return 0


def _generation_is_failed(path: Path) -> bool:
    payload = _read_json_any(path)
    if not isinstance(payload, dict):
        return False
    if str(payload.get("generation_stage") or "").strip().lower() == "failed":
        return True
    text = " ".join(
        str(payload.get(key) or "")
        for key in ("explanation_short", "explanation_full")
    ).lower()
    return (
        "correction pipeline failed" in text
        or "failed before producing" in text
        or "benchmark generation failed" in text
    )


def _verification_output_counts(benchmark_dir: Path) -> dict[str, int]:
    verification_dir = benchmark_dir / "verifications"
    generation_dir = benchmark_dir / "generations"
    counts = {
        "processed": 0,
        "valid": 0,
        "empty": 0,
        "failed_generations": 0,
    }
    if not verification_dir.exists():
        return counts

    for verification_path in verification_dir.iterdir():
        if not verification_path.is_file() or verification_path.suffix != ".json":
            continue
        counts["processed"] += 1
        generation_failed = _generation_is_failed(generation_dir / verification_path.name)
        row_count = _verification_row_count(verification_path)
        if generation_failed:
            counts["failed_generations"] += 1
        if row_count <= 0:
            counts["empty"] += 1
        if row_count > 0 and not generation_failed:
            counts["valid"] += 1
    return counts


def _estimate_generation_count(
    bundle_path: Path,
    arms: list[str],
    conditions: list[str],
    semantic_levels: list[str],
) -> int | None:
    if not arms or not conditions:
        return None

    records = build_manifest(bundle_path)
    runs_per_artifact = 0
    for arm in arms:
        if arm == "B":
            runs_per_artifact += len(conditions) * max(1, len(semantic_levels))
        else:
            runs_per_artifact += len(conditions)

    if runs_per_artifact <= 0:
        return None
    return len(records) * runs_per_artifact


def _effective_benchmark_timeout(expected_generation_count: int | None) -> int:
    if expected_generation_count is None or expected_generation_count <= 0:
        return BENCHMARK_TIMEOUT_SECONDS
    return max(
        BENCHMARK_TIMEOUT_SECONDS,
        expected_generation_count * BENCHMARK_SECONDS_PER_GENERATION,
    )


def _running_progress_payload(
    benchmark_dir: Path,
    expected_generation_count: int | None,
) -> dict[str, Any]:
    manifest_exists = (benchmark_dir / "manifest.jsonl").exists()
    run_metadata_exists = (benchmark_dir / "run_metadata.json").exists()
    score_count = _count_output_files(benchmark_dir / "scores")
    generation_count = _count_output_files(benchmark_dir / "generations")
    claim_count = _count_output_files(benchmark_dir / "extracted_claims")
    verification_counts = _verification_output_counts(benchmark_dir)
    verification_count = verification_counts["processed"]
    valid_verification_count = verification_counts["valid"]
    failed_generation_count = verification_counts["failed_generations"]
    gold_count = _count_output_files(benchmark_dir / "gold")
    latest_generation = _latest_output_name(benchmark_dir / "generations")
    latest_verification = _latest_output_name(benchmark_dir / "verifications")

    progress = 20.0
    message = "Running benchmark evaluation on the generated report bundle."
    current_items = ["bundle manifest", "gold facts", "claim verification"]

    if manifest_exists:
        progress = max(progress, 24.0)
    if gold_count:
        progress = max(progress, 28.0)

    if expected_generation_count and expected_generation_count > 0:
        generated_ratio = min(1.0, generation_count / expected_generation_count)
        verified_ratio = min(1.0, verification_count / expected_generation_count)
        progress = max(progress, 28.0 + (generated_ratio * 45.0))
        progress = max(progress, 28.0 + (verified_ratio * 57.0))
        message = (
            "Running benchmark evaluation on the generated report bundle "
            f"({verification_count}/{expected_generation_count} processed; "
            f"{valid_verification_count} valid verifications"
            + (f"; {failed_generation_count} failed generations" if failed_generation_count else "")
            + ")."
        )
        current_items = [
            f"generated {generation_count}/{expected_generation_count}",
            f"processed {verification_count}/{expected_generation_count}",
            f"valid verifications {valid_verification_count}/{expected_generation_count}",
            "leaderboard scoring pending",
        ]
    elif generation_count or claim_count or verification_count:
        completed = max(generation_count, claim_count, verification_count)
        message = (
            "Running benchmark evaluation on the generated report bundle "
            f"({completed} intermediate outputs written)."
        )
        current_items = [
            f"generations {generation_count}",
            f"claims {claim_count}",
            f"verifications {verification_count}",
        ]

    if latest_verification:
        current_items[-1] = f"latest verification: {latest_verification}"
    elif latest_generation:
        current_items[-1] = f"latest generation: {latest_generation}"

    if score_count or run_metadata_exists:
        progress = max(progress, 90.0)
        current_items = ["leaderboard", "run metadata", "publishing summary"]

    return {
        "progress": round(min(90.0, progress), 1),
        "message": message,
        "current_items": current_items,
    }


def publish_benchmark_results(
    report_info: Dict[str, Any],
    report_root: str | Path | None = None,
    benchmark_dirname: str = BENCHMARK_DIRNAME,
) -> Dict[str, Any]:
    report_dir = _report_dir(report_info, report_root)
    benchmark_dir = report_dir / benchmark_dirname
    summary_path = report_dir / "summary.json"
    summary = _read_json(summary_path)

    per_chart_payload = write_per_chart_benchmark_outputs(benchmark_dir)

    leaderboard_payload = _read_json(benchmark_dir / "scores" / "leaderboard.json")
    run_metadata = _read_json(benchmark_dir / "run_metadata.json")
    leaderboard_rows = leaderboard_payload.get("leaderboard")
    if not isinstance(leaderboard_rows, list):
        leaderboard_rows = []
    artifact_scores = leaderboard_payload.get("artifact_scores")
    if not isinstance(artifact_scores, list):
        artifact_scores = []

    selected_payload, selection_warnings = build_selected_benchmark_explanations(benchmark_dir)
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
        "output_dir": benchmark_dirname,
        "leaderboard_preview": leaderboard_rows[:6],
        "row_count": len(leaderboard_rows),
        "artifact_score_count": len(artifact_scores),
        "warnings": list(run_metadata.get("warnings") or []) + selection_warnings,
        "best_overall": leaderboard_rows[0] if leaderboard_rows else None,
        "per_chart": {
            "artifact_count": per_chart_payload.get("artifact_count"),
            "chart_count": per_chart_payload.get("chart_count"),
            "core_artifact_count": per_chart_payload.get("core_artifact_count"),
            "coverage_gap_count": len(per_chart_payload.get("coverage_gaps") or []),
            "coverage_gap_preview": list(per_chart_payload.get("coverage_gaps") or [])[:6],
            "best_preview": list(per_chart_payload.get("best_rows") or [])[:6],
            "hardest_preview": list(per_chart_payload.get("hardest_rows") or [])[:6],
        },
        "files": file_map,
        "selected_explanations": {
            "arm": selected_payload.get("selected_arm"),
            "input_condition": selected_payload.get("selected_condition"),
            "semantic_level": selected_payload.get("selected_semantic_level"),
            "asset_count": len(selected_payload.get("assets") or {}),
            "provider": selected_payload.get("provider"),
            "model": selected_payload.get("model"),
            "selection_method": selected_payload.get("selection_method"),
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
    llm_provider: str | None = None,
    llm_model: str | None = None,
    groq_api_keys: Any | None = None,
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
    if BENCHMARK_RUNTIME_RESUME:
        benchmark_dir.mkdir(parents=True, exist_ok=True)
    else:
        _reset_benchmark_output_dir(benchmark_dir)

    runtime_arms = _benchmark_runtime_arms()
    runtime_conditions = _benchmark_runtime_conditions()
    runtime_levels = _benchmark_runtime_levels()
    runtime_client = _benchmark_client_name(llm_provider)

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
        current_items=["A/B/C generations", "claim verification", "leaderboard scoring"],
        output_dir=benchmark_dirname,
    )

    try:
        with _staged_runtime_bundle(report_dir) as bundle_path:
            try:
                expected_generation_count = _estimate_generation_count(
                    bundle_path=bundle_path,
                    arms=runtime_arms,
                    conditions=runtime_conditions,
                    semantic_levels=runtime_levels,
                )
            except Exception:
                expected_generation_count = None
            timeout_seconds = _effective_benchmark_timeout(expected_generation_count)

            command = [
                sys.executable,
                str(script_path),
                "--bundle-path",
                str(bundle_path),
                "--output-dir",
                str(benchmark_dir),
                "--client",
                runtime_client,
                "--arms",
                BENCHMARK_RUNTIME_ARMS,
                "--conditions",
                BENCHMARK_RUNTIME_CONDITIONS,
            ]
            if "B" in runtime_arms:
                command.extend(["--levels", ",".join(runtime_levels)])
            if BENCHMARK_RUNTIME_RESUME:
                command.append("--resume")

            with (
                tempfile.NamedTemporaryFile(
                    mode="w+",
                    encoding="utf-8",
                    prefix="benchmark_stdout_",
                    suffix=".log",
                ) as stdout_handle,
                tempfile.NamedTemporaryFile(
                    mode="w+",
                    encoding="utf-8",
                    prefix="benchmark_stderr_",
                    suffix=".log",
                ) as stderr_handle,
            ):
                child_env = os.environ.copy()
                child_env["BENCHMARK_LLM_CLIENT"] = runtime_client
                if llm_model:
                    if runtime_client == "groq":
                        child_env["GROQ_BENCHMARK_MODEL"] = str(llm_model)
                    elif runtime_client == "openai":
                        child_env["OPENAI_BENCHMARK_MODEL"] = str(llm_model)
                    elif runtime_client == "ollama":
                        child_env["OLLAMA_BENCHMARK_MODEL"] = str(llm_model)
                if runtime_client == "groq":
                    key_list = parse_groq_api_keys(groq_api_keys)
                    if key_list:
                        child_env["GROQ_API_KEYS"] = ",".join(key_list)

                process = subprocess.Popen(
                    command,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    text=True,
                    env=child_env,
                )
                deadline = time.monotonic() + timeout_seconds
                last_progress_signature: tuple[float, str, tuple[str, ...]] | None = None

                while True:
                    payload = _running_progress_payload(
                        benchmark_dir=benchmark_dir,
                        expected_generation_count=expected_generation_count,
                    )
                    current_signature = (
                        float(payload["progress"]),
                        str(payload["message"]),
                        tuple(str(item) for item in payload["current_items"]),
                    )
                    if current_signature != last_progress_signature:
                        update_report_benchmark_status(
                            report_info=report_info,
                            status="pending",
                            message=str(payload["message"]),
                            report_root=report_root,
                            progress=float(payload["progress"]),
                            phase="running",
                            step_index=2,
                            total_steps=3,
                            current_items=list(payload["current_items"]),
                            output_dir=benchmark_dirname,
                        )
                        last_progress_signature = current_signature

                    completed = process.poll()
                    if completed is not None:
                        break

                    if time.monotonic() >= deadline:
                        process.kill()
                        process.wait(timeout=30)
                        raise subprocess.TimeoutExpired(command, timeout_seconds)

                    time.sleep(BENCHMARK_PROGRESS_POLL_SECONDS)

                stdout_handle.flush()
                stderr_handle.flush()
                stdout_handle.seek(0)
                stderr_handle.seek(0)
                completed = subprocess.CompletedProcess(
                    args=command,
                    returncode=int(process.returncode or 0),
                    stdout=stdout_handle.read(),
                    stderr=stderr_handle.read(),
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
