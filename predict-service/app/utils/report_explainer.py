from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_REPORT_MODEL = os.getenv("OPENAI_REPORT_MODEL", "gpt-5.2")
EXPLANATIONS_FILENAME = "llm_explanations.json"

EXPLAINABLE_ASSET_LABELS: Dict[str, str] = {
    "metrics_overview": "Trained metrics overview",
    "fig3a_gra_ranking": "Figure 3A - Grey relational ranking",
    "fig3b_shap_analysis": "Figure 3B - SHAP analysis",
    "fig3_feature_analysis": "Figure 3 - Combined feature analysis",
    "fig4_univariate_analysis": "Figure 4 - Univariate analysis",
    "fig5_model_comparison": "Figure 5 - Model comparison",
    "fig6ab_mse_r2_features": "Figure 6A/B - MSE and R² vs feature count",
    "fig6c_prediction_time": "Figure 6C - Prediction over time",
    "model_svm_scatter": "SVM scatter plot",
    "model_dt_scatter": "Decision tree scatter plot",
    "model_rf_scatter": "Random forest scatter plot",
    "model_knn_scatter": "KNN scatter plot",
    "model_xgboost_scatter": "XGBoost scatter plot",
    "model_comparison_bars": "Model comparison bars",
    "predicted_vs_actual": "Predicted versus actual chart",
    "residuals": "Residual analysis chart",
    "feature_importance": "Feature importance chart",
    "correlation_heatmap": "Correlation heatmap",
    "feature_distributions": "Feature distributions",
    "feature_vs_target": "Feature vs target chart",
    "boxplots": "Feature boxplots",
    "time_series": "Time-series chart",
    "model_comparison_table": "Model comparison table",
    "feature_importance_table": "Feature importance table",
    "best_model_shap_importance": "SHAP importance table",
    "descriptive_statistics": "Descriptive statistics table",
    "correlation_matrix": "Correlation matrix table",
    "table1_incremental_results": "Incremental feature analysis table",
}

TABLE_KEYS = {
    "model_comparison_table",
    "feature_importance_table",
    "best_model_shap_importance",
    "descriptive_statistics",
    "correlation_matrix",
    "table1_incremental_results",
}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _safe_records(df: pd.DataFrame, limit: int = 20) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    limited = df.head(limit).copy()
    limited = limited.where(pd.notna(limited), None)
    return json.loads(limited.to_json(orient="records", force_ascii=False))


def _read_text_excerpt(path: Path, max_chars: int = 3200) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    normalized_lines = [line.strip() for line in text.replace("\r", "\n").splitlines() if line.strip()]
    normalized = "\n".join(normalized_lines)
    if len(normalized) <= max_chars:
        return normalized

    clipped = normalized[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def _strongest_correlations(df: pd.DataFrame, limit: int = 12) -> List[Dict[str, Any]]:
    if df.empty:
        return []

    working = df.copy()
    first_col = str(working.columns[0])
    if first_col.lower().startswith("unnamed") or first_col == "":
        working = working.rename(columns={first_col: "feature"})

    if "feature" in working.columns:
        working = working.set_index("feature")

    pairs: List[Dict[str, Any]] = []
    labels = list(working.index)
    for row_index, row_label in enumerate(labels):
        for col_index, col_label in enumerate(working.columns):
            if row_label == col_label:
                continue
            if row_label not in working.columns:
                pass
            if col_index <= row_index and col_label in labels:
                continue

            try:
                value = float(working.iloc[row_index, col_index])
            except Exception:
                continue
            if pd.isna(value):
                continue
            pairs.append(
                {
                    "pair": f"{row_label} vs {col_label}",
                    "correlation": round(value, 4),
                    "abs_correlation": round(abs(value), 4),
                }
            )

    pairs.sort(key=lambda item: item["abs_correlation"], reverse=True)
    return pairs[:limit]


def _sort_model_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _sort_key(row: Dict[str, Any]) -> Any:
        try:
            r2 = float(row.get("r2_score"))
        except (TypeError, ValueError):
            r2 = float("-inf")
        try:
            mse = float(row.get("mse"))
        except (TypeError, ValueError):
            mse = float("inf")
        return (-r2, mse, str(row.get("model") or ""))

    return sorted(rows, key=_sort_key)


def _build_asset_evidence(
    explainable_assets: List[Dict[str, Any]],
    report_context: Dict[str, Any],
    pipeline_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    best_model = str(pipeline_result.get("best_model") or report_context.get("best_model") or "").strip()
    benchmark_rows = _sort_model_rows(list(report_context.get("model_comparison_table") or []))
    top_gra = list(report_context.get("gra_ranking") or [])[:5]
    top_features = list(report_context.get("top_features") or [])[:5]
    feature_importance = list(report_context.get("feature_importance_table") or [])[:6]
    shap_importance = list(report_context.get("shap_importance_table") or [])[:6]
    strongest_correlations = list(report_context.get("top_correlations") or [])[:6]
    descriptive_rows = list(report_context.get("descriptive_statistics_table") or [])[:6]
    incremental_rows = list(report_context.get("incremental_feature_table") or [])[:11]

    shared_blocks = {
        "model_metrics": {
            "winning_model": best_model,
            "benchmark_models_sorted": benchmark_rows[:5],
        },
        "feature_story": {
            "top_gra_features": top_gra,
            "top_feature_importance": feature_importance,
            "top_shap_features": shap_importance,
            "top_features_summary": top_features,
        },
        "data_shape": {
            "rows_after_preprocessing": report_context.get("rows_after_preprocessing"),
            "dataset_columns": list(report_context.get("dataset_columns") or []),
            "selected_sheet": report_context.get("selected_sheet"),
        },
        "distribution_story": {
            "descriptive_statistics_sample": descriptive_rows,
        },
        "correlation_story": {
            "strongest_correlations": strongest_correlations,
        },
        "incremental_story": {
            "incremental_feature_table": incremental_rows,
        },
    }

    evidence_map = {
        "metrics_overview": ["model_metrics", "data_shape"],
        "fig5_model_comparison": ["model_metrics"],
        "model_comparison_bars": ["model_metrics"],
        "model_comparison_table": ["model_metrics"],
        "predicted_vs_actual": ["model_metrics", "data_shape"],
        "residuals": ["model_metrics", "data_shape"],
        "model_svm_scatter": ["model_metrics"],
        "model_dt_scatter": ["model_metrics"],
        "model_rf_scatter": ["model_metrics"],
        "model_knn_scatter": ["model_metrics"],
        "model_xgboost_scatter": ["model_metrics"],
        "fig3a_gra_ranking": ["feature_story"],
        "fig3_feature_analysis": ["feature_story", "correlation_story"],
        "gra_ranking": ["feature_story"],
        "fig3b_shap_analysis": ["feature_story"],
        "best_model_shap_importance": ["feature_story"],
        "feature_importance": ["feature_story"],
        "feature_importance_table": ["feature_story"],
        "fig4_univariate_analysis": ["distribution_story", "correlation_story"],
        "feature_distributions": ["distribution_story"],
        "boxplots": ["distribution_story"],
        "feature_vs_target": ["distribution_story", "correlation_story"],
        "descriptive_statistics": ["distribution_story"],
        "correlation_heatmap": ["correlation_story"],
        "correlation_matrix": ["correlation_story"],
        "fig6ab_mse_r2_features": ["incremental_story", "model_metrics"],
        "table1_incremental_results": ["incremental_story", "model_metrics"],
        "fig6c_prediction_time": ["model_metrics", "data_shape"],
        "time_series": ["model_metrics", "data_shape"],
    }

    asset_evidence: List[Dict[str, Any]] = []
    for asset in explainable_assets:
        key = str(asset.get("key") or "")
        block_names = evidence_map.get(key, [])
        snippets = {name: shared_blocks[name] for name in block_names if name in shared_blocks}
        asset_evidence.append(
            {
                "key": key,
                "title": asset.get("title"),
                "kind": asset.get("kind"),
                "evidence": snippets,
            }
        )

    return asset_evidence


def _build_prompt_payload(
    report_dir: Path,
    report_info: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    runtime: Dict[str, Any] | None,
) -> Dict[str, Any]:
    files = dict(report_info.get("files") or {})
    explainable_assets: List[Dict[str, Any]] = [
        {
            "key": "metrics_overview",
            "title": EXPLAINABLE_ASSET_LABELS["metrics_overview"],
            "kind": "table",
        }
    ]

    for key, title in EXPLAINABLE_ASSET_LABELS.items():
        if key == "metrics_overview":
            continue
        if key in files:
            explainable_assets.append(
                {
                    "key": key,
                    "title": title,
                    "kind": "table" if key in TABLE_KEYS else "chart",
                }
            )

    model_comparison_df = _read_csv(report_dir / str(files.get("model_comparison_table", "")))
    feature_importance_df = _read_csv(report_dir / str(files.get("feature_importance_table", "")))
    shap_importance_df = _read_csv(report_dir / str(files.get("best_model_shap_importance", "")))
    descriptive_stats_df = _read_csv(report_dir / str(files.get("descriptive_statistics", "")))
    correlation_df = _read_csv(report_dir / str(files.get("correlation_matrix", "")))
    incremental_df = _read_csv(report_dir / str(files.get("table1_incremental_results", "")))
    analysis_summary_excerpt = _read_text_excerpt(report_dir / str(files.get("analysis_summary", "")))
    results_summary_excerpt = _read_text_excerpt(report_dir / str(files.get("results_summary", "")))

    cleaned_df = runtime.get("cleaned_df") if isinstance(runtime, dict) else None
    dataset_columns = list(cleaned_df.columns) if hasattr(cleaned_df, "columns") else []

    descriptive_rows = _safe_records(descriptive_stats_df, limit=8)
    for row in descriptive_rows:
        for key in list(row.keys()):
            if key not in {"feature", "mean", "std", "min", "max"} and key != descriptive_stats_df.columns[0]:
                row.pop(key, None)

    incremental_records = _safe_records(incremental_df, limit=11)
    benchmark_records = _sort_model_rows(_safe_records(model_comparison_df, limit=6))

    report_context = {
        "report_id": report_info.get("report_id"),
        "best_model": pipeline_result.get("best_model"),
        "selected_sheet": pipeline_result.get("selected_sheet"),
        "rows_after_preprocessing": pipeline_result.get("rows_after_preprocessing"),
        "top_features": pipeline_result.get("top_features"),
        "metrics": pipeline_result.get("metrics", {}),
        "gra_ranking": pipeline_result.get("gra_ranking", [])[:8],
        "dataset_columns": dataset_columns,
        "model_comparison_table": benchmark_records,
        "feature_importance_table": _safe_records(feature_importance_df, limit=8),
        "shap_importance_table": _safe_records(shap_importance_df, limit=8),
        "descriptive_statistics_table": descriptive_rows,
        "top_correlations": _strongest_correlations(correlation_df, limit=8),
        "incremental_feature_table": incremental_records,
        "analysis_summary_excerpt": analysis_summary_excerpt,
        "results_summary_excerpt": results_summary_excerpt,
    }
    asset_evidence = _build_asset_evidence(explainable_assets, report_context, pipeline_result)

    return {
        "task": (
            "Explain each machine-learning report chart or table for non-technical users. "
            "Use only the supplied evidence. If a pattern is weak or uncertain, say that clearly."
        ),
        "audience": "non-technical website users",
        "style_rules": [
            "Write one medium-length paragraph per asset.",
            "Keep the explanation concrete and friendly.",
            "Avoid heavy jargon. If a term matters, explain it in simple words.",
            "Do not mention OpenAI, prompting, or the model itself in the explanations.",
            "Do not invent numbers or trends that are not in the provided data.",
            "For each asset, clearly cover: what it shows, how to read it, the main takeaway, and one practical caution or limitation when relevant.",
            "Use concrete numbers, ranks, or feature names whenever they are available in the provided evidence.",
            "Make the explanation detailed enough that a non-technical reader can understand why the chart or table matters.",
        ],
        "languages": ["en", "zh_TW"],
        "assets": explainable_assets,
        "report_context": report_context,
        "asset_evidence": asset_evidence,
    }


def _chunk_assets(items: List[Dict[str, Any]], chunk_size: int) -> List[List[Dict[str, Any]]]:
    return [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)]


def _build_response_schema(explainable_keys: List[str]) -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "report_explanations",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "overview": {
                        "type": "object",
                        "properties": {
                            "en": {"type": "string"},
                            "zh_TW": {"type": "string"},
                        },
                        "required": ["en", "zh_TW"],
                        "additionalProperties": False,
                    },
                    "assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string", "enum": explainable_keys},
                                "en": {"type": "string"},
                                "zh_TW": {"type": "string"},
                            },
                            "required": ["key", "en", "zh_TW"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["overview", "assets"],
                "additionalProperties": False,
            },
        },
    }


def _build_overview_response_schema() -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "report_overview",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "overview": {
                        "type": "object",
                        "properties": {
                            "en": {"type": "string"},
                            "zh_TW": {"type": "string"},
                        },
                        "required": ["en", "zh_TW"],
                        "additionalProperties": False,
                    }
                },
                "required": ["overview"],
                "additionalProperties": False,
            },
        },
    }


def _call_openai(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    response = requests.post(
        OPENAI_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    choice = data["choices"][0]
    content = choice["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("OpenAI response did not contain a text JSON payload.")
    if not content.strip():
        raise ValueError(
            "OpenAI response returned empty content "
            f"(finish_reason={choice.get('finish_reason')!r})."
        )
    return json.loads(content)


def _generate_global_overview(
    prompt_payload: Dict[str, Any],
    api_key: str,
) -> Dict[str, str]:
    overview_payload = {
        "task": (
            "Write one comprehensive report overview for a non-technical reader. "
            "This overview must synthesize the whole report, using the full report context and the asset_evidence list together."
        ),
        "audience": prompt_payload.get("audience"),
        "languages": prompt_payload.get("languages"),
        "assets": prompt_payload.get("assets"),
        "report_context": prompt_payload.get("report_context"),
        "asset_evidence": prompt_payload.get("asset_evidence"),
        "style_rules": [
            "Write one cohesive overview in each language.",
            "Use exactly 3 paragraphs in each language, returned as a single string with newline breaks between paragraphs.",
            "Paragraph 1 must explain the dataset scope, the winning model, and the main model-comparison results with concrete metrics.",
            "Paragraph 2 must explain the feature story across GRA, feature importance, SHAP, and correlation results, including where the methods agree or disagree.",
            "Paragraph 3 must explain what the incremental feature table and the rest of the report suggest overall, plus the most important caution or limitation for non-technical readers.",
            "Treat the asset_evidence list as the complete set of explainable charts and tables shown on the website, and synthesize them into one narrative instead of describing only a single figure.",
            "If multiple charts show the same evidence in different visual forms, merge them into one clear takeaway instead of repeating yourself.",
            "Use the provided results_summary_excerpt and analysis_summary_excerpt when they help connect the charts and tables into one overall story.",
            "This overview must mention the report as a whole rather than describing only one figure.",
            "Use concrete numbers, model names, feature names, ranks, and metrics whenever they are available.",
            "Make the explanation understandable for a non-technical user without removing important detail.",
            "Do not use bullet lists.",
            "Do not invent information that is not present in the supplied evidence.",
        ],
    }

    request_payload = {
        "model": OPENAI_REPORT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a bilingual machine-learning report summarizer for non-technical users. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(overview_payload, ensure_ascii=False),
            },
        ],
        "response_format": _build_overview_response_schema(),
        "reasoning_effort": "low",
        "verbosity": "medium",
        "max_completion_tokens": 2800,
    }

    parsed = _call_openai(request_payload, api_key)
    overview = parsed.get("overview", {})
    return {
        "en": str(overview.get("en") or "").strip(),
        "zh_TW": str(overview.get("zh_TW") or "").strip(),
    }


def _update_summary_file(
    summary_path: Path,
    explanation_payload: Dict[str, Any],
) -> None:
    summary = _read_json(summary_path)
    files = dict(summary.get("files") or {})
    files["llm_explanations"] = EXPLANATIONS_FILENAME
    summary["files"] = files
    summary["llm_explanations"] = explanation_payload
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_report_explanations(
    report_info: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    runtime: Dict[str, Any] | None = None,
    report_root: str | Path | None = None,
) -> Dict[str, Any] | None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("⚠️ Skipping OpenAI report explanations: OPENAI_API_KEY is not configured.")
        return None

    report_id = str(report_info.get("report_id") or "").strip()
    if not report_id:
        return None

    report_dir = Path(report_root or Path(__file__).resolve().parents[1] / "reports") / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    prompt_payload = _build_prompt_payload(
        report_dir=report_dir,
        report_info=report_info,
        pipeline_result=pipeline_result,
        runtime=runtime,
    )
    all_assets = list(prompt_payload["assets"])
    overview = {"en": "", "zh_TW": ""}
    asset_map: Dict[str, Dict[str, str]] = {}

    try:
        overview = _generate_global_overview(prompt_payload, api_key)
    except Exception as exc:
        print(f"⚠️ OpenAI global overview generation failed: {exc}")

    for batch_index, asset_batch in enumerate(_chunk_assets(all_assets, 2)):
        batch_keys = [item["key"] for item in asset_batch]
        batch_payload = dict(prompt_payload)
        batch_payload["assets"] = asset_batch
        batch_payload["style_rules"] = list(prompt_payload["style_rules"]) + [
            "For each chart or table, write about 2-4 sentences in each language.",
            "For the overview, write about 3-4 sentences in each language.",
            "Do not use bullets. Write complete, readable prose.",
        ]

        response_format = _build_response_schema(batch_keys)
        request_payload = {
            "model": OPENAI_REPORT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a bilingual machine-learning report explainer for non-technical users. "
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(batch_payload, ensure_ascii=False),
                },
            ],
            "response_format": response_format,
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }

        try:
            parsed = _call_openai(request_payload, api_key)
        except Exception as exc:
            print(f"⚠️ OpenAI explanation generation failed on batch {batch_index + 1}: {exc}")
            return None

        if batch_index == 0 and not any(overview.values()):
            overview = {
                "en": str(parsed.get("overview", {}).get("en") or "").strip(),
                "zh_TW": str(parsed.get("overview", {}).get("zh_TW") or "").strip(),
            }

        for item in parsed.get("assets", []):
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            asset_map[key] = {
                "en": str(item.get("en") or "").strip(),
                "zh_TW": str(item.get("zh_TW") or "").strip(),
            }

    explanation_payload = {
        "provider": "openai",
        "model": OPENAI_REPORT_MODEL,
        "generated_at": datetime.now().isoformat(),
        "overview": overview,
        "assets": asset_map,
    }

    explanation_path = report_dir / EXPLANATIONS_FILENAME
    explanation_path.write_text(
        json.dumps(explanation_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_path = report_dir / "summary.json"
    if summary_path.exists():
        _update_summary_file(summary_path, explanation_payload)

    files = dict(report_info.get("files") or {})
    files["llm_explanations"] = EXPLANATIONS_FILENAME
    report_info["files"] = files
    report_info["llm_explanations"] = explanation_payload

    return explanation_payload
