from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .chart_assets import get_chart_asset_spec
from .io_utils import IMAGE_SUFFIXES, read_csv_rows, read_json, read_text
from .schemas import ArtifactInputs, ManifestRecord


@dataclass(frozen=True)
class ArtifactSpec:
    artifact_type: str
    chart_type: str
    required_files: tuple[str, ...]
    optional_chart_candidates: tuple[str, ...] = ()
    optional_summary_candidates: tuple[str, ...] = ()


ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        artifact_type="model_comparison/main",
        chart_type="bar_chart",
        required_files=("table_model_comparison.csv", "summary.json"),
        optional_chart_candidates=(
            "fig5_model_comparison.png",
            "fig_model_comparison_bars.png",
            "model_comparison_bars",
        ),
        optional_summary_candidates=("results_summary.txt", "analysis_summary"),
    ),
    ArtifactSpec(
        artifact_type="incremental_feature_analysis/main",
        chart_type="line_chart",
        required_files=("table1_incremental_results.csv",),
        optional_chart_candidates=("fig6ab_mse_r2_features.png",),
        optional_summary_candidates=("results_summary.txt", "analysis_summary"),
    ),
    ArtifactSpec(
        artifact_type="feature_ranking/gra",
        chart_type="ranking_chart",
        required_files=("gra_ranking.json",),
        optional_chart_candidates=("fig3a_gra_ranking.png", "fig_gra_ranking.png"),
        optional_summary_candidates=("results_summary.txt",),
    ),
)


def _read_asset_evidence(bundle_dir: Path) -> list[dict[str, Any]]:
    asset_evidence_path = bundle_dir / "asset_evidence.json"
    if not asset_evidence_path.exists():
        return []
    payload = read_json(asset_evidence_path)
    assets = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(assets, list):
        raise ValueError(f"asset_evidence.json must contain an 'assets' list: {asset_evidence_path}")
    return [asset for asset in assets if isinstance(asset, dict)]


def _bundle_name(bundle_dir: Path, bundle_manifest: dict[str, Any], summary: dict[str, Any]) -> str:
    return (
        str(bundle_manifest.get("report_id") or "").strip()
        or str(summary.get("model_name") or "").strip()
        or bundle_dir.name
    )


def _resolve_candidate(
    bundle_dir: Path,
    summary: dict[str, Any],
    candidate: str,
) -> str | None:
    direct = bundle_dir / candidate
    if direct.exists():
        return candidate

    summary_files = summary.get("files", {})
    if candidate in summary_files:
        resolved = str(summary_files[candidate]).strip()
        if resolved and (bundle_dir / resolved).exists():
            return resolved
    return None


def _resolve_existing_files(
    bundle_dir: Path,
    summary: dict[str, Any],
    candidates: tuple[str, ...],
) -> list[str]:
    resolved: list[str] = []
    for candidate in candidates:
        match = _resolve_candidate(bundle_dir, summary, candidate)
        if match and match not in resolved:
            resolved.append(match)
    return resolved


def _model_entities(table_rows: list[dict[str, str]]) -> list[str]:
    models = [str(row.get("model") or "").strip() for row in table_rows]
    return [model for model in models if model]


def _incremental_entities(table_rows: list[dict[str, str]]) -> list[str]:
    if not table_rows:
        return []
    entities: list[str] = []
    for key in table_rows[0].keys():
        if key.endswith("_R2") or key.endswith("_MSE"):
            model_name = key.rsplit("_", 1)[0]
            if model_name not in entities:
                entities.append(model_name)
    return entities


def _ranking_entities(ranking_payload: Any) -> list[str]:
    entities: list[str] = []
    if isinstance(ranking_payload, list):
        for item in ranking_payload:
            if isinstance(item, dict):
                feature = str(item.get("feature") or "").strip()
                if feature:
                    entities.append(feature)
    return entities


def _feature_entities(items: Any, key: str = "feature") -> list[str]:
    entities: list[str] = []
    if not isinstance(items, list):
        return entities
    for item in items:
        if not isinstance(item, dict):
            continue
        entity = str(item.get(key) or "").strip()
        if entity and entity not in entities:
            entities.append(entity)
    return entities


def _pair_entities(items: Any) -> list[str]:
    entities: list[str] = []
    if not isinstance(items, list):
        return entities
    for item in items:
        if not isinstance(item, dict):
            continue
        pair = str(item.get("pair") or "").strip()
        if pair and pair not in entities:
            entities.append(pair)
    return entities


def _asset_primary_entities(asset: dict[str, Any], family: str) -> list[str]:
    evidence = asset.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}

    if family == "feature_ranking":
        feature_story = evidence.get("feature_story")
        if isinstance(feature_story, dict):
            return _feature_entities(feature_story.get("top_gra_features"))
        return []

    if family == "feature_story_shap":
        feature_story = evidence.get("feature_story")
        if isinstance(feature_story, dict):
            return _feature_entities(feature_story.get("top_shap_features"))
        return []

    if family == "feature_story_importance":
        feature_story = evidence.get("feature_story")
        if isinstance(feature_story, dict):
            return _feature_entities(feature_story.get("top_feature_importance"))
        return []

    if family == "feature_analysis_combined":
        entities: list[str] = []
        feature_story = evidence.get("feature_story")
        if isinstance(feature_story, dict):
            for source_key in ("top_gra_features", "top_feature_importance", "top_shap_features"):
                for feature in _feature_entities(feature_story.get(source_key)):
                    if feature not in entities:
                        entities.append(feature)
        correlation_story = evidence.get("correlation_story")
        if isinstance(correlation_story, dict):
            for feature in _feature_entities(correlation_story.get("top_target_correlations")):
                if feature not in entities:
                    entities.append(feature)
        return entities

    if family == "correlation":
        entities: list[str] = []
        correlation_story = evidence.get("correlation_story")
        if isinstance(correlation_story, dict):
            for pair in _pair_entities(correlation_story.get("strongest_correlations")):
                if pair not in entities:
                    entities.append(pair)
            for feature in _feature_entities(correlation_story.get("top_target_correlations")):
                if feature not in entities:
                    entities.append(feature)
        return entities

    if family == "distribution":
        distribution_story = evidence.get("distribution_story")
        if isinstance(distribution_story, dict):
            return _feature_entities(distribution_story.get("descriptive_statistics_sample"), "Unnamed: 0")
        return []

    if family == "model_comparison_chart":
        model_metrics = evidence.get("model_metrics")
        if isinstance(model_metrics, dict):
            models = model_metrics.get("benchmark_models_sorted")
            if isinstance(models, list):
                return _feature_entities(models, "model")
        return []

    if family == "incremental_feature_analysis_chart":
        incremental_story = evidence.get("incremental_story")
        if isinstance(incremental_story, dict):
            return _feature_entities(incremental_story.get("best_step_per_model"), "model")
        return []

    if family in {
        "prediction_sequence",
        "prediction_overview",
        "prediction_residuals",
        "prediction_scatter",
    }:
        model_metrics = evidence.get("model_metrics")
        if isinstance(model_metrics, dict):
            for key in ("winning_model", "model_name"):
                model_name = str(model_metrics.get(key) or "").strip()
                if model_name:
                    return [model_name]
        return []

    return []


def _resolve_asset_source_files(bundle_dir: Path, asset: dict[str, Any]) -> tuple[list[str], str | None, list[str]]:
    source_files: list[str] = []
    raw_source_files = asset.get("source_files")
    if not isinstance(raw_source_files, list):
        raise ValueError(f"Asset '{asset.get('key')}' is missing a valid source_files list.")

    for source_file in raw_source_files:
        normalized = str(source_file or "").strip()
        if not normalized:
            continue
        if not (bundle_dir / normalized).exists():
            raise FileNotFoundError(
                f"Asset '{asset.get('key')}' declares a missing source file: {normalized}"
            )
        if normalized not in source_files:
            source_files.append(normalized)

    asset_file = str(asset.get("asset_file") or "").strip() or None
    if asset_file:
        if not (bundle_dir / asset_file).exists():
            raise FileNotFoundError(
                f"Asset '{asset.get('key')}' declares a missing chart file: {asset_file}"
            )
        if asset_file not in source_files:
            source_files.append(asset_file)

    summary_files = [name for name in source_files if name.lower().endswith(".txt")]
    return source_files, asset_file, summary_files


def _load_asset_payload(bundle_dir: Path, asset_key: str) -> dict[str, Any]:
    for asset in _read_asset_evidence(bundle_dir):
        if str(asset.get("key") or "").strip() == asset_key:
            return asset
    raise FileNotFoundError(f"Asset payload for '{asset_key}' was not found in asset_evidence.json.")


def build_manifest(bundle_dir: Path) -> list[ManifestRecord]:
    if not bundle_dir.is_dir():
        raise FileNotFoundError(f"Bundle directory does not exist: {bundle_dir}")

    summary = read_json(bundle_dir / "summary.json") if (bundle_dir / "summary.json").exists() else {}
    bundle_manifest = (
        read_json(bundle_dir / "bundle_manifest.json")
        if (bundle_dir / "bundle_manifest.json").exists()
        else {}
    )
    bundle_name = _bundle_name(bundle_dir, bundle_manifest, summary)

    records: list[ManifestRecord] = []
    for spec in ARTIFACT_SPECS:
        missing = [name for name in spec.required_files if not (bundle_dir / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing required files for '{spec.artifact_type}': {', '.join(missing)}"
            )

        chart_files = _resolve_existing_files(
            bundle_dir=bundle_dir,
            summary=summary,
            candidates=spec.optional_chart_candidates,
        )
        summary_files = _resolve_existing_files(
            bundle_dir=bundle_dir,
            summary=summary,
            candidates=spec.optional_summary_candidates,
        )
        source_files = list(spec.required_files) + chart_files + summary_files

        if spec.artifact_type == "model_comparison/main":
            primary_entities = _model_entities(read_csv_rows(bundle_dir / "table_model_comparison.csv"))
        elif spec.artifact_type == "incremental_feature_analysis/main":
            primary_entities = _incremental_entities(
                read_csv_rows(bundle_dir / "table1_incremental_results.csv")
            )
        else:
            primary_entities = _ranking_entities(read_json(bundle_dir / "gra_ranking.json"))

        records.append(
            ManifestRecord(
                artifact_id=f"{bundle_name}:{spec.artifact_type}",
                artifact_type=spec.artifact_type,
                chart_type=spec.chart_type,
                source_files=source_files,
                primary_entities=primary_entities,
                bundle_name=bundle_name,
                chart_file=chart_files[0] if chart_files else None,
                summary_files=summary_files,
            )
        )

    for asset in _read_asset_evidence(bundle_dir):
        if str(asset.get("kind") or "").strip().lower() != "chart":
            continue

        asset_key = str(asset.get("key") or "").strip()
        spec = get_chart_asset_spec(asset_key)
        if spec is None:
            raise ValueError(
                f"Unsupported chart asset '{asset_key}' found in asset_evidence.json. "
                "Add a chart asset spec before benchmarking this report."
            )

        source_files, chart_file, summary_files = _resolve_asset_source_files(bundle_dir, asset)
        records.append(
            ManifestRecord(
                artifact_id=f"{bundle_name}:chart:{asset_key}",
                artifact_type=spec.artifact_type,
                chart_type=spec.chart_type,
                source_files=source_files,
                primary_entities=_asset_primary_entities(asset, spec.family),
                bundle_name=bundle_name,
                chart_file=chart_file,
                summary_files=summary_files,
                asset_key=asset_key,
                asset_title=str(asset.get("title") or "").strip() or None,
                asset_family=spec.family,
            )
        )
    return records


def load_artifact_inputs(record: ManifestRecord, bundle_dir: Path) -> ArtifactInputs:
    tables: dict[str, list[dict[str, Any]]] = {}
    json_payloads: dict[str, Any] = {}
    text_payloads: dict[str, str] = {}
    chart_files: list[str] = []
    asset_payload: dict[str, Any] | None = None

    for source_file in record.source_files:
        source_path = bundle_dir / source_file
        if not source_path.exists():
            raise FileNotFoundError(
                f"Source file declared in manifest is missing: {source_path}"
            )

        suffix = source_path.suffix.lower()
        if suffix == ".csv":
            tables[source_file] = read_csv_rows(source_path)
        elif suffix == ".json":
            json_payloads[source_file] = read_json(source_path)
        elif suffix == ".txt":
            text_payloads[source_file] = read_text(source_path)
        elif suffix in IMAGE_SUFFIXES:
            chart_files.append(source_file)

    if record.asset_key:
        asset_payload = _load_asset_payload(bundle_dir, record.asset_key)

    return ArtifactInputs(
        record=record,
        bundle_dir=bundle_dir,
        tables=tables,
        json_payloads=json_payloads,
        text_payloads=text_payloads,
        chart_files=chart_files,
        asset_payload=asset_payload,
    )
