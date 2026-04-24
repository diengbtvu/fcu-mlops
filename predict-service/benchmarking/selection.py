from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import slugify

SELECTABLE_ARMS = ("A", "B", "C")
BENCHMARK_SELECTED_FILENAME = "selected_explanations.json"

CORE_ARTIFACT_ASSET_KEYS: dict[str, tuple[str, ...]] = {
    "model_comparison/main": (
        "metrics_overview",
        "model_comparison_table",
    ),
    "incremental_feature_analysis/main": (
        "table1_incremental_results",
    ),
    "feature_ranking/gra": (
        "gra_ranking",
    ),
}

OVERVIEW_PRIORITY_KEYS = (
    "metrics_overview",
    "fig5_model_comparison",
    "model_comparison_bars",
    "fig3_feature_analysis",
    "fig3a_gra_ranking",
    "feature_importance",
    "fig6ab_mse_r2_features",
    "table1_incremental_results",
    "correlation_heatmap",
    "predicted_vs_actual",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def select_best_benchmark_row(
    leaderboard_rows: list[dict[str, Any]],
    *,
    allowed_arms: tuple[str, ...] = SELECTABLE_ARMS,
) -> dict[str, Any] | None:
    for row in leaderboard_rows:
        arm = str(row.get("arm") or "").strip()
        if arm in allowed_arms:
            return row
    return None


def _generation_file_name(
    artifact_id: str,
    arm: str,
    condition: str,
    semantic_level: str | None = None,
) -> str:
    name_parts = [artifact_id, arm]
    if semantic_level:
        name_parts.append(semantic_level)
    name_parts.append(condition)
    return f"{slugify('_'.join(name_parts))}.json"


def _load_selected_generation(
    benchmark_dir: Path,
    artifact_id: str,
    arm: str,
    condition: str,
    semantic_level: str | None = None,
) -> dict[str, Any]:
    path = benchmark_dir / "generations" / _generation_file_name(
        artifact_id,
        arm,
        condition,
        semantic_level,
    )
    return _read_json(path)


def _asset_payload(text: str) -> dict[str, str]:
    return {
        "en": text,
        "zh_TW": "",
    }


def _overview_payload(
    assets: dict[str, dict[str, str]],
) -> dict[str, str]:
    selected_texts: list[str] = []
    for key in OVERVIEW_PRIORITY_KEYS:
        asset = assets.get(key) or {}
        text = str(asset.get("en") or "").strip()
        if text and text not in selected_texts:
            selected_texts.append(text)
        if len(selected_texts) >= 3:
            break

    if selected_texts:
        combined = "\n\n".join(selected_texts)
        return {
            "en": combined,
            "zh_TW": "",
        }
    return {"en": "", "zh_TW": ""}


def build_selected_benchmark_explanations(
    benchmark_dir: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    leaderboard_payload = _read_json(benchmark_dir / "scores" / "leaderboard.json")
    run_metadata = _read_json(benchmark_dir / "run_metadata.json")
    manifest_rows = _read_jsonl(benchmark_dir / "manifest.jsonl")
    leaderboard_rows = leaderboard_payload.get("leaderboard")
    if not isinstance(leaderboard_rows, list):
        leaderboard_rows = []

    selected_row = select_best_benchmark_row(leaderboard_rows)
    if selected_row is None:
        warnings.append("No eligible A/B/C benchmark row was available for report selection.")
        return None, warnings

    selected_arm = str(selected_row.get("arm") or "").strip()
    selected_condition = str(selected_row.get("input_condition") or "").strip()
    selected_semantic_level = str(selected_row.get("semantic_level") or "").strip() or None
    assets: dict[str, dict[str, str]] = {}

    for row in manifest_rows:
        artifact_id = str(row.get("artifact_id") or "").strip()
        if not artifact_id:
            continue
        generation = _load_selected_generation(
            benchmark_dir=benchmark_dir,
            artifact_id=artifact_id,
            arm=selected_arm,
            condition=selected_condition,
            semantic_level=selected_semantic_level,
        )
        if not generation:
            warnings.append(
                f"Missing selected generation for {artifact_id} ({selected_arm}/{selected_condition})."
            )
            continue

        explanation_text = str(
            generation.get("explanation_full") or generation.get("explanation_short") or ""
        ).strip()
        if not explanation_text:
            warnings.append(
                f"Selected generation for {artifact_id} did not include explanation text."
            )
            continue

        asset_key = str(row.get("asset_key") or "").strip()
        if asset_key:
            assets.setdefault(asset_key, _asset_payload(explanation_text))

        artifact_type = str(row.get("artifact_type") or "").strip()
        for derived_key in CORE_ARTIFACT_ASSET_KEYS.get(artifact_type, ()):
            assets.setdefault(derived_key, _asset_payload(explanation_text))

    if not assets:
        warnings.append("The selected benchmark row did not produce any website explanation assets.")
        return None, warnings

    payload = {
        "provider": "benchmark_selected",
        "model": run_metadata.get("client_model"),
        "generated_at": run_metadata.get("created_at"),
        "selection_method": "best_leaderboard_row",
        "selected_arm": selected_arm,
        "selected_condition": selected_condition,
        "selected_semantic_level": selected_semantic_level,
        "selected_row": selected_row,
        "overview": _overview_payload(assets),
        "assets": assets,
    }
    return payload, warnings
