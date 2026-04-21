from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

from .manifest import load_artifact_inputs
from .schemas import EvidenceRef, GoldArtifact, GroundTruthFact, ManifestRecord

HIGHER_IS_BETTER = {"r2_score"}
ERROR_METRICS = {"mse", "rmse", "mae"}


def _as_float(value: Any) -> float:
    return float(str(value).strip())


def _sort_metric_rows(
    rows: list[dict[str, Any]],
    metric: str,
    higher_is_better: bool,
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: _as_float(row[metric]),
        reverse=higher_is_better,
    )


def _table_evidence(source_file: str, detail: str | None = None) -> list[EvidenceRef]:
    return [EvidenceRef(source_file=source_file, priority="table/json", detail=detail)]


def _evidence_priority(source_file: str) -> str:
    suffix = Path(source_file).suffix.lower()
    if suffix in {".json", ".csv"}:
        return "table/json"
    if suffix == ".txt":
        return "summary_text"
    return "chart"


def _evidence(source_file: str, detail: str | None = None) -> list[EvidenceRef]:
    return [EvidenceRef(source_file=source_file, priority=_evidence_priority(source_file), detail=detail)]


def _fact(
    record: ManifestRecord,
    fact_key: str,
    fact_type: str,
    subject: str,
    predicate: str,
    *,
    object: Any = None,
    value: Any = None,
    source_file: str,
    detail: str | None = None,
    importance: int = 1,
) -> GroundTruthFact:
    return GroundTruthFact(
        fact_id=f"{record.artifact_id}:{fact_key}",
        fact_type=fact_type,
        subject=subject,
        predicate=predicate,
        object=object,
        value=value,
        evidence=_evidence(source_file, detail),
        importance=importance,
    )


def _artifact(
    record: ManifestRecord,
    facts: list[GroundTruthFact],
    salient_facts: list[str],
    forbidden_inferences: list[str],
) -> GoldArtifact:
    return GoldArtifact(
        artifact_id=record.artifact_id,
        artifact_type=record.artifact_type,
        source_files=record.source_files,
        chart_type=record.chart_type,
        primary_entities=record.primary_entities,
        ground_truth_facts=facts,
        salient_facts=salient_facts,
        forbidden_inferences=forbidden_inferences,
    )


def _build_model_comparison_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    source_file = "table_model_comparison.csv"
    rows = inputs.tables[source_file]
    if not rows:
        raise ValueError("Model comparison table is empty.")

    metric_names = [
        key for key in rows[0].keys() if key != "model" and str(rows[0].get(key, "")).strip()
    ]
    ranked_rows = _sort_metric_rows(rows, metric="r2_score", higher_is_better=True)
    best_row = ranked_rows[0]
    best_model = str(best_row["model"])

    facts: list[GroundTruthFact] = [
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:best_model",
            fact_type="best_model",
            subject="model_comparison",
            predicate="best_model",
            object=best_model,
            value=_as_float(best_row["r2_score"]),
            evidence=_table_evidence(source_file, f"best model by r2_score = {best_model}"),
            importance=3,
        )
    ]

    for row in rows:
        model_name = str(row["model"])
        for metric in metric_names:
            facts.append(
                GroundTruthFact(
                    fact_id=f"{record.artifact_id}:metric:{model_name}:{metric}",
                    fact_type="metric_value",
                    subject=model_name,
                    predicate=metric,
                    value=_as_float(row[metric]),
                    evidence=_table_evidence(source_file, f"{model_name} {metric}"),
                    importance=2 if model_name == best_model else 1,
                )
            )

    for metric in metric_names:
        higher_is_better = metric in HIGHER_IS_BETTER
        ranking = [
            str(item["model"])
            for item in _sort_metric_rows(rows, metric=metric, higher_is_better=higher_is_better)
        ]
        facts.append(
            GroundTruthFact(
                fact_id=f"{record.artifact_id}:ranking:{metric}",
                fact_type="ranking",
                subject="model_comparison",
                predicate=metric,
                object=ranking,
                evidence=_table_evidence(source_file, f"{metric} ranking"),
                importance=2 if metric == "r2_score" else 1,
            )
        )

    for row in rows:
        other_model = str(row["model"])
        if other_model == best_model:
            continue
        for metric in metric_names:
            best_value = _as_float(best_row[metric])
            other_value = _as_float(row[metric])
            if metric in ERROR_METRICS:
                gap_value = other_value - best_value
            else:
                gap_value = best_value - other_value
            facts.append(
                GroundTruthFact(
                    fact_id=f"{record.artifact_id}:gap:{best_model}:{other_model}:{metric}",
                    fact_type="pairwise_metric_gap",
                    subject=best_model,
                    predicate=metric,
                    object=other_model,
                    value=gap_value,
                    evidence=_table_evidence(source_file, f"{best_model} vs {other_model} {metric} gap"),
                    importance=1,
                )
            )

    salient_facts = [
        f"{record.artifact_id}:best_model",
        f"{record.artifact_id}:metric:{best_model}:r2_score",
        f"{record.artifact_id}:metric:{best_model}:mse",
        f"{record.artifact_id}:ranking:r2_score",
    ]
    return GoldArtifact(
        artifact_id=record.artifact_id,
        artifact_type=record.artifact_type,
        source_files=record.source_files,
        chart_type=record.chart_type,
        primary_entities=record.primary_entities,
        ground_truth_facts=facts,
        salient_facts=salient_facts,
        forbidden_inferences=[
            "Do not claim that the winning model will generalize outside this bundle.",
            "Do not treat llm_explanations.json as ground truth.",
        ],
    )


def _extract_incremental_models(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    models: list[str] = []
    for key in rows[0].keys():
        if key.endswith("_R2"):
            models.append(key[:-3])
    return models


def _find_global_best(
    rows: list[dict[str, Any]],
    metric_suffix: str,
    higher_is_better: bool,
) -> tuple[str, dict[str, Any], float]:
    best_model = ""
    best_row: dict[str, Any] = {}
    best_value: float | None = None

    for row in rows:
        for model_name in _extract_incremental_models(rows):
            column_name = f"{model_name}_{metric_suffix}"
            if column_name not in row:
                continue
            value = _as_float(row[column_name])
            if best_value is None:
                best_model = model_name
                best_row = row
                best_value = value
                continue
            better = value > best_value if higher_is_better else value < best_value
            if better:
                best_model = model_name
                best_row = row
                best_value = value

    if best_value is None:
        raise ValueError(f"No values found for metric suffix '{metric_suffix}'.")
    return best_model, best_row, best_value


def _detect_plateau(rows: list[dict[str, Any]], model_name: str) -> tuple[int, str]:
    series: list[tuple[int, str, float]] = []
    for row in rows:
        n_features = int(float(row["n_features"]))
        feature_subset = str(row["feature_subset"])
        r2_value = _as_float(row[f"{model_name}_R2"])
        series.append((n_features, feature_subset, r2_value))

    best_value = max(value for _, _, value in series)
    plateau_margin = 0.01
    future_gain_tolerance = 0.005
    for index, (feature_count, feature_subset, current_value) in enumerate(series):
        future_values = [value for _, _, value in series[index:]]
        if best_value - current_value > plateau_margin:
            continue
        if max(future_values) - current_value <= future_gain_tolerance:
            return feature_count, feature_subset
    feature_count, feature_subset, _ = max(series, key=lambda item: item[2])
    return feature_count, feature_subset


def _build_incremental_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    source_file = "table1_incremental_results.csv"
    rows = inputs.tables[source_file]
    if not rows:
        raise ValueError("Incremental feature analysis table is empty.")

    best_r2_model, best_r2_row, best_r2_value = _find_global_best(
        rows=rows,
        metric_suffix="R2",
        higher_is_better=True,
    )
    best_mse_model, best_mse_row, best_mse_value = _find_global_best(
        rows=rows,
        metric_suffix="MSE",
        higher_is_better=False,
    )
    plateau_count, plateau_subset = _detect_plateau(rows, best_r2_model)

    feature_subset_optimum = str(best_r2_row["feature_subset"])
    optimum_feature_count = int(float(best_r2_row["n_features"]))

    facts = [
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:feature_subset_optimum",
            fact_type="feature_subset_optimum",
            subject=best_r2_model,
            predicate="feature_subset_optimum",
            object=feature_subset_optimum,
            value=optimum_feature_count,
            evidence=_table_evidence(source_file, f"{best_r2_model} optimum subset"),
            importance=3,
        ),
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:best_r2",
            fact_type="best_r2",
            subject=best_r2_model,
            predicate="best_r2",
            object=feature_subset_optimum,
            value=best_r2_value,
            evidence=_table_evidence(source_file, f"{best_r2_model} best R2"),
            importance=3,
        ),
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:best_mse",
            fact_type="best_mse",
            subject=best_mse_model,
            predicate="best_mse",
            object=str(best_mse_row["feature_subset"]),
            value=best_mse_value,
            evidence=_table_evidence(source_file, f"{best_mse_model} best MSE"),
            importance=3,
        ),
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:plateau",
            fact_type="plateau",
            subject=best_r2_model,
            predicate="plateau",
            object=plateau_subset,
            value=plateau_count,
            evidence=_table_evidence(source_file, f"{best_r2_model} plateau start"),
            importance=2,
        ),
    ]

    return GoldArtifact(
        artifact_id=record.artifact_id,
        artifact_type=record.artifact_type,
        source_files=record.source_files,
        chart_type=record.chart_type,
        primary_entities=record.primary_entities,
        ground_truth_facts=facts,
        salient_facts=[fact.fact_id for fact in facts],
        forbidden_inferences=[
            "Do not assume that more features always improve performance.",
            "Do not use summary text to override table values.",
        ],
    )


def _build_feature_ranking_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    source_file = "gra_ranking.json"
    ranking_payload = inputs.json_payloads[source_file]
    if not isinstance(ranking_payload, list) or not ranking_payload:
        raise ValueError("GRA ranking payload is empty.")

    ranking_rows = sorted(
        ranking_payload,
        key=lambda item: int(item.get("rank", 10_000)),
    )
    ordered_features = [str(item["feature"]) for item in ranking_rows]
    top_item = ranking_rows[0]

    facts: list[GroundTruthFact] = [
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:top_feature",
            fact_type="top_feature",
            subject="gra",
            predicate="gra_score",
            object=str(top_item["feature"]),
            value=_as_float(top_item["score"]),
            evidence=_table_evidence(source_file, "top GRA feature"),
            importance=3,
        ),
        GroundTruthFact(
            fact_id=f"{record.artifact_id}:ranking",
            fact_type="ranking",
            subject="gra",
            predicate="gra_score",
            object=ordered_features,
            evidence=_table_evidence(source_file, "GRA rank ordering"),
            importance=2,
        ),
    ]
    for item in ranking_rows:
        feature = str(item["feature"])
        rank_value = int(item["rank"])
        score_value = _as_float(item["score"])
        facts.append(
            GroundTruthFact(
                fact_id=f"{record.artifact_id}:rank_score:{feature}",
                fact_type="rank_score",
                subject=feature,
                predicate="gra_score",
                object=rank_value,
                value=score_value,
                evidence=_table_evidence(source_file, f"{feature} GRA score"),
                importance=2 if rank_value <= 3 else 1,
            )
        )

    return GoldArtifact(
        artifact_id=record.artifact_id,
        artifact_type=record.artifact_type,
        source_files=record.source_files,
        chart_type=record.chart_type,
        primary_entities=record.primary_entities,
        ground_truth_facts=facts,
        salient_facts=[
            f"{record.artifact_id}:top_feature",
            f"{record.artifact_id}:ranking",
        ],
        forbidden_inferences=[
            "Do not treat GRA rank as proof of causality.",
            "Do not let summary prose override ranking JSON.",
        ],
    )


def _metric_ranking_rows(
    rows: list[dict[str, Any]],
    metric_key: str,
    higher_is_better: bool = True,
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda item: _as_float(item[metric_key]),
        reverse=higher_is_better,
    )


def _build_chart_model_comparison_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    model_metrics = evidence.get("model_metrics") if isinstance(evidence, dict) else {}
    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).name in {"summary.json", "table_model_comparison.csv"}
        ),
        record.source_files[0],
    )

    rows = model_metrics.get("benchmark_models_sorted") if isinstance(model_metrics, dict) else None
    if not isinstance(rows, list) or not rows:
        if "table_model_comparison.csv" not in inputs.tables:
            raise ValueError(f"Chart artifact '{record.artifact_id}' is missing model comparison metrics.")
        rows = inputs.tables["table_model_comparison.csv"]

    ranked_rows = _metric_ranking_rows(rows, "r2_score", higher_is_better=True)
    best_row = ranked_rows[0]
    best_model = str(best_row["model"])
    facts: list[GroundTruthFact] = [
        _fact(
            record,
            "best_model",
            "best_model",
            "model_comparison",
            "best_model",
            object=best_model,
            value=_as_float(best_row["r2_score"]),
            source_file=source_file,
            detail=f"winning model = {best_model}",
            importance=3,
        ),
        _fact(
            record,
            "ranking:r2_score",
            "ranking",
            "model_comparison",
            "r2_score",
            object=[str(item["model"]) for item in ranked_rows],
            source_file=source_file,
            detail="model ranking by r2_score",
            importance=2,
        ),
    ]

    for row in rows:
        model_name = str(row["model"])
        for metric_name in ("r2_score", "rmse", "mse", "mae"):
            if metric_name not in row:
                continue
            facts.append(
                _fact(
                    record,
                    f"metric:{model_name}:{metric_name}",
                    "metric_value",
                    model_name,
                    metric_name,
                    value=_as_float(row[metric_name]),
                    source_file=source_file,
                    detail=f"{model_name} {metric_name}",
                    importance=2 if model_name == best_model else 1,
                )
            )

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:best_model",
            f"{record.artifact_id}:ranking:r2_score",
            f"{record.artifact_id}:metric:{best_model}:r2_score",
            f"{record.artifact_id}:metric:{best_model}:rmse",
        ],
        [
            "Do not claim deployment performance from benchmark chart scores alone.",
            "Do not let narrative text override the chart's metric sources.",
        ],
    )


def _build_chart_incremental_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    incremental_story = evidence.get("incremental_story") if isinstance(evidence, dict) else {}
    best_steps = (
        incremental_story.get("best_step_per_model")
        if isinstance(incremental_story, dict)
        else None
    )
    if not isinstance(best_steps, list) or not best_steps:
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing incremental evidence.")

    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).name == "table1_incremental_results.csv"
        ),
        record.source_files[0],
    )
    best_by_r2 = max(best_steps, key=lambda item: _as_float(item["best_r2"]))
    best_by_mse = min(best_steps, key=lambda item: _as_float(item["best_mse"]))
    ranked_models = [
        str(item["model"])
        for item in sorted(best_steps, key=lambda item: _as_float(item["best_r2"]), reverse=True)
    ]

    facts: list[GroundTruthFact] = [
        _fact(
            record,
            "feature_subset_optimum",
            "feature_subset_optimum",
            str(best_by_r2["model"]),
            "feature_subset_optimum",
            object=str(best_by_r2["best_feature_subset"]),
            value=int(best_by_r2["best_n_features"]),
            source_file=source_file,
            detail=f"{best_by_r2['model']} best feature count",
            importance=3,
        ),
        _fact(
            record,
            "best_r2",
            "best_r2",
            str(best_by_r2["model"]),
            "r2_score",
            object=str(best_by_r2["best_feature_subset"]),
            value=_as_float(best_by_r2["best_r2"]),
            source_file=source_file,
            detail=f"{best_by_r2['model']} best R2",
            importance=3,
        ),
        _fact(
            record,
            "best_mse",
            "best_mse",
            str(best_by_mse["model"]),
            "mse",
            object=str(best_by_mse["best_feature_subset"]),
            value=_as_float(best_by_mse["best_mse"]),
            source_file=source_file,
            detail=f"{best_by_mse['model']} best MSE",
            importance=3,
        ),
        _fact(
            record,
            "ranking:r2_score",
            "ranking",
            "incremental_feature_analysis",
            "r2_score",
            object=ranked_models,
            source_file=source_file,
            detail="best-step ranking by r2_score",
            importance=2,
        ),
    ]

    for item in best_steps:
        model_name = str(item["model"])
        facts.append(
            _fact(
                record,
                f"metric:{model_name}:r2_score",
                "metric_value",
                model_name,
                "r2_score",
                value=_as_float(item["best_r2"]),
                source_file=source_file,
                detail=f"{model_name} best-step R2",
                importance=2 if model_name == str(best_by_r2["model"]) else 1,
            )
        )
        facts.append(
            _fact(
                record,
                f"metric:{model_name}:mse",
                "metric_value",
                model_name,
                "mse",
                value=_as_float(item["best_mse"]),
                source_file=source_file,
                detail=f"{model_name} best-step MSE",
                importance=2 if model_name == str(best_by_mse["model"]) else 1,
            )
        )

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:feature_subset_optimum",
            f"{record.artifact_id}:best_r2",
            f"{record.artifact_id}:best_mse",
            f"{record.artifact_id}:ranking:r2_score",
        ],
        [
            "Do not claim that adding more features always helps every model.",
            "Do not let prose override the incremental evidence table.",
        ],
    )


def _build_feature_story_gold(
    record: ManifestRecord,
    bundle_dir: Path,
    source_key: str,
    value_key: str,
    metric_name: str,
    detail_label: str,
) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    feature_story = evidence.get("feature_story") if isinstance(evidence, dict) else {}
    rows = feature_story.get(source_key) if isinstance(feature_story, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing feature-story evidence.")

    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).suffix.lower() in {".csv", ".json"}
        ),
        record.source_files[0],
    )
    ordered_rows = sorted(rows, key=lambda item: _as_float(item[value_key]), reverse=True)
    ordered_features = [str(item["feature"]) for item in ordered_rows]
    top_item = ordered_rows[0]
    facts: list[GroundTruthFact] = [
        _fact(
            record,
            "top_feature",
            "top_feature",
            detail_label,
            metric_name,
            object=str(top_item["feature"]),
            value=_as_float(top_item[value_key]),
            source_file=source_file,
            detail=f"top {metric_name} feature",
            importance=3,
        ),
        _fact(
            record,
            "ranking",
            "ranking",
            detail_label,
            metric_name,
            object=ordered_features,
            source_file=source_file,
            detail=f"{metric_name} ranking",
            importance=2,
        ),
    ]
    for item in ordered_rows:
        feature_name = str(item["feature"])
        facts.append(
            _fact(
                record,
                f"metric:{feature_name}:{metric_name}",
                "metric_value",
                feature_name,
                metric_name,
                value=_as_float(item[value_key]),
                source_file=source_file,
                detail=f"{feature_name} {metric_name}",
                importance=2 if feature_name == str(top_item["feature"]) else 1,
            )
        )

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:top_feature",
            f"{record.artifact_id}:ranking",
            f"{record.artifact_id}:metric:{top_item['feature']}:{metric_name}",
        ],
        [
            "Do not interpret feature scores as causal proof.",
            "Do not let summary prose override feature ranking values.",
        ],
    )


def _build_correlation_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    correlation_story = evidence.get("correlation_story") if isinstance(evidence, dict) else {}
    strongest_pairs = correlation_story.get("strongest_correlations") if isinstance(correlation_story, dict) else None
    target_rows = correlation_story.get("top_target_correlations") if isinstance(correlation_story, dict) else None
    if not isinstance(strongest_pairs, list) or not strongest_pairs:
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing strongest correlation evidence.")
    if not isinstance(target_rows, list) or not target_rows:
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing target correlation evidence.")

    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).name == "table_correlation_matrix.csv"
        ),
        record.source_files[0],
    )
    top_target = max(target_rows, key=lambda item: _as_float(item["abs_correlation"]))
    ordered_target = [
        str(item["feature"])
        for item in sorted(target_rows, key=lambda item: _as_float(item["abs_correlation"]), reverse=True)
    ]
    ordered_pairs = [
        str(item["pair"])
        for item in sorted(strongest_pairs, key=lambda item: _as_float(item["abs_correlation"]), reverse=True)
    ]

    facts: list[GroundTruthFact] = [
        _fact(
            record,
            "top_feature:target_correlation",
            "top_feature",
            "hpr",
            "target_correlation",
            object=str(top_target["feature"]),
            value=_as_float(top_target["correlation"]),
            source_file=source_file,
            detail="top HPR correlation feature",
            importance=3,
        ),
        _fact(
            record,
            "ranking:target_correlation",
            "ranking",
            "hpr",
            "target_correlation",
            object=ordered_target,
            source_file=source_file,
            detail="ranking by HPR correlation",
            importance=2,
        ),
        _fact(
            record,
            "ranking:correlation",
            "ranking",
            "feature_pairs",
            "correlation",
            object=ordered_pairs,
            source_file=source_file,
            detail="ranking by pairwise correlation strength",
            importance=2,
        ),
    ]

    for item in target_rows:
        feature_name = str(item["feature"])
        facts.append(
            _fact(
                record,
                f"metric:{feature_name}:target_correlation",
                "metric_value",
                feature_name,
                "target_correlation",
                value=_as_float(item["correlation"]),
                source_file=source_file,
                detail=f"{feature_name} correlation with HPR",
                importance=2 if feature_name == str(top_target["feature"]) else 1,
            )
        )

    for item in strongest_pairs:
        pair_name = str(item["pair"])
        facts.append(
            _fact(
                record,
                f"metric:{pair_name}:correlation",
                "metric_value",
                pair_name,
                "correlation",
                value=_as_float(item["correlation"]),
                source_file=source_file,
                detail=f"{pair_name} pairwise correlation",
                importance=2 if pair_name == ordered_pairs[0] else 1,
            )
        )

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:top_feature:target_correlation",
            f"{record.artifact_id}:ranking:target_correlation",
            f"{record.artifact_id}:metric:{ordered_pairs[0]}:correlation",
        ],
        [
            "Do not interpret correlation as causation.",
            "Do not let summary prose override the correlation matrix.",
        ],
    )


def _build_distribution_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    distribution_story = evidence.get("distribution_story") if isinstance(evidence, dict) else {}
    rows = (
        distribution_story.get("descriptive_statistics_sample")
        if isinstance(distribution_story, dict)
        else None
    )
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing distribution evidence.")

    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).name == "table_descriptive_statistics.csv"
        ),
        record.source_files[0],
    )
    mean_rows = sorted(rows, key=lambda item: _as_float(item["mean"]), reverse=True)
    std_rows = sorted(rows, key=lambda item: _as_float(item["std"]), reverse=True)
    top_mean = mean_rows[0]
    top_std = std_rows[0]
    facts: list[GroundTruthFact] = [
        _fact(
            record,
            "top_feature:mean",
            "top_feature",
            "distribution",
            "mean",
            object=str(top_mean["Unnamed: 0"]),
            value=_as_float(top_mean["mean"]),
            source_file=source_file,
            detail="highest mean feature",
            importance=3,
        ),
        _fact(
            record,
            "ranking:mean",
            "ranking",
            "distribution",
            "mean",
            object=[str(item["Unnamed: 0"]) for item in mean_rows],
            source_file=source_file,
            detail="ranking by mean",
            importance=2,
        ),
        _fact(
            record,
            "top_feature:std",
            "top_feature",
            "distribution",
            "std",
            object=str(top_std["Unnamed: 0"]),
            value=_as_float(top_std["std"]),
            source_file=source_file,
            detail="highest standard deviation feature",
            importance=2,
        ),
        _fact(
            record,
            "ranking:std",
            "ranking",
            "distribution",
            "std",
            object=[str(item["Unnamed: 0"]) for item in std_rows],
            source_file=source_file,
            detail="ranking by std",
            importance=2,
        ),
    ]

    for item in rows:
        feature_name = str(item["Unnamed: 0"])
        facts.append(
            _fact(
                record,
                f"metric:{feature_name}:mean",
                "metric_value",
                feature_name,
                "mean",
                value=_as_float(item["mean"]),
                source_file=source_file,
                detail=f"{feature_name} mean",
                importance=2 if feature_name == str(top_mean["Unnamed: 0"]) else 1,
            )
        )
        facts.append(
            _fact(
                record,
                f"metric:{feature_name}:std",
                "metric_value",
                feature_name,
                "std",
                value=_as_float(item["std"]),
                source_file=source_file,
                detail=f"{feature_name} std",
                importance=2 if feature_name == str(top_std["Unnamed: 0"]) else 1,
            )
        )

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:top_feature:mean",
            f"{record.artifact_id}:top_feature:std",
            f"{record.artifact_id}:ranking:mean",
        ],
        [
            "Do not infer real-world units from scaled distribution summaries.",
            "Do not let prose override descriptive statistics values.",
        ],
    )


def _build_prediction_metrics_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    model_metrics = evidence.get("model_metrics") if isinstance(evidence, dict) else {}
    prediction_story = evidence.get("prediction_story") if isinstance(evidence, dict) else {}

    model_name = ""
    metrics_row: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    if record.asset_family == "prediction_scatter":
        model_name = str(model_metrics.get("model_name") or "").strip()
        metrics_row = model_metrics.get("metrics") if isinstance(model_metrics, dict) else {}
        diagnostics = prediction_story.get("diagnostics") if isinstance(prediction_story, dict) else {}
    else:
        model_name = str(model_metrics.get("winning_model") or "").strip()
        metrics_row = model_metrics.get("best_model_metrics") if isinstance(model_metrics, dict) else {}
        diagnostics = (
            prediction_story.get("winning_model_diagnostics")
            if isinstance(prediction_story, dict)
            else {}
        )

    if not model_name or not isinstance(metrics_row, dict) or not isinstance(diagnostics, dict):
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing prediction diagnostics.")

    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).suffix.lower() == ".json"
        ),
        record.source_files[0],
    )
    facts: list[GroundTruthFact] = []
    metric_keys = ["r2_score", "rmse", "mse", "mae"]
    diagnostic_keys = [
        "pred_actual_correlation",
        "linear_fit_slope",
        "linear_fit_intercept",
        "residual_mean",
        "residual_std",
        "mean_abs_residual",
        "max_abs_residual",
        "p95_abs_residual",
        "actual_min",
        "actual_max",
        "predicted_min",
        "predicted_max",
    ]
    for metric_name in metric_keys:
        if metric_name in metrics_row:
            facts.append(
                _fact(
                    record,
                    f"metric:{model_name}:{metric_name}",
                    "metric_value",
                    model_name,
                    metric_name,
                    value=_as_float(metrics_row[metric_name]),
                    source_file=source_file,
                    detail=f"{model_name} {metric_name}",
                    importance=2 if metric_name == "r2_score" else 1,
                )
            )
    for metric_name in diagnostic_keys:
        if metric_name in diagnostics:
            facts.append(
                _fact(
                    record,
                    f"metric:{model_name}:{metric_name}",
                    "metric_value",
                    model_name,
                    metric_name,
                    value=_as_float(diagnostics[metric_name]),
                    source_file=source_file,
                    detail=f"{model_name} {metric_name}",
                    importance=2 if metric_name in {"pred_actual_correlation", "max_abs_residual"} else 1,
                )
            )

    salient_metrics = {
        "prediction_overview": ("r2_score", "pred_actual_correlation", "max_abs_residual", "predicted_max"),
        "prediction_residuals": ("residual_mean", "residual_std", "p95_abs_residual", "max_abs_residual"),
        "prediction_scatter": ("r2_score", "pred_actual_correlation", "linear_fit_slope", "max_abs_residual"),
    }.get(record.asset_family or "", ("r2_score", "pred_actual_correlation", "max_abs_residual"))

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:metric:{model_name}:{metric_name}"
            for metric_name in salient_metrics
            if any(fact.fact_id.endswith(f":{model_name}:{metric_name}") for fact in facts)
        ],
        [
            "Do not read diagnostic plots as guarantees for every individual prediction.",
            "Do not let narrative prose override the diagnostic metrics.",
        ],
    )


def _build_prediction_sequence_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    model_metrics = evidence.get("model_metrics") if isinstance(evidence, dict) else {}
    sequence_story = evidence.get("sequence_story") if isinstance(evidence, dict) else {}
    model_name = str(model_metrics.get("winning_model") or "").strip()
    diagnostics = (
        sequence_story.get("winning_model_sequence_diagnostics")
        if isinstance(sequence_story, dict)
        else {}
    )
    if not model_name or not isinstance(diagnostics, dict) or not diagnostics:
        raise ValueError(f"Chart artifact '{record.artifact_id}' is missing sequence diagnostics.")

    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).suffix.lower() == ".json"
        ),
        record.source_files[0],
    )
    facts: list[GroundTruthFact] = []
    for metric_name in (
        "actual_peak_index",
        "actual_peak_value",
        "predicted_peak_index",
        "predicted_peak_value",
        "mean_abs_gap",
        "max_abs_gap",
        "sequence_correlation",
    ):
        if metric_name in diagnostics:
            facts.append(
                _fact(
                    record,
                    f"metric:{model_name}:{metric_name}",
                    "metric_value",
                    model_name,
                    metric_name,
                    value=_as_float(diagnostics[metric_name]),
                    source_file=source_file,
                    detail=f"{model_name} {metric_name}",
                    importance=2 if metric_name in {"mean_abs_gap", "sequence_correlation"} else 1,
                )
            )

    return _artifact(
        record,
        facts,
        [
            f"{record.artifact_id}:metric:{model_name}:sequence_correlation",
            f"{record.artifact_id}:metric:{model_name}:mean_abs_gap",
            f"{record.artifact_id}:metric:{model_name}:actual_peak_index",
            f"{record.artifact_id}:metric:{model_name}:predicted_peak_index",
        ],
        [
            "Do not claim perfect event timing from aggregate sequence diagnostics.",
            "Do not let prose override sequence diagnostic values.",
        ],
    )


def _build_combined_feature_analysis_gold(record: ManifestRecord, bundle_dir: Path) -> GoldArtifact:
    inputs = load_artifact_inputs(record, bundle_dir)
    asset_payload = inputs.asset_payload or {}
    evidence = asset_payload.get("evidence") if isinstance(asset_payload, dict) else {}
    feature_story = evidence.get("feature_story") if isinstance(evidence, dict) else {}
    correlation_story = evidence.get("correlation_story") if isinstance(evidence, dict) else {}
    incremental_story = evidence.get("incremental_story") if isinstance(evidence, dict) else {}
    source_file = next(
        (
            file_name
            for file_name in record.source_files
            if Path(file_name).suffix.lower() in {".csv", ".json"}
        ),
        record.source_files[0],
    )

    facts: list[GroundTruthFact] = []
    salient_facts: list[str] = []

    def add_top_feature(rows: Any, value_key: str, metric_name: str, label: str) -> None:
        if not isinstance(rows, list) or not rows:
            return
        ordered = sorted(rows, key=lambda item: _as_float(item[value_key]), reverse=True)
        top_item = ordered[0]
        facts.append(
            _fact(
                record,
                f"top_feature:{metric_name}",
                "top_feature",
                label,
                metric_name,
                object=str(top_item["feature"]),
                value=_as_float(top_item[value_key]),
                source_file=source_file,
                detail=f"top {metric_name} feature",
                importance=3,
            )
        )
        facts.append(
            _fact(
                record,
                f"ranking:{metric_name}",
                "ranking",
                label,
                metric_name,
                object=[str(item["feature"]) for item in ordered],
                source_file=source_file,
                detail=f"{metric_name} ranking",
                importance=2,
            )
        )
        salient_facts.extend(
            [
                f"{record.artifact_id}:top_feature:{metric_name}",
                f"{record.artifact_id}:ranking:{metric_name}",
            ]
        )

    if isinstance(feature_story, dict):
        add_top_feature(feature_story.get("top_gra_features"), "score", "gra_score", "combined_feature_story")
        add_top_feature(feature_story.get("top_feature_importance"), "importance", "importance", "combined_feature_story")
        add_top_feature(feature_story.get("top_shap_features"), "mean_abs_shap", "mean_abs_shap", "combined_feature_story")

    if isinstance(correlation_story, dict):
        target_rows = correlation_story.get("top_target_correlations")
        if isinstance(target_rows, list) and target_rows:
            ordered = sorted(target_rows, key=lambda item: _as_float(item["abs_correlation"]), reverse=True)
            top_item = ordered[0]
            facts.append(
                _fact(
                    record,
                    "top_feature:target_correlation",
                    "top_feature",
                    "combined_feature_story",
                    "target_correlation",
                    object=str(top_item["feature"]),
                    value=_as_float(top_item["correlation"]),
                    source_file=source_file,
                    detail="top target correlation feature",
                    importance=3,
                )
            )
            salient_facts.append(f"{record.artifact_id}:top_feature:target_correlation")

        strongest_pairs = correlation_story.get("strongest_correlations")
        if isinstance(strongest_pairs, list) and strongest_pairs:
            top_pair = max(strongest_pairs, key=lambda item: _as_float(item["abs_correlation"]))
            facts.append(
                _fact(
                    record,
                    f"metric:{top_pair['pair']}:correlation",
                    "metric_value",
                    str(top_pair["pair"]),
                    "correlation",
                    value=_as_float(top_pair["correlation"]),
                    source_file=source_file,
                    detail="strongest pair correlation",
                    importance=2,
                )
            )
            salient_facts.append(f"{record.artifact_id}:metric:{top_pair['pair']}:correlation")

    if isinstance(incremental_story, dict):
        best_steps = incremental_story.get("best_step_per_model")
        if isinstance(best_steps, list) and best_steps:
            best_by_r2 = max(best_steps, key=lambda item: _as_float(item["best_r2"]))
            facts.append(
                _fact(
                    record,
                    "feature_subset_optimum",
                    "feature_subset_optimum",
                    str(best_by_r2["model"]),
                    "feature_subset_optimum",
                    object=str(best_by_r2["best_feature_subset"]),
                    value=int(best_by_r2["best_n_features"]),
                    source_file=source_file,
                    detail="best overall incremental feature count",
                    importance=2,
                )
            )
            facts.append(
                _fact(
                    record,
                    "best_r2",
                    "best_r2",
                    str(best_by_r2["model"]),
                    "r2_score",
                    object=str(best_by_r2["best_feature_subset"]),
                    value=_as_float(best_by_r2["best_r2"]),
                    source_file=source_file,
                    detail="best overall incremental R2",
                    importance=2,
                )
            )
            salient_facts.extend(
                [
                    f"{record.artifact_id}:feature_subset_optimum",
                    f"{record.artifact_id}:best_r2",
                ]
            )

    if not facts:
        raise ValueError(f"Chart artifact '{record.artifact_id}' has no combined feature-analysis evidence.")

    return _artifact(
        record,
        facts,
        list(dict.fromkeys(salient_facts)),
        [
            "Do not collapse different feature-analysis lenses into a single causal claim.",
            "Do not let prose override the structured evidence for each lens.",
        ],
    )


def build_gold_artifacts(bundle_dir: Path, records: list[ManifestRecord]) -> list[GoldArtifact]:
    gold_artifacts: list[GoldArtifact] = []
    for record in records:
        if record.artifact_type == "model_comparison/main":
            gold_artifacts.append(_build_model_comparison_gold(record, bundle_dir))
        elif record.artifact_type == "incremental_feature_analysis/main":
            gold_artifacts.append(_build_incremental_gold(record, bundle_dir))
        elif record.artifact_type == "feature_ranking/gra":
            gold_artifacts.append(_build_feature_ranking_gold(record, bundle_dir))
        elif record.asset_family == "model_comparison_chart":
            gold_artifacts.append(_build_chart_model_comparison_gold(record, bundle_dir))
        elif record.asset_family == "incremental_feature_analysis_chart":
            gold_artifacts.append(_build_chart_incremental_gold(record, bundle_dir))
        elif record.asset_family == "feature_ranking":
            gold_artifacts.append(_build_feature_ranking_gold(record, bundle_dir))
        elif record.asset_family == "feature_story_shap":
            gold_artifacts.append(
                _build_feature_story_gold(
                    record,
                    bundle_dir,
                    source_key="top_shap_features",
                    value_key="mean_abs_shap",
                    metric_name="mean_abs_shap",
                    detail_label="shap",
                )
            )
        elif record.asset_family == "feature_story_importance":
            gold_artifacts.append(
                _build_feature_story_gold(
                    record,
                    bundle_dir,
                    source_key="top_feature_importance",
                    value_key="importance",
                    metric_name="importance",
                    detail_label="feature_importance",
                )
            )
        elif record.asset_family == "feature_analysis_combined":
            gold_artifacts.append(_build_combined_feature_analysis_gold(record, bundle_dir))
        elif record.asset_family == "correlation":
            gold_artifacts.append(_build_correlation_gold(record, bundle_dir))
        elif record.asset_family == "distribution":
            gold_artifacts.append(_build_distribution_gold(record, bundle_dir))
        elif record.asset_family in {"prediction_overview", "prediction_residuals", "prediction_scatter"}:
            gold_artifacts.append(_build_prediction_metrics_gold(record, bundle_dir))
        elif record.asset_family == "prediction_sequence":
            gold_artifacts.append(_build_prediction_sequence_gold(record, bundle_dir))
        else:
            raise ValueError(f"Unsupported artifact type: {record.artifact_type}")
    return gold_artifacts
