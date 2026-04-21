from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .claim_extractor import normalize_generation
from .io_utils import read_json
from .schemas import BASELINE_ARM, ExplanationOutput, ManifestRecord

ASSET_KEY_PREFERENCES: dict[str, tuple[str, ...]] = {
    "model_comparison/main": (
        "model_comparison_table",
        "metrics_overview",
        "fig5_model_comparison",
        "model_comparison_bars",
    ),
    "incremental_feature_analysis/main": (
        "table1_incremental_results",
        "fig6ab_mse_r2_features",
    ),
    "feature_ranking/gra": (
        "fig3a_gra_ranking",
        "best_model_shap_importance",
    ),
}

BEST_MODEL_PATTERNS = (
    re.compile(r"\bWinning model:\s*(?P<model>[A-Za-z0-9_+-]+)\b", re.IGNORECASE),
    re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s+is the winner\b", re.IGNORECASE),
    re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s+is the winning model\b", re.IGNORECASE),
    re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s+is the best overall performer\b", re.IGNORECASE),
    re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s+provides the best overall accuracy\b", re.IGNORECASE),
    re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s+was the best overall performer\b", re.IGNORECASE),
)
R2_INLINE_PATTERN = re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s*\(R[²2]\s*=\s*(?P<value>[0-9.]+)\)", re.IGNORECASE)
WEAKEST_MODEL_PATTERN = re.compile(r"\b(?P<model>[A-Za-z0-9_+-]+)\s+is (?:the )?(?:weakest|lowest)\b", re.IGNORECASE)
BEST_STEP_PATTERN = re.compile(
    r"\b(?P<model>[A-Za-z0-9_+-]+)\s+(?:at|peaks at|reaches its best at|does best at|performs best at)\s*"
    r"(?:n\s*=\s*)?(?P<count>\d+)\s*(?:features?)?\s*"
    r"(?:with\s*)?\(?R[²2]\s*=\s*(?P<r2>[0-9.]+)(?:,\s*|\s*\()\s*MSE\s*=\s*(?P<mse>[0-9.]+)\)?",
    re.IGNORECASE,
)
RANK_ITEM_PATTERNS = (
    re.compile(
        r"\b(?P<feature>[A-Za-z0-9_+\-]+)\s*\(rank\s*(?P<rank>\d+),\s*(?P<score>[0-9.]+)\)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<feature>[A-Za-z0-9_+\-]+)\s*(?:ranks?\s*)?#(?P<rank>\d+)\s*\((?P<score>[0-9.]+)\)",
        re.IGNORECASE,
    ),
)
MODEL_NAME_PATTERN = re.compile(
    r"\b(?P<model>[A-Za-z0-9_+-]+)\s+(?:scatter|prediction|sequence|model(?:’|')?s?)",
    re.IGNORECASE,
)
KNOWN_MODEL_PATTERN = re.compile(r"\b(?P<model>KNN|RF|SVM|DT|XGBoost)\b", re.IGNORECASE)
GENERIC_VALUE_PATTERN = re.compile(r"(?P<label>[A-Za-z0-9_+\-(), ]+?)\s*=\s*(?P<value>[0-9.]+)")
PREDICTION_METRIC_PATTERN = re.compile(
    r"(?P<label>"
    r"R2|R²|RMSE|MSE|MAE|corr\(pred,actual\)|corr\(pred, actual\)|"
    r"predicted-vs-actual correlation|slope|residual_mean|residual_std|"
    r"max_abs_residual|max absolute residual|p95_abs_residual|"
    r"actual_peak_index|actual peak occurs at index|actual_peak_value|"
    r"predicted_peak_index|predicted peak occurs later at index|predicted_peak_value|"
    r"mean_abs_gap|mean absolute gap|max_abs_gap|max absolute gap|"
    r"sequence_correlation|sequence correlation|predicted_min|predicted_max|"
    r"actual_min|actual_max"
    r")\s*(?:=|is|at)?\s*(?P<value>[0-9.]+)",
    re.IGNORECASE,
)


def _first_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    match = re.search(r"(?<=[.!?])\s+", stripped)
    if not match:
        return stripped
    return stripped[: match.start()].strip()


def _baseline_condition(record: ManifestRecord) -> str:
    if record.chart_file and record.summary_files:
        return "image_table_summary"
    if record.chart_file:
        return "image_table"
    return "table_only"


def _extract_assets(payload: dict[str, Any]) -> dict[str, Any]:
    assets = payload.get("assets")
    if isinstance(assets, dict):
        return assets
    return {}


def _extract_asset_entry(asset_payload: Any) -> dict[str, Any]:
    if isinstance(asset_payload, dict):
        return asset_payload
    return {}


def _find_asset_entry(payload: dict[str, Any], record: ManifestRecord) -> tuple[str | None, dict[str, Any]]:
    assets = _extract_assets(payload)
    if record.asset_key:
        entry = _extract_asset_entry(assets.get(record.asset_key))
        if entry:
            return record.asset_key, entry

    for asset_key in ASSET_KEY_PREFERENCES.get(record.artifact_type, ()):
        entry = _extract_asset_entry(assets.get(asset_key))
        if entry:
            return asset_key, entry
    return None, {}


def _structured_generation_payload(
    *,
    record: ManifestRecord,
    asset_key: str,
    asset_entry: dict[str, Any],
) -> dict[str, Any]:
    benchmark_payload = asset_entry.get("benchmark_payload")
    if not isinstance(benchmark_payload, dict):
        raise ValueError(
            f"{record.artifact_id}: asset '{asset_key}' is missing benchmark_payload in llm_explanations.json."
        )

    explanation_short = str(benchmark_payload.get("explanation_short") or "").strip()
    explanation_full = str(benchmark_payload.get("explanation_full") or "").strip()
    claims = benchmark_payload.get("claims")

    if not explanation_short:
        raise ValueError(
            f"{record.artifact_id}: asset '{asset_key}' has an empty benchmark explanation_short."
        )
    if not explanation_full:
        raise ValueError(
            f"{record.artifact_id}: asset '{asset_key}' has an empty benchmark explanation_full."
        )
    if not isinstance(claims, list):
        raise ValueError(
            f"{record.artifact_id}: asset '{asset_key}' has a non-list benchmark claims payload."
        )

    return {
        "artifact_id": record.artifact_id,
        "arm": BASELINE_ARM,
        "input_condition": _baseline_condition(record),
        "explanation_short": explanation_short,
        "explanation_full": explanation_full,
        "claims": claims,
    }


def _extract_arrow_section(text: str, label: str) -> str:
    pattern = re.compile(
        rf"{re.escape(label)}\s*->\s*(?P<section>.+?)(?=(?:\.\s+[A-Z]|$))",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return str(match.group("section")).strip().rstrip(".")


def _parse_label_value_pairs(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for match in GENERIC_VALUE_PATTERN.finditer(text):
        label = str(match.group("label")).strip().strip(",")
        if not label:
            continue
        items.append(
            {
                "label": label,
                "value": float(str(match.group("value")).rstrip(".,;:")),
            }
        )
    return items


def _parse_rank_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pattern in RANK_ITEM_PATTERNS:
        for match in pattern.finditer(text):
            items.append(
                {
                    "feature": str(match.group("feature")).strip(),
                    "rank": int(match.group("rank")),
                    "score": float(match.group("score")),
                }
            )
    unique: dict[str, dict[str, Any]] = {}
    for item in items:
        unique[item["feature"]] = item
    return sorted(unique.values(), key=lambda item: item["rank"])


def _parse_narrative_feature_values(text: str) -> list[dict[str, Any]]:
    patterns = (
        re.compile(
            r"(?P<label>[A-Za-z0-9_+\-/]+)\s+is\s+(?:the\s+)?(?:largest|highest|top)[^0-9]*(?P<value>[0-9.]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<label>[A-Za-z0-9_+\-/]+)\s+at\s+(?P<value>[0-9.]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<label>[A-Za-z0-9_+\-/]+)\s*\((?P<value>[0-9.]+)\)",
            re.IGNORECASE,
        ),
    )
    items: dict[str, float] = {}
    for pattern in patterns:
        for match in pattern.finditer(text):
            label = str(match.group("label")).strip()
            if not label or label.lower() in {"r2", "rmse", "mse", "mae"}:
                continue
            items.setdefault(label, float(str(match.group("value")).rstrip(".,;:")))
    return [{"label": label, "value": value} for label, value in items.items()]


def _feature_metric_claims(metric: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []
    ordered = sorted(items, key=lambda item: float(item["value"]), reverse=True)
    top_item = ordered[0]
    ordered_items = [str(item["label"]) for item in ordered[:3]]
    top_label = str(top_item["label"])
    return [
        {
            "claim_id": f"baseline-top-{metric}",
            "claim_text": f"{top_label} is the top feature by {metric}.",
            "claim_type": "top_feature",
            "span_category": "sentence",
            "is_numeric": False,
            "requires_grounding_from": "table/json",
            "confidence": 0.9,
            "object": top_label,
            "metric": metric,
        },
        {
            "claim_id": f"baseline-ranking-{metric}",
            "claim_text": f"The {metric} ordering is {' > '.join(ordered_items)}.",
            "claim_type": "ranking",
            "span_category": "sentence",
            "is_numeric": False,
            "requires_grounding_from": "table/json",
            "confidence": 0.86,
            "metric": metric,
            "ordered_items": ordered_items,
        },
        {
            "claim_id": f"baseline-metric-{metric}",
            "claim_text": f"{top_label} has {metric}={top_item['value']}.",
            "claim_type": "metric_value",
            "span_category": "sentence",
            "is_numeric": True,
            "requires_grounding_from": "table/json",
            "confidence": 0.88,
            "subject": top_label,
            "metric": metric,
            "value": float(top_item["value"]),
        },
    ]


def _build_model_comparison_claims(text: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    best_model = ""
    for pattern in BEST_MODEL_PATTERNS:
        match = pattern.search(text)
        if match:
            best_model = str(match.group("model")).strip()
            break

    if best_model:
        claims.append(
            {
                "claim_id": "baseline-best-model",
                "claim_text": f"{best_model} is the best model in the comparison.",
                "claim_type": "best_model",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.9,
                "object": best_model,
            }
        )

    if best_model:
        for metric_name, pattern in (
            ("r2_score", r"R[²2]\s*=\s*([0-9.]+)"),
            ("rmse", r"RMSE\s*=\s*([0-9.]+)"),
            ("mse", r"MSE\s*=\s*([0-9.]+)"),
            ("mae", r"MAE\s*=\s*([0-9.]+)"),
        ):
            match = re.search(
                rf"\b{re.escape(best_model)}\b[^.]*?{pattern}",
                text,
                re.IGNORECASE,
            )
            if match:
                value = float(match.group(1))
                claims.append(
                    {
                        "claim_id": f"baseline-{metric_name}",
                        "claim_text": f"{best_model} achieved {metric_name}={value}.",
                        "claim_type": "metric_value",
                        "span_category": "sentence",
                        "is_numeric": True,
                        "requires_grounding_from": "table/json",
                        "confidence": 0.88,
                        "subject": best_model,
                        "metric": metric_name,
                        "value": value,
                    }
                )

    r2_by_model: dict[str, float] = {}
    if best_model:
        best_match = re.search(
            rf"\b{re.escape(best_model)}\b[^.]*?R[²2]\s*=\s*([0-9.]+)",
            text,
            re.IGNORECASE,
        )
        if best_match:
            r2_by_model[best_model] = float(best_match.group(1))
    for match in R2_INLINE_PATTERN.finditer(text):
        r2_by_model[str(match.group("model")).strip()] = float(match.group("value"))

    weakest_match = WEAKEST_MODEL_PATTERN.search(text)
    if weakest_match:
        weakest_model = str(weakest_match.group("model")).strip()
        if weakest_model not in r2_by_model:
            r2_by_model[weakest_model] = float("-inf")

    if len(r2_by_model) >= 2:
        ordered_items = [model for model, _ in sorted(r2_by_model.items(), key=lambda item: item[1], reverse=True)]
        claims.append(
            {
                "claim_id": "baseline-ranking",
                "claim_text": f"The model ranking by R2 is {' > '.join(ordered_items)}.",
                "claim_type": "ranking",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "metric": "r2_score",
                "ordered_items": ordered_items,
            }
        )

    return claims


def _build_incremental_claims(text: str) -> list[dict[str, Any]]:
    matches = [
        {
            "model": str(match.group("model")).strip(),
            "count": int(match.group("count")),
            "r2": float(match.group("r2")),
            "mse": float(match.group("mse")),
        }
        for match in BEST_STEP_PATTERN.finditer(text)
    ]
    if not matches:
        return []

    best_by_r2 = max(matches, key=lambda item: item["r2"])
    ranked_models = [item["model"] for item in sorted(matches, key=lambda item: item["r2"], reverse=True)]
    return [
        {
            "claim_id": "baseline-feature-optimum",
            "claim_text": f"{best_by_r2['model']} reaches its best subset at {best_by_r2['count']} features.",
            "claim_type": "feature_subset_optimum",
            "span_category": "sentence",
            "is_numeric": True,
            "requires_grounding_from": "table/json",
            "confidence": 0.88,
            "subject": best_by_r2["model"],
            "feature_count": best_by_r2["count"],
            "value": best_by_r2["count"],
        },
        {
            "claim_id": "baseline-best-r2",
            "claim_text": f"{best_by_r2['model']} reaches R2={best_by_r2['r2']} at its best step.",
            "claim_type": "metric_value",
            "span_category": "sentence",
            "is_numeric": True,
            "requires_grounding_from": "table/json",
            "confidence": 0.86,
            "subject": best_by_r2["model"],
            "metric": "r2_score",
            "value": best_by_r2["r2"],
        },
        {
            "claim_id": "baseline-ranking",
            "claim_text": f"The best-step R2 ranking is {' > '.join(ranked_models[:3])}.",
            "claim_type": "ranking",
            "span_category": "sentence",
            "is_numeric": False,
            "requires_grounding_from": "table/json",
            "confidence": 0.8,
            "metric": "r2_score",
            "ordered_items": ranked_models[:3],
        },
    ]


def _build_gra_claims(text: str) -> list[dict[str, Any]]:
    items = _parse_rank_items(text)
    if not items:
        return []

    top_item = items[0]
    ordered_items = [item["feature"] for item in items[:3]]
    return [
        {
            "claim_id": "baseline-top-feature",
            "claim_text": f"{top_item['feature']} is the top feature in the GRA ranking.",
            "claim_type": "top_feature",
            "span_category": "sentence",
            "is_numeric": False,
            "requires_grounding_from": "table/json",
            "confidence": 0.9,
            "object": top_item["feature"],
            "metric": "gra_score",
        },
        {
            "claim_id": "baseline-gra-ranking",
            "claim_text": f"The GRA ordering is {' > '.join(ordered_items)}.",
            "claim_type": "ranking",
            "span_category": "sentence",
            "is_numeric": False,
            "requires_grounding_from": "table/json",
            "confidence": 0.86,
            "metric": "gra_score",
            "ordered_items": ordered_items,
        },
        {
            "claim_id": "baseline-gra-score",
            "claim_text": f"{top_item['feature']} has gra_score={top_item['score']}.",
            "claim_type": "metric_value",
            "span_category": "sentence",
            "is_numeric": True,
            "requires_grounding_from": "table/json",
            "confidence": 0.88,
            "subject": top_item["feature"],
            "metric": "gra_score",
            "value": top_item["score"],
        },
    ]


def _build_feature_story_claims(text: str, section_label: str, metric: str) -> list[dict[str, Any]]:
    section = _extract_arrow_section(text, section_label) or text
    items = _parse_label_value_pairs(section)
    if not items:
        items = _parse_narrative_feature_values(section)
    return _feature_metric_claims(metric, items)


def _build_combined_feature_claims(text: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for section_label, metric in (
        ("GRA ranking", "gra_score"),
        ("Feature importance", "importance"),
        ("SHAP importance", "mean_abs_shap"),
        ("Top HPR correlations", "target_correlation"),
    ):
        section = _extract_arrow_section(text, section_label)
        items = _parse_label_value_pairs(section)
        if not items:
            continue
        ordered = sorted(items, key=lambda item: float(item["value"]), reverse=True)
        top_item = ordered[0]
        claims.append(
            {
                "claim_id": f"baseline-top-{metric}",
                "claim_text": f"{top_item['label']} is the top feature by {metric}.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.84,
                "object": str(top_item["label"]),
                "metric": metric,
            }
        )
    if claims:
        return claims

    narrative_sections = {
        "gra_score": re.search(r"GRA ranking\s*\((?P<section>.+?)\)", text, re.IGNORECASE),
        "importance": re.search(r"model feature importance\s*\((?P<section>.+?)\)", text, re.IGNORECASE),
        "mean_abs_shap": re.search(r"SHAP importance\s*\((?P<section>.+?)\)", text, re.IGNORECASE),
        "target_correlation": re.search(r"top HPR correlations include\s+(?P<section>.+?)(?:\)|, while|\.)", text, re.IGNORECASE),
    }
    for metric, match in narrative_sections.items():
        if not match:
            continue
        section = str(match.group("section")).strip()
        items = _parse_label_value_pairs(section)
        if not items:
            items = _parse_narrative_feature_values(section)
        if not items:
            continue
        top_item = max(items, key=lambda item: float(item["value"]))
        claims.append(
            {
                "claim_id": f"baseline-top-{metric}",
                "claim_text": f"{top_item['label']} is the top feature by {metric}.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "object": str(top_item["label"]),
                "metric": metric,
            }
        )
    if claims:
        return claims

    fallback_pattern = re.compile(
        r"(?P<feature>[A-Za-z0-9_+\-]+)\s+is\s+(?:also\s+)?top by\s+(?P<metric>[A-Za-z0-9_+\-]+)",
        re.IGNORECASE,
    )
    metric_alias = {
        "gra_score": "gra_score",
        "importance": "importance",
        "mean_abs_shap": "mean_abs_shap",
        "target_correlation": "target_correlation",
    }
    for match in fallback_pattern.finditer(text):
        metric = metric_alias.get(str(match.group("metric")).strip().lower())
        if not metric:
            continue
        claims.append(
            {
                "claim_id": f"baseline-top-{metric}",
                "claim_text": f"{match.group('feature')} is the top feature by {metric}.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "object": str(match.group("feature")).strip(),
                "metric": metric,
            }
        )
    return claims


def _build_correlation_claims(text: str) -> list[dict[str, Any]]:
    target_section = _extract_arrow_section(text, "Top HPR correlations")
    pair_section = _extract_arrow_section(text, "Strongest correlations")
    target_items = _parse_label_value_pairs(target_section)
    pair_items = _parse_label_value_pairs(pair_section)
    claims: list[dict[str, Any]] = []
    if target_items:
        ordered = sorted(target_items, key=lambda item: float(item["value"]), reverse=True)
        top_item = ordered[0]
        claims.append(
            {
                "claim_id": "baseline-top-target-feature",
                "claim_text": f"{top_item['label']} is the top feature by target_correlation.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.88,
                "object": str(top_item["label"]),
                "metric": "target_correlation",
            }
        )
        claims.append(
            {
                "claim_id": "baseline-target-ranking",
                "claim_text": f"The target_correlation ordering is {' > '.join(str(item['label']) for item in ordered[:3])}.",
                "claim_type": "ranking",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "metric": "target_correlation",
                "ordered_items": [str(item["label"]) for item in ordered[:3]],
            }
        )
    if pair_items:
        top_pair = max(pair_items, key=lambda item: float(item["value"]))
        claims.append(
            {
                "claim_id": "baseline-top-pair",
                "claim_text": f"{top_pair['label']} has correlation={top_pair['value']}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.84,
                "subject": str(top_pair["label"]),
                "metric": "correlation",
                "value": float(top_pair["value"]),
            }
        )
    if claims:
        return claims

    narrative_target = re.search(
        r"(?:highest correlations are|strongest positive correlations listed are|strongest links to HPR are)\s+(?P<section>.+?)(?:,?\s+so|\.)",
        text,
        re.IGNORECASE,
    )
    narrative_pairs = re.search(
        r"(?:strongest measurement-to-measurement links are|some pairs are very tightly linked, such as|strongest feature-to-feature links shown are)\s+(?P<section>.+?)(?:,?\s+with|\.)",
        text,
        re.IGNORECASE,
    )
    target_items = _parse_label_value_pairs(narrative_target.group("section")) if narrative_target else []
    pair_items = []
    if narrative_pairs:
        pair_items = [
            {"label": str(match.group("pair")).strip(), "value": float(str(match.group("value")).rstrip(".,;:"))}
            for match in re.finditer(
                r"(?P<pair>[A-Za-z0-9_+\- ]+vs [A-Za-z0-9_+\- ]+)\s*(?:=|\()(?P<value>[0-9.]+)",
                narrative_pairs.group("section"),
                re.IGNORECASE,
            )
        ]
    if target_items:
        ordered = sorted(target_items, key=lambda item: float(item["value"]), reverse=True)
        top_item = ordered[0]
        claims.append(
            {
                "claim_id": "baseline-top-target-feature",
                "claim_text": f"{top_item['label']} is the top feature by target_correlation.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "object": str(top_item["label"]),
                "metric": "target_correlation",
            }
        )
    if pair_items:
        top_pair = max(pair_items, key=lambda item: float(item["value"]))
        claims.append(
            {
                "claim_id": "baseline-top-pair",
                "claim_text": f"{top_pair['label']} has correlation={top_pair['value']}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.8,
                "subject": str(top_pair["label"]),
                "metric": "correlation",
                "value": float(top_pair["value"]),
            }
        )
    if claims:
        return claims

    target_match = re.search(
        r"strongest feature-to-target pattern is (?P<feature>[A-Za-z0-9_+\-]+)\s+at\s+(?P<value>[0-9.]+)",
        text,
        re.IGNORECASE,
    )
    pair_match = re.search(
        r"strongest pairwise correlation is (?P<pair>[A-Za-z0-9_+\- ]+?)=(?P<value>[0-9.]+)",
        text,
        re.IGNORECASE,
    )
    if target_match:
        claims.append(
            {
                "claim_id": "baseline-top-target-feature",
                "claim_text": f"{target_match.group('feature')} is the top feature by target_correlation.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "object": str(target_match.group("feature")).strip(),
                "metric": "target_correlation",
            }
        )
    if pair_match:
        claims.append(
            {
                "claim_id": "baseline-top-pair",
                "claim_text": f"{pair_match.group('pair').strip()} has correlation={pair_match.group('value')}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.8,
                "subject": str(pair_match.group("pair")).strip(),
                "metric": "correlation",
                "value": float(str(pair_match.group("value")).rstrip(".,;:")),
            }
        )
    return claims


def _build_distribution_claims(text: str) -> list[dict[str, Any]]:
    mean_section = _extract_arrow_section(text, "Highest mean features")
    std_section = _extract_arrow_section(text, "Highest std features")
    mean_items = _parse_label_value_pairs(mean_section)
    std_items = _parse_label_value_pairs(std_section)
    if not mean_items:
        mean_match = re.search(
            r"highest average \(mean\) features are (?P<section>.+?)(?:,?\s+while|\.)",
            text,
            re.IGNORECASE,
        )
        if mean_match:
            mean_items = _parse_label_value_pairs(mean_match.group("section"))
    if not std_items:
        std_match = re.search(
            r"(?:most variable .*?(?:include|are)|highest standard deviation.*?(?:include|are))\s+(?P<section>.+?)(?:\.|$)",
            text,
            re.IGNORECASE,
        )
        if std_match:
            std_items = _parse_label_value_pairs(std_match.group("section"))
    claims: list[dict[str, Any]] = []
    if mean_items:
        ordered_mean = sorted(mean_items, key=lambda item: float(item["value"]), reverse=True)
        top_mean = ordered_mean[0]
        claims.append(
            {
                "claim_id": "baseline-top-mean",
                "claim_text": f"{top_mean['label']} is the top feature by mean.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.88,
                "object": str(top_mean["label"]),
                "metric": "mean",
            }
        )
        claims.append(
            {
                "claim_id": "baseline-mean-ranking",
                "claim_text": f"The mean ordering is {' > '.join(str(item['label']) for item in ordered_mean[:3])}.",
                "claim_type": "ranking",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "metric": "mean",
                "ordered_items": [str(item["label"]) for item in ordered_mean[:3]],
            }
        )
    if std_items:
        ordered_std = sorted(std_items, key=lambda item: float(item["value"]), reverse=True)
        top_std = ordered_std[0]
        claims.append(
            {
                "claim_id": "baseline-top-std",
                "claim_text": f"{top_std['label']} is the top feature by std.",
                "claim_type": "top_feature",
                "span_category": "sentence",
                "is_numeric": False,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "object": str(top_std["label"]),
                "metric": "std",
            }
        )
    return claims


def _parse_model_name(text: str) -> str:
    fallback = KNOWN_MODEL_PATTERN.search(text)
    if fallback:
        return str(fallback.group("model")).strip()
    match = MODEL_NAME_PATTERN.search(text)
    return str(match.group("model")).strip() if match else ""


def _metrics_from_arrow_text(text: str) -> dict[str, float]:
    section = text.split("->", 1)[1] if "->" in text else text
    metrics: dict[str, float] = {}
    alias_map = {
        "R2": "r2_score",
        "R²": "r2_score",
        "RMSE": "rmse",
        "MSE": "mse",
        "MAE": "mae",
        "corr(pred,actual)": "pred_actual_correlation",
        "corr(pred, actual)": "pred_actual_correlation",
        "predicted-vs-actual correlation": "pred_actual_correlation",
        "slope": "linear_fit_slope",
        "residual_mean": "residual_mean",
        "residual_std": "residual_std",
        "max_abs_residual": "max_abs_residual",
        "max absolute residual": "max_abs_residual",
        "p95_abs_residual": "p95_abs_residual",
        "actual_peak_index": "actual_peak_index",
        "actual peak occurs at index": "actual_peak_index",
        "actual_peak_value": "actual_peak_value",
        "predicted_peak_index": "predicted_peak_index",
        "predicted peak occurs later at index": "predicted_peak_index",
        "predicted_peak_value": "predicted_peak_value",
        "mean_abs_gap": "mean_abs_gap",
        "mean absolute gap": "mean_abs_gap",
        "max_abs_gap": "max_abs_gap",
        "max absolute gap": "max_abs_gap",
        "sequence_correlation": "sequence_correlation",
        "sequence correlation": "sequence_correlation",
        "predicted_min": "predicted_min",
        "predicted_max": "predicted_max",
        "actual_min": "actual_min",
        "actual_max": "actual_max",
    }
    for match in PREDICTION_METRIC_PATTERN.finditer(section):
        label = str(match.group("label")).strip()
        normalized = alias_map.get(label, label.lower())
        metrics[normalized] = float(str(match.group("value")).rstrip(".,;:"))
    return metrics


def _build_prediction_metric_claims(text: str, third_metric: str) -> list[dict[str, Any]]:
    model_name = _parse_model_name(text)
    metrics = _metrics_from_arrow_text(text)
    if not model_name or not metrics:
        return []

    claims: list[dict[str, Any]] = []
    if "r2_score" in metrics:
        claims.append(
            {
                "claim_id": "baseline-r2",
                "claim_text": f"{model_name} has r2_score={metrics['r2_score']}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.88,
                "subject": model_name,
                "metric": "r2_score",
                "value": metrics["r2_score"],
            }
        )
    if "pred_actual_correlation" in metrics:
        claims.append(
            {
                "claim_id": "baseline-correlation",
                "claim_text": f"{model_name} has pred_actual_correlation={metrics['pred_actual_correlation']}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.86,
                "subject": model_name,
                "metric": "pred_actual_correlation",
                "value": metrics["pred_actual_correlation"],
            }
        )
    if third_metric in metrics:
        claims.append(
            {
                "claim_id": f"baseline-{third_metric}",
                "claim_text": f"{model_name} has {third_metric}={metrics[third_metric]}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.84,
                "subject": model_name,
                "metric": third_metric,
                "value": metrics[third_metric],
            }
        )
    if not claims and "residual_mean" in metrics:
        claims.append(
            {
                "claim_id": "baseline-residual-mean",
                "claim_text": f"{model_name} has residual_mean={metrics['residual_mean']}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.82,
                "subject": model_name,
                "metric": "residual_mean",
                "value": metrics["residual_mean"],
            }
        )
    return claims


def _build_sequence_claims(text: str) -> list[dict[str, Any]]:
    model_name = _parse_model_name(text)
    metrics = _metrics_from_arrow_text(text)
    if not model_name or "sequence_correlation" not in metrics:
        return []
    claims: list[dict[str, Any]] = []
    for metric_name in ("sequence_correlation", "mean_abs_gap", "actual_peak_index", "predicted_peak_index"):
        if metric_name not in metrics:
            continue
        claims.append(
            {
                "claim_id": f"baseline-{metric_name}",
                "claim_text": f"{model_name} has {metric_name}={metrics[metric_name]}.",
                "claim_type": "metric_value",
                "span_category": "sentence",
                "is_numeric": True,
                "requires_grounding_from": "table/json",
                "confidence": 0.84,
                "subject": model_name,
                "metric": metric_name,
                "value": metrics[metric_name],
            }
        )
    return claims


def _build_claims(record: ManifestRecord, text: str) -> list[dict[str, Any]]:
    if record.asset_family == "model_comparison_chart":
        return _build_model_comparison_claims(text)
    if record.asset_family == "incremental_feature_analysis_chart":
        return _build_incremental_claims(text)
    if record.asset_family == "feature_ranking":
        return _build_gra_claims(text)
    if record.asset_family == "feature_story_shap":
        return _build_feature_story_claims(text, "SHAP importance", "mean_abs_shap")
    if record.asset_family == "feature_story_importance":
        return _build_feature_story_claims(text, "Feature importance", "importance")
    if record.asset_family == "feature_analysis_combined":
        return _build_combined_feature_claims(text)
    if record.asset_family == "correlation":
        return _build_correlation_claims(text)
    if record.asset_family == "distribution":
        return _build_distribution_claims(text)
    if record.asset_family == "prediction_overview":
        return _build_prediction_metric_claims(text, "max_abs_residual")
    if record.asset_family == "prediction_residuals":
        return _build_prediction_metric_claims(text, "residual_std")
    if record.asset_family == "prediction_scatter":
        return _build_prediction_metric_claims(text, "linear_fit_slope")
    if record.asset_family == "prediction_sequence":
        return _build_sequence_claims(text)
    if record.artifact_type == "model_comparison/main":
        return _build_model_comparison_claims(text)
    if record.artifact_type == "incremental_feature_analysis/main":
        return _build_incremental_claims(text)
    if record.artifact_type == "feature_ranking/gra":
        return _build_gra_claims(text)
    return []


def load_llm_baseline_generations(
    bundle_dir: Path,
    records: list[ManifestRecord],
) -> tuple[list[ExplanationOutput], list[str]]:
    explanation_path = bundle_dir / "llm_explanations.json"
    if not explanation_path.exists():
        return [], []

    payload = read_json(explanation_path)
    generations: list[ExplanationOutput] = []
    for record in records:
        asset_key, asset_entry = _find_asset_entry(payload, record)
        if not asset_key or not asset_entry:
            raise ValueError(
                f"{record.artifact_id}: no matching baseline asset found in llm_explanations.json."
            )

        raw_payload = _structured_generation_payload(
            record=record,
            asset_key=asset_key,
            asset_entry=asset_entry,
        )

        generations.append(
            normalize_generation(
                payload=raw_payload,
                artifact_id=record.artifact_id,
                arm=BASELINE_ARM,
                input_condition=_baseline_condition(record),
            )
        )

    return generations, []
