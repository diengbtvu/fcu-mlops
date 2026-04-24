from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_csv_rows, write_json
from .schemas import ArtifactScore, to_primitive

PER_CHART_JSON_FILENAME = "per_chart_benchmark.json"
PER_CHART_CSV_FILENAME = "per_chart_benchmark.csv"
STATUS_ORDER = ("supported", "partially_supported", "contradicted", "unverifiable")


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


def _metric_value(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_sort_key(row: dict[str, Any]) -> tuple[float, float, float, str, str, str]:
    return (
        -(_metric_value(row, "fact_f1") or 0.0),
        _metric_value(row, "unsupported_claim_rate") or 0.0,
        _metric_value(row, "contradiction_rate") or 0.0,
        str(row.get("arm") or ""),
        str(row.get("input_condition") or ""),
        str(row.get("semantic_level") or ""),
    )


def _artifact_scope(record: dict[str, Any]) -> str:
    return "chart" if str(record.get("asset_key") or "").strip() else "core_bundle"


def _artifact_metadata(record: dict[str, Any] | None, artifact_id: str) -> dict[str, Any]:
    record = record or {}
    return {
        "artifact_id": artifact_id,
        "artifact_type": str(record.get("artifact_type") or ""),
        "artifact_scope": _artifact_scope(record),
        "asset_key": str(record.get("asset_key") or "") or None,
        "asset_title": str(record.get("asset_title") or "") or None,
        "asset_family": str(record.get("asset_family") or "") or None,
        "chart_type": str(record.get("chart_type") or "") or None,
        "chart_file": str(record.get("chart_file") or "") or None,
        "bundle_name": str(record.get("bundle_name") or "") or None,
        "primary_entities": list(record.get("primary_entities") or []),
        "source_files": list(record.get("source_files") or []),
        "summary_files": list(record.get("summary_files") or []),
    }


def _coerce_score_rows(artifact_scores: list[ArtifactScore | dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in artifact_scores:
        if isinstance(entry, ArtifactScore):
            rows.append(entry.to_dict())
            continue
        if isinstance(entry, dict):
            rows.append(dict(to_primitive(entry)))
    return rows


def _verification_breakdowns(benchmark_dir: Path) -> dict[tuple[str, str, str, str | None], dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str | None], dict[str, Any]] = defaultdict(
        lambda: {
            "status_counts": Counter(),
            "reason_counts": Counter(),
            "numeric_deltas": [],
        }
    )
    verifications_dir = benchmark_dir / "verifications"
    if not verifications_dir.exists():
        return grouped

    for payload_path in sorted(verifications_dir.glob("*.json")):
        payload = read_json(payload_path)
        verifications = payload.get("verifications")
        if not isinstance(verifications, list):
            continue

        for item in verifications:
            if not isinstance(item, dict):
                continue
            artifact_id = str(item.get("artifact_id") or payload.get("artifact_id") or "").strip()
            arm = str(item.get("arm") or payload.get("arm") or "").strip()
            input_condition = str(item.get("input_condition") or payload.get("input_condition") or "").strip()
            semantic_level = (
                str(item.get("semantic_level") or payload.get("semantic_level") or "").strip() or None
            )
            if not artifact_id or not arm or not input_condition:
                continue

            status = str(item.get("status") or "").strip()
            reason = str(item.get("reason") or "").strip()
            delta = item.get("numeric_delta")
            bucket = grouped[(artifact_id, arm, input_condition, semantic_level)]
            if status:
                bucket["status_counts"][status] += 1
            if reason:
                bucket["reason_counts"][reason] += 1
            if isinstance(delta, (int, float)):
                bucket["numeric_deltas"].append(float(delta))
    return grouped


def _reason_summary(reason_counts: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"reason": reason, "count": count}
        for reason, count in reason_counts.most_common(limit)
    ]


def _artifact_row(
    metadata: dict[str, Any],
    score_row: dict[str, Any],
    breakdown: dict[str, Any],
    rank: int,
) -> dict[str, Any]:
    status_counts = breakdown.get("status_counts") or Counter()
    reason_counts = breakdown.get("reason_counts") or Counter()
    numeric_deltas = list(breakdown.get("numeric_deltas") or [])
    top_reasons = _reason_summary(reason_counts, limit=3)

    row = {
        **metadata,
        "row_rank": rank,
        "arm": str(score_row.get("arm") or ""),
        "input_condition": str(score_row.get("input_condition") or ""),
        "semantic_level": str(score_row.get("semantic_level") or "") or None,
        "claim_count": int(score_row.get("claim_count") or 0),
        "fact_precision": _metric_value(score_row, "fact_precision"),
        "fact_recall": _metric_value(score_row, "fact_recall"),
        "fact_f1": _metric_value(score_row, "fact_f1"),
        "unsupported_claim_rate": _metric_value(score_row, "unsupported_claim_rate"),
        "contradiction_rate": _metric_value(score_row, "contradiction_rate"),
        "coverage_of_salient_facts": _metric_value(score_row, "coverage_of_salient_facts"),
        "numeric_accuracy": _metric_value(score_row, "numeric_accuracy"),
        "numeric_tolerance_accuracy": _metric_value(score_row, "numeric_tolerance_accuracy"),
        "supported_claim_count": int(status_counts.get("supported", 0)),
        "partially_supported_claim_count": int(status_counts.get("partially_supported", 0)),
        "contradicted_claim_count": int(status_counts.get("contradicted", 0)),
        "unverifiable_claim_count": int(status_counts.get("unverifiable", 0)),
        "top_reasons": top_reasons,
        "top_reason": top_reasons[0]["reason"] if top_reasons else None,
        "top_reason_count": top_reasons[0]["count"] if top_reasons else 0,
        "mean_numeric_delta": (
            sum(numeric_deltas) / len(numeric_deltas) if numeric_deltas else None
        ),
    }
    return row


def build_per_chart_benchmark_payload(
    manifest_rows: list[dict[str, Any]],
    artifact_scores: list[ArtifactScore | dict[str, Any]],
    verification_index: dict[tuple[str, str, str, str | None], dict[str, Any]],
    *,
    generated_at: str | None = None,
    expected_arms: list[str] | None = None,
    expected_conditions: list[str] | None = None,
    expected_levels: list[str] | None = None,
) -> dict[str, Any]:
    manifest_by_artifact = {
        str(row.get("artifact_id") or "").strip(): row
        for row in manifest_rows
        if str(row.get("artifact_id") or "").strip()
    }
    score_rows = _coerce_score_rows(artifact_scores)
    grouped_scores: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for score_row in score_rows:
        artifact_id = str(score_row.get("artifact_id") or "").strip()
        if artifact_id:
            grouped_scores[artifact_id].append(score_row)

    artifact_ids = sorted(set(manifest_by_artifact) | set(grouped_scores))
    flat_rows: list[dict[str, Any]] = []
    artifact_entries: list[dict[str, Any]] = []
    expected_pairs: list[tuple[str, str, str | None]] = []
    if expected_arms and expected_conditions:
        for arm in expected_arms:
            for condition in expected_conditions:
                if arm == "B" and expected_levels:
                    for semantic_level in expected_levels:
                        expected_pairs.append((arm, condition, semantic_level))
                else:
                    expected_pairs.append((arm, condition, None))

    for artifact_id in artifact_ids:
        metadata = _artifact_metadata(manifest_by_artifact.get(artifact_id), artifact_id)
        sorted_rows = sorted(grouped_scores.get(artifact_id, []), key=_row_sort_key)
        row_payloads: list[dict[str, Any]] = []
        aggregate_reasons: Counter[str] = Counter()

        for rank, score_row in enumerate(sorted_rows, start=1):
            breakdown = verification_index.get(
                (
                    artifact_id,
                    str(score_row.get("arm") or ""),
                    str(score_row.get("input_condition") or ""),
                    str(score_row.get("semantic_level") or "") or None,
                ),
                {},
            )
            aggregate_reasons.update(breakdown.get("reason_counts") or {})
            row_payload = _artifact_row(metadata, score_row, breakdown, rank)
            row_payloads.append(row_payload)
            flat_rows.append(row_payload)

        best_row = row_payloads[0] if row_payloads else None
        seen_pairs = {
            (
                str(row.get("arm") or ""),
                str(row.get("input_condition") or ""),
                str(row.get("semantic_level") or "") or None,
            )
            for row in row_payloads
        }
        missing_rows = [
            {"arm": arm, "input_condition": condition, "semantic_level": semantic_level}
            for arm, condition, semantic_level in expected_pairs
            if (arm, condition, semantic_level) not in seen_pairs
        ]
        artifact_entries.append(
            {
                **metadata,
                "compared_row_count": len(row_payloads),
                "expected_row_count": len(expected_pairs) if expected_pairs else None,
                "missing_rows": missing_rows,
                "best_row": best_row,
                "aggregate_reasons": _reason_summary(aggregate_reasons),
                "rows": row_payloads,
            }
        )

    best_rows = [entry["best_row"] for entry in artifact_entries if entry.get("best_row")]
    best_rows.sort(key=_row_sort_key)
    hardest_rows = sorted(
        best_rows,
        key=lambda row: (
            _metric_value(row, "fact_f1") or 0.0,
            -(_metric_value(row, "unsupported_claim_rate") or 0.0),
            -(_metric_value(row, "contradiction_rate") or 0.0),
            str(row.get("artifact_id") or ""),
        ),
    )
    csv_rows: list[dict[str, Any]] = []
    for row in flat_rows:
        csv_rows.append(
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key not in {"primary_entities", "source_files", "summary_files", "top_reasons"}
                },
                "primary_entities": " | ".join(row.get("primary_entities") or []),
                "source_files": " | ".join(row.get("source_files") or []),
                "summary_files": " | ".join(row.get("summary_files") or []),
            }
        )

    return {
        "generated_at": generated_at,
        "artifact_count": len(artifact_entries),
        "chart_count": sum(1 for entry in artifact_entries if entry.get("artifact_scope") == "chart"),
        "core_artifact_count": sum(
            1 for entry in artifact_entries if entry.get("artifact_scope") == "core_bundle"
        ),
        "row_count": len(flat_rows),
        "coverage_gaps": [
            {
                "artifact_id": entry["artifact_id"],
                "asset_key": entry.get("asset_key"),
                "artifact_scope": entry.get("artifact_scope"),
                "missing_rows": entry["missing_rows"],
            }
            for entry in artifact_entries
            if entry.get("missing_rows")
        ],
        "best_rows": best_rows[:10],
        "hardest_rows": hardest_rows[:10],
        "rows": flat_rows,
        "csv_rows": csv_rows,
        "artifacts": artifact_entries,
    }


def write_per_chart_benchmark_outputs(
    benchmark_dir: Path,
    *,
    artifact_scores: list[ArtifactScore | dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    benchmark_dir = Path(benchmark_dir)
    manifest_rows = _read_jsonl(benchmark_dir / "manifest.jsonl")
    run_metadata: dict[str, Any] = {}

    if artifact_scores is None:
        leaderboard_payload = read_json(benchmark_dir / "scores" / "leaderboard.json")
        raw_artifact_scores = leaderboard_payload.get("artifact_scores")
        artifact_scores = raw_artifact_scores if isinstance(raw_artifact_scores, list) else []

    run_metadata_path = benchmark_dir / "run_metadata.json"
    if run_metadata_path.exists():
        run_metadata = read_json(run_metadata_path)
        if generated_at is None:
            generated_at = str(run_metadata.get("created_at") or "").strip() or None

    payload = build_per_chart_benchmark_payload(
        manifest_rows=manifest_rows,
        artifact_scores=artifact_scores,
        verification_index=_verification_breakdowns(benchmark_dir),
        generated_at=generated_at,
        expected_arms=list(run_metadata.get("arms") or []),
        expected_conditions=list(run_metadata.get("conditions") or []),
        expected_levels=list(run_metadata.get("levels") or []),
    )
    csv_rows = list(payload.pop("csv_rows"))
    write_json(benchmark_dir / "scores" / PER_CHART_JSON_FILENAME, payload)
    write_csv_rows(benchmark_dir / "scores" / PER_CHART_CSV_FILENAME, csv_rows)
    payload["csv_rows"] = csv_rows
    return payload
