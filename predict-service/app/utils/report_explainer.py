from __future__ import annotations

import copy
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

import numpy as np
import pandas as pd
import requests
from benchmarking.schemas import CANONICAL_CLAIM_TYPES
from dotenv import load_dotenv
from groq_key_pool import GroqApiKeyPool, groq_api_keys_from_env, parse_groq_api_keys
from openai_rate_control import shared_openai_request_gate

DEFAULT_OPENAI_CHAT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_REPORT_MODEL = "gpt-5.2"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_REPORT_MODEL = "gemma2:9b"
DEFAULT_OLLAMA_NUM_CTX = 16384
DEFAULT_GROQ_CHAT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_REPORT_MODEL = "openai/gpt-oss-120b"
SUPPORTED_LLM_PROVIDERS = {"openai", "ollama", "groq"}
GROQ_REPORT_MODELS = {
    "openai/gpt-oss-120b": "GPT-OSS 120B",
    "llama-3.3-70b-versatile": "Llama 3.3 70B Versatile",
}
OPENAI_CHAT_COMPLETIONS_URL = f"{DEFAULT_OPENAI_CHAT_BASE_URL}/chat/completions"
OPENAI_REPORT_MODEL = os.getenv("OPENAI_REPORT_MODEL", DEFAULT_OPENAI_REPORT_MODEL)
GROQ_REPORT_MODEL = os.getenv("GROQ_REPORT_MODEL", DEFAULT_GROQ_REPORT_MODEL)
OPENAI_REPORT_MAX_RETRIES = max(1, int(os.getenv("OPENAI_REPORT_MAX_RETRIES", "8")))
GROQ_REPORT_MAX_RETRIES = max(1, int(os.getenv("GROQ_REPORT_MAX_RETRIES", "5")))
GROQ_REPORT_RETRY_FOREVER = str(
    os.getenv("GROQ_REPORT_RETRY_FOREVER", "1")
).strip().lower() not in {"0", "false", "no", "off"}
GROQ_REPORT_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0,
    float(os.getenv("GROQ_REPORT_MIN_REQUEST_INTERVAL_SECONDS", "3")),
)
GROQ_REPORT_MAX_RETRY_WAIT_SECONDS = max(
    1.0,
    float(os.getenv("GROQ_REPORT_MAX_RETRY_WAIT_SECONDS", "3")),
)
OPENAI_REPORT_RETRY_BACKOFF_SECONDS = max(
    1.0,
    float(os.getenv("OPENAI_REPORT_RETRY_BACKOFF_SECONDS", "8")),
)
GROQ_REPORT_RETRY_BACKOFF_SECONDS = max(
    1.0,
    float(os.getenv("GROQ_REPORT_RETRY_BACKOFF_SECONDS", "3")),
)
OPENAI_REPORT_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0,
    float(os.getenv("OPENAI_REPORT_MIN_REQUEST_INTERVAL_SECONDS", "6")),
)
OPENAI_REPORT_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("OPENAI_REPORT_RETRY_JITTER_SECONDS", "1.0")),
)
GROQ_REPORT_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("GROQ_REPORT_RETRY_JITTER_SECONDS", "0.5")),
)
OPENAI_REPORT_ASSET_BATCH_SIZE = max(1, int(os.getenv("OPENAI_REPORT_ASSET_BATCH_SIZE", "1")))
OPENAI_REPORT_ASSET_MAX_COMPLETION_TOKENS = max(
    2000,
    int(os.getenv("OPENAI_REPORT_ASSET_MAX_COMPLETION_TOKENS", "3200")),
)
OPENAI_REPORT_OVERVIEW_MAX_COMPLETION_TOKENS = max(
    1200,
    int(os.getenv("OPENAI_REPORT_OVERVIEW_MAX_COMPLETION_TOKENS", "1800")),
)
GROQ_REPORT_ASSET_MAX_COMPLETION_TOKENS = max(
    500,
    int(os.getenv("GROQ_REPORT_ASSET_MAX_COMPLETION_TOKENS", "900")),
)
GROQ_REPORT_OVERVIEW_MAX_COMPLETION_TOKENS = max(
    500,
    int(os.getenv("GROQ_REPORT_OVERVIEW_MAX_COMPLETION_TOKENS", "900")),
)
EXPLANATIONS_FILENAME = "llm_explanations.json"
ASSET_EVIDENCE_FILENAME = "asset_evidence.json"
STATUS_FILENAME = "llm_explanations_status"

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


def _provider_display_name(provider: str) -> str:
    if provider == "groq":
        return "Groq"
    if provider == "ollama":
        return "Ollama"
    return "OpenAI"


def _get_llm_provider(provider_override: str | None = None) -> str:
    provider = str(
        provider_override
        or os.getenv("REPORT_LLM_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or "openai"
    ).strip().lower()
    if provider not in SUPPORTED_LLM_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        raise RuntimeError(
            f"Unsupported REPORT_LLM_PROVIDER '{provider}'. Supported values: {supported}."
        )
    return provider


def _get_report_model(provider: str, model_override: str | None = None) -> str:
    if model_override and str(model_override).strip():
        model = str(model_override).strip()
        if provider == "groq" and model not in GROQ_REPORT_MODELS:
            allowed = ", ".join(GROQ_REPORT_MODELS)
            raise RuntimeError(
                f"Unsupported Groq report model '{model}'. Supported values: {allowed}."
            )
        return model
    if provider == "groq":
        model = str(
            os.getenv("GROQ_REPORT_MODEL")
            or os.getenv("REPORT_LLM_MODEL")
            or os.getenv("LLM_MODEL")
            or DEFAULT_GROQ_REPORT_MODEL
        ).strip()
        if model not in GROQ_REPORT_MODELS:
            allowed = ", ".join(GROQ_REPORT_MODELS)
            raise RuntimeError(
                f"Unsupported Groq report model '{model}'. Supported values: {allowed}."
            )
    elif provider == "ollama":
        model = str(
            os.getenv("OLLAMA_REPORT_MODEL")
            or os.getenv("REPORT_LLM_MODEL")
            or os.getenv("LLM_MODEL")
            or DEFAULT_OLLAMA_REPORT_MODEL
        ).strip()
    else:
        model = str(
            os.getenv("OPENAI_REPORT_MODEL")
            or os.getenv("REPORT_LLM_MODEL")
            or os.getenv("LLM_MODEL")
            or DEFAULT_OPENAI_REPORT_MODEL
        ).strip()

    if not model:
        raise RuntimeError(
            f"{_provider_display_name(provider)} report model is not configured."
        )
    return model


def _get_openai_chat_completions_url() -> str:
    base_url = str(
        os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENAI_CHAT_BASE_URL
    ).strip().rstrip("/")
    return f"{base_url}/chat/completions"


def _get_openai_api_key() -> str:
    return str(os.getenv("OPENAI_API_KEY") or "").strip()


def _get_groq_chat_completions_url() -> str:
    base_url = str(
        os.getenv("GROQ_BASE_URL") or DEFAULT_GROQ_CHAT_BASE_URL
    ).strip().rstrip("/")
    return f"{base_url}/chat/completions"


def _get_groq_api_keys(api_keys_override: Any | None = None) -> List[str]:
    override_keys = parse_groq_api_keys(api_keys_override)
    if override_keys:
        return override_keys
    return groq_api_keys_from_env()


def _groq_supports_json_schema(model: str) -> bool:
    return str(model or "").strip().startswith("openai/gpt-oss")


def _needs_inline_json_schema_instruction(provider: str, model: str) -> bool:
    if provider == "ollama":
        return True
    if provider == "groq":
        return True
    return False


def _get_ollama_chat_url() -> str:
    base_url = str(
        os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL
    ).strip().rstrip("/")
    return f"{base_url}/api/chat"


def _get_ollama_num_ctx() -> int:
    raw_value = str(os.getenv("OLLAMA_NUM_CTX") or DEFAULT_OLLAMA_NUM_CTX).strip()
    try:
        value = int(raw_value)
    except ValueError:
        value = DEFAULT_OLLAMA_NUM_CTX
    return max(4096, value)


def _extract_json_object(raw_content: str, provider: str) -> Dict[str, Any]:
    candidates: List[str] = []
    stripped = raw_content.strip()
    if stripped:
        candidates.append(stripped)

        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                fenced_body = "\n".join(lines[1:-1]).strip()
                if fenced_body:
                    candidates.append(fenced_body)

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            embedded_json = stripped[start:end + 1].strip()
            if embedded_json:
                candidates.append(embedded_json)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError(
        f"{_provider_display_name(provider)} response did not contain a valid JSON object."
    )


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


def _safe_float(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not np.isfinite(number):
        return None

    return round(number, digits)


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe_value(value.item())
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def _normalize_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    working = df.copy()
    first_col = str(working.columns[0])
    if first_col.lower().startswith("unnamed") or first_col == "":
        working = working.rename(columns={first_col: "feature"})

    if "feature" in working.columns:
        working = working.set_index("feature")

    return working


def _top_target_correlations(
    df: pd.DataFrame,
    target: str = "HPR",
    limit: int = 6,
) -> List[Dict[str, Any]]:
    working = _normalize_matrix(df)
    if working.empty or target not in working.columns:
        return []

    pairs: List[Dict[str, Any]] = []
    series = working[target].drop(labels=[target], errors="ignore")
    for feature, value in series.items():
        try:
            corr = float(value)
        except (TypeError, ValueError):
            continue
        if pd.isna(corr):
            continue
        pairs.append(
            {
                "feature": str(feature),
                "correlation": round(corr, 4),
                "abs_correlation": round(abs(corr), 4),
            }
        )

    pairs.sort(key=lambda item: item["abs_correlation"], reverse=True)
    return pairs[:limit]


def _row_feature_name(row: Dict[str, Any]) -> str:
    return str(
        row.get("feature")
        or row.get("Unnamed: 0")
        or row.get("index")
        or row.get("name")
        or ""
    ).strip()


def _feature_distribution_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "highest_mean_features": [],
            "highest_std_features": [],
        }

    by_mean = sorted(
        [
            {
                "feature": _row_feature_name(row),
                "mean": _safe_float(row.get("mean"), 4),
            }
            for row in rows
            if _row_feature_name(row)
        ],
        key=lambda item: item["mean"] if item["mean"] is not None else float("-inf"),
        reverse=True,
    )
    by_std = sorted(
        [
            {
                "feature": _row_feature_name(row),
                "std": _safe_float(row.get("std"), 4),
            }
            for row in rows
            if _row_feature_name(row)
        ],
        key=lambda item: item["std"] if item["std"] is not None else float("-inf"),
        reverse=True,
    )

    return {
        "highest_mean_features": by_mean[:5],
        "highest_std_features": by_std[:5],
    }


def _incremental_model_bests(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    df = pd.DataFrame(rows)
    results: List[Dict[str, Any]] = []
    for model_name in ("SVM", "DT", "RF", "KNN", "XGBoost"):
        r2_col = f"{model_name}_R2"
        mse_col = f"{model_name}_MSE"
        if r2_col not in df.columns or mse_col not in df.columns:
            continue

        ranked = (
            df[["n_features", "feature_subset", r2_col, mse_col]]
            .dropna(subset=[r2_col, mse_col], how="any")
            .sort_values(by=[r2_col, mse_col], ascending=[False, True])
        )
        if ranked.empty:
            continue

        best_row = ranked.iloc[0]
        results.append(
            {
                "model": model_name,
                "best_n_features": int(best_row["n_features"]),
                "best_feature_subset": str(best_row["feature_subset"]),
                "best_r2": _safe_float(best_row[r2_col], 6),
                "best_mse": _safe_float(best_row[mse_col], 6),
            }
        )

    return results


def _prediction_diagnostics(y_true: Any, y_pred: Any) -> Dict[str, Any]:
    actual = np.asarray(y_true, dtype=float).reshape(-1)
    predicted = np.asarray(y_pred, dtype=float).reshape(-1)
    sample_count = min(actual.size, predicted.size)
    if sample_count == 0:
        return {}

    actual = actual[:sample_count]
    predicted = predicted[:sample_count]
    residuals = predicted - actual
    abs_residuals = np.abs(residuals)

    diagnostics: Dict[str, Any] = {
        "sample_count": int(sample_count),
        "actual_min": _safe_float(np.min(actual), 6),
        "actual_max": _safe_float(np.max(actual), 6),
        "predicted_min": _safe_float(np.min(predicted), 6),
        "predicted_max": _safe_float(np.max(predicted), 6),
        "residual_mean": _safe_float(np.mean(residuals), 6),
        "residual_std": _safe_float(np.std(residuals), 6),
        "mean_abs_residual": _safe_float(np.mean(abs_residuals), 6),
        "max_abs_residual": _safe_float(np.max(abs_residuals), 6),
        "p95_abs_residual": _safe_float(np.percentile(abs_residuals, 95), 6),
    }

    largest_error_index = int(np.argmax(abs_residuals))
    diagnostics["largest_error_index"] = largest_error_index
    diagnostics["largest_error_actual"] = _safe_float(actual[largest_error_index], 6)
    diagnostics["largest_error_predicted"] = _safe_float(predicted[largest_error_index], 6)

    if sample_count > 1:
        corr = np.corrcoef(actual, predicted)[0, 1]
        diagnostics["pred_actual_correlation"] = _safe_float(corr, 6)
        try:
            slope, intercept = np.polyfit(actual, predicted, 1)
            diagnostics["linear_fit_slope"] = _safe_float(slope, 6)
            diagnostics["linear_fit_intercept"] = _safe_float(intercept, 6)
        except Exception:
            diagnostics["linear_fit_slope"] = None
            diagnostics["linear_fit_intercept"] = None

    return diagnostics


def _sequence_diagnostics(y_actual: Any, y_predicted: Any) -> Dict[str, Any]:
    actual = np.asarray(y_actual, dtype=float).reshape(-1)
    predicted = np.asarray(y_predicted, dtype=float).reshape(-1)
    sample_count = min(actual.size, predicted.size)
    if sample_count == 0:
        return {}

    actual = actual[:sample_count]
    predicted = predicted[:sample_count]
    abs_gap = np.abs(predicted - actual)

    diagnostics: Dict[str, Any] = {
        "sample_count": int(sample_count),
        "actual_peak_index": int(np.argmax(actual)),
        "actual_peak_value": _safe_float(np.max(actual), 6),
        "predicted_peak_index": int(np.argmax(predicted)),
        "predicted_peak_value": _safe_float(np.max(predicted), 6),
        "mean_abs_gap": _safe_float(np.mean(abs_gap), 6),
        "max_abs_gap": _safe_float(np.max(abs_gap), 6),
    }

    if sample_count > 1:
        corr = np.corrcoef(actual, predicted)[0, 1]
        diagnostics["sequence_correlation"] = _safe_float(corr, 6)

    return diagnostics


def _format_model_metric_rows(rows: List[Dict[str, Any]], limit: int = 5) -> str:
    formatted = []
    for row in rows[:limit]:
        model_name = str(row.get("model") or "").strip()
        if not model_name:
            continue
        formatted.append(
            (
                f"{model_name}: R2={_safe_float(row.get('r2_score'), 4)}, "
                f"RMSE={_safe_float(row.get('rmse'), 4)}, "
                f"MSE={_safe_float(row.get('mse'), 5)}, "
                f"MAE={_safe_float(row.get('mae'), 4)}"
            )
        )
    return " | ".join(formatted)


def _format_ranked_feature_rows(
    rows: List[Dict[str, Any]],
    value_key: str,
    limit: int = 5,
) -> str:
    formatted = []
    for row in rows[:limit]:
        feature = _row_feature_name(row)
        if not feature:
            feature = str(row.get("feature") or "").strip()
        if not feature:
            continue
        formatted.append(f"{feature}={_safe_float(row.get(value_key), 4)}")
    return " | ".join(formatted)


def _persist_asset_evidence(
    report_dir: Path,
    report_info: Dict[str, Any],
    payload: Dict[str, Any],
) -> None:
    evidence_path = report_dir / ASSET_EVIDENCE_FILENAME
    evidence_path.write_text(
        json.dumps(_json_safe_value(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    files = dict(report_info.get("files") or {})
    files["asset_evidence"] = ASSET_EVIDENCE_FILENAME
    report_info["files"] = files

    summary_path = report_dir / "summary.json"
    if summary_path.exists():
        summary = _read_json(summary_path)
        summary_files = dict(summary.get("files") or {})
        summary_files["asset_evidence"] = ASSET_EVIDENCE_FILENAME
        summary["files"] = summary_files
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _build_asset_evidence(
    explainable_assets: List[Dict[str, Any]],
    report_info: Dict[str, Any],
    report_context: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    runtime: Dict[str, Any] | None,
) -> Dict[str, Any]:
    files = dict(report_info.get("files") or {})
    route_prefix = str(report_info.get("route_prefix") or "").strip()
    best_model = str(pipeline_result.get("best_model") or report_context.get("best_model") or "").strip()
    benchmark_rows = _sort_model_rows(list(report_context.get("model_comparison_table") or []))
    top_gra = list(report_context.get("gra_ranking") or [])[:5]
    top_features = list(report_context.get("top_features") or [])[:5]
    feature_importance = list(report_context.get("feature_importance_table") or [])[:6]
    shap_importance = list(report_context.get("shap_importance_table") or [])[:6]
    strongest_correlations = list(report_context.get("top_correlations") or [])[:6]
    target_correlations = list(report_context.get("target_correlations") or [])[:6]
    descriptive_rows = list(report_context.get("descriptive_statistics_table") or [])[:6]
    incremental_rows = list(report_context.get("incremental_feature_table") or [])[:11]
    incremental_bests = _incremental_model_bests(incremental_rows)
    distribution_summary = _feature_distribution_summary(descriptive_rows)

    model_results = dict(runtime.get("model_results") or {}) if isinstance(runtime, dict) else {}
    y_test_series = runtime.get("y_test_series") if isinstance(runtime, dict) else None
    prediction_diagnostics: Dict[str, Dict[str, Any]] = {}
    for model_name, metrics in model_results.items():
        y_pred_test = metrics.get("y_pred_test") if isinstance(metrics, dict) else None
        if y_test_series is None or y_pred_test is None:
            continue
        prediction_diagnostics[model_name] = _prediction_diagnostics(y_test_series, y_pred_test)

    winning_diagnostics = prediction_diagnostics.get(best_model, {})
    sequence_evidence: Dict[str, Any] = {}
    if isinstance(runtime, dict):
        best_model_object = runtime.get("best_model_object")
        X_norm_df = runtime.get("X_norm_df")
        y_norm_series = runtime.get("y_norm_series")
        if best_model_object is not None and X_norm_df is not None and y_norm_series is not None:
            try:
                sequence_predictions = best_model_object.predict(np.asarray(X_norm_df))
                sequence_evidence = _sequence_diagnostics(y_norm_series, sequence_predictions)
            except Exception:
                sequence_evidence = {}

    shared_blocks = {
        "model_metrics": {
            "winning_model": best_model,
            "benchmark_models_sorted": benchmark_rows[:5],
            "best_model_metrics": report_context.get("metrics", {}),
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
            "top_target_correlations": target_correlations,
        },
        "incremental_story": {
            "incremental_feature_table": incremental_rows,
            "best_step_per_model": incremental_bests,
        },
        "prediction_story": {
            "winning_model_diagnostics": winning_diagnostics,
            "per_model_prediction_diagnostics": prediction_diagnostics,
        },
        "sequence_story": {
            "winning_model_sequence_diagnostics": sequence_evidence,
        },
    }

    model_metrics_text = (
        f"Winning model: {best_model}. "
        f"Benchmark test metrics -> {_format_model_metric_rows(benchmark_rows)}."
    ).strip()
    gra_text = (
        "GRA ranking -> "
        f"{_format_ranked_feature_rows(top_gra, 'score')}."
    ).strip()
    shap_text = (
        "SHAP importance -> "
        f"{_format_ranked_feature_rows(shap_importance, 'mean_abs_shap')}."
    ).strip()
    feature_importance_text = (
        "Feature importance -> "
        f"{_format_ranked_feature_rows(feature_importance, 'importance')}."
    ).strip()
    correlation_text = (
        "Strongest correlations -> "
        + " | ".join(
            f"{item['pair']}={item['correlation']}"
            for item in strongest_correlations[:5]
        )
        + ". "
        + "Top HPR correlations -> "
        + " | ".join(
            f"{item['feature']}={item['correlation']}"
            for item in target_correlations[:5]
        )
        + "."
    ).strip()
    distribution_text = (
        "Highest mean features -> "
        + " | ".join(
            f"{item['feature']}={item['mean']}"
            for item in distribution_summary["highest_mean_features"][:5]
        )
        + ". Highest std features -> "
        + " | ".join(
            f"{item['feature']}={item['std']}"
            for item in distribution_summary["highest_std_features"][:5]
        )
        + "."
    ).strip()
    incremental_text = (
        "Best feature-count step per model -> "
        + " | ".join(
            (
                f"{item['model']}: n={item['best_n_features']}, "
                f"R2={item['best_r2']}, MSE={item['best_mse']}"
            )
            for item in incremental_bests
        )
        + "."
    ).strip()

    asset_evidence_items: List[Dict[str, Any]] = []
    for asset in explainable_assets:
        key = str(asset.get("key") or "")
        asset_file = str(files.get(key) or "")
        source_files = ["summary.json"]
        result_text = ""
        snippets: Dict[str, Any] = {}

        if key in {"metrics_overview", "fig5_model_comparison", "model_comparison_bars", "model_comparison_table"}:
            snippets = {
                "model_metrics": shared_blocks["model_metrics"],
                "data_shape": shared_blocks["data_shape"],
            }
            result_text = model_metrics_text
            source_files.extend(["table_model_comparison.csv", "results_summary.txt", "analysis_summary_report.txt"])
        elif key in {"fig3a_gra_ranking", "gra_ranking"}:
            snippets = {"feature_story": shared_blocks["feature_story"]}
            result_text = gra_text
            source_files.extend(["gra_ranking.json", "results_summary.txt", "best_model_summary.json"])
        elif key in {"fig3b_shap_analysis", "best_model_shap_importance"}:
            snippets = {"feature_story": shared_blocks["feature_story"]}
            result_text = shap_text
            source_files.extend(["best_model_shap_importance.csv", "best_model_summary.json"])
        elif key in {"feature_importance", "feature_importance_table"}:
            snippets = {"feature_story": shared_blocks["feature_story"]}
            result_text = feature_importance_text
            source_files.extend(["table_feature_importance.csv", "best_model_summary.json"])
        elif key == "fig3_feature_analysis":
            snippets = {
                "feature_story": shared_blocks["feature_story"],
                "correlation_story": shared_blocks["correlation_story"],
                "incremental_story": shared_blocks["incremental_story"],
            }
            result_text = " ".join([gra_text, feature_importance_text, shap_text, correlation_text, incremental_text]).strip()
            source_files.extend(
                [
                    "gra_ranking.json",
                    "table_feature_importance.csv",
                    "best_model_shap_importance.csv",
                    "table_correlation_matrix.csv",
                    "table1_incremental_results.csv",
                ]
            )
        elif key in {"fig4_univariate_analysis", "feature_vs_target"}:
            snippets = {
                "distribution_story": shared_blocks["distribution_story"],
                "correlation_story": shared_blocks["correlation_story"],
            }
            result_text = correlation_text
            source_files.extend(["table_correlation_matrix.csv", "table_descriptive_statistics.csv", "analysis_summary_report.txt"])
        elif key in {"descriptive_statistics", "feature_distributions", "boxplots"}:
            snippets = {"distribution_story": shared_blocks["distribution_story"]}
            result_text = distribution_text
            source_files.extend(["table_descriptive_statistics.csv"])
        elif key in {"correlation_heatmap", "correlation_matrix"}:
            snippets = {"correlation_story": shared_blocks["correlation_story"]}
            result_text = correlation_text
            source_files.extend(["table_correlation_matrix.csv", "analysis_summary_report.txt"])
        elif key in {"fig6ab_mse_r2_features", "table1_incremental_results"}:
            snippets = {
                "incremental_story": shared_blocks["incremental_story"],
                "model_metrics": shared_blocks["model_metrics"],
            }
            result_text = incremental_text
            source_files.extend(["table1_incremental_results.csv", "results_summary.txt"])
        elif key in {"predicted_vs_actual", "residuals"}:
            snippets = {
                "model_metrics": shared_blocks["model_metrics"],
                "prediction_story": shared_blocks["prediction_story"],
                "data_shape": shared_blocks["data_shape"],
            }
            result_text = (
                f"{best_model} prediction diagnostics -> "
                f"R2={_safe_float(report_context.get('metrics', {}).get('r2_score'), 4)}, "
                f"RMSE={_safe_float(report_context.get('metrics', {}).get('rmse'), 4)}, "
                f"MAE={_safe_float(report_context.get('metrics', {}).get('mae'), 4)}, "
                f"residual_mean={winning_diagnostics.get('residual_mean')}, "
                f"residual_std={winning_diagnostics.get('residual_std')}, "
                f"max_abs_residual={winning_diagnostics.get('max_abs_residual')}, "
                f"corr(pred,actual)={winning_diagnostics.get('pred_actual_correlation')}."
            )
            source_files.extend(["table_model_comparison.csv", "best_model_summary.json"])
        elif key in {"fig6c_prediction_time", "time_series"}:
            snippets = {
                "model_metrics": shared_blocks["model_metrics"],
                "sequence_story": shared_blocks["sequence_story"],
                "data_shape": shared_blocks["data_shape"],
            }
            result_text = (
                f"{best_model} sequence diagnostics -> "
                f"actual_peak_index={sequence_evidence.get('actual_peak_index')}, "
                f"actual_peak_value={sequence_evidence.get('actual_peak_value')}, "
                f"predicted_peak_index={sequence_evidence.get('predicted_peak_index')}, "
                f"predicted_peak_value={sequence_evidence.get('predicted_peak_value')}, "
                f"mean_abs_gap={sequence_evidence.get('mean_abs_gap')}, "
                f"sequence_correlation={sequence_evidence.get('sequence_correlation')}."
            )
            source_files.extend(["best_model_summary.json", "analysis_summary_report.txt"])
        elif key.startswith("model_") and key.endswith("_scatter"):
            model_name = key.replace("model_", "").replace("_scatter", "").upper()
            if model_name == "XGBOOST":
                model_name = "XGBoost"
            diag = prediction_diagnostics.get(model_name, {})
            metrics_row = next((row for row in benchmark_rows if str(row.get("model")) == model_name), {})
            snippets = {
                "model_metrics": {
                    "model_name": model_name,
                    "metrics": metrics_row,
                },
                "prediction_story": {
                    "diagnostics": diag,
                },
            }
            result_text = (
                f"{model_name} scatter diagnostics -> "
                f"R2={_safe_float(metrics_row.get('r2_score'), 4)}, "
                f"RMSE={_safe_float(metrics_row.get('rmse'), 4)}, "
                f"MAE={_safe_float(metrics_row.get('mae'), 4)}, "
                f"corr(pred,actual)={diag.get('pred_actual_correlation')}, "
                f"slope={diag.get('linear_fit_slope')}, "
                f"max_abs_residual={diag.get('max_abs_residual')}."
            )
            source_files.extend(["table_model_comparison.csv"])
        else:
            snippets = {
                "model_metrics": shared_blocks["model_metrics"],
                "data_shape": shared_blocks["data_shape"],
            }
            result_text = model_metrics_text

        asset_evidence_items.append(
            _json_safe_value(
                {
                    "key": key,
                    "title": asset.get("title"),
                    "kind": asset.get("kind"),
                    "asset_file": asset_file or None,
                    "route_prefix": route_prefix or None,
                    "source_files": sorted(set(file_name for file_name in source_files if file_name)),
                    "result_text": result_text,
                    "evidence": snippets,
                }
            )
        )

    return {
        "generated_at": datetime.now().isoformat(),
        "report_id": report_context.get("report_id"),
        "best_model": best_model,
        "assets": asset_evidence_items,
    }


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
    best_model_summary = _read_json(report_dir / str(files.get("best_model_summary", "")))
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

    summary_metrics = best_model_summary.get("metrics") if isinstance(best_model_summary, dict) else {}
    if not isinstance(summary_metrics, dict):
        summary_metrics = {}
    if not summary_metrics and isinstance(best_model_summary, dict):
        summary_metrics = {
            "r2_score": best_model_summary.get("r2"),
            "mse": best_model_summary.get("mse"),
            "mae": best_model_summary.get("mae"),
            "rmse": best_model_summary.get("rmse"),
        }

    report_context = {
        "report_id": report_info.get("report_id"),
        "best_model": pipeline_result.get("best_model") or best_model_summary.get("best_model"),
        "selected_sheet": pipeline_result.get("selected_sheet"),
        "rows_after_preprocessing": (
            pipeline_result.get("rows_after_preprocessing")
            or best_model_summary.get("rows_after_preprocessing")
            or best_model_summary.get("total_samples")
        ),
        "top_features": pipeline_result.get("top_features") or best_model_summary.get("top_features"),
        "metrics": pipeline_result.get("metrics") or summary_metrics,
        "gra_ranking": (pipeline_result.get("gra_ranking") or best_model_summary.get("gra_ranking") or [])[:8],
        "dataset_columns": dataset_columns,
        "model_comparison_table": benchmark_records,
        "feature_importance_table": _safe_records(feature_importance_df, limit=8),
        "shap_importance_table": _safe_records(shap_importance_df, limit=8),
        "descriptive_statistics_table": descriptive_rows,
        "top_correlations": _strongest_correlations(correlation_df, limit=8),
        "target_correlations": _top_target_correlations(correlation_df, limit=8),
        "incremental_feature_table": incremental_records,
        "analysis_summary_excerpt": analysis_summary_excerpt,
        "results_summary_excerpt": results_summary_excerpt,
    }
    asset_evidence_payload = _build_asset_evidence(
        explainable_assets=explainable_assets,
        report_info=report_info,
        report_context=report_context,
        pipeline_result=pipeline_result,
        runtime=runtime if isinstance(runtime, dict) else None,
    )
    _persist_asset_evidence(report_dir, report_info, asset_evidence_payload)
    asset_evidence = list(asset_evidence_payload.get("assets") or [])

    return {
        "task": (
            "Explain each machine-learning report chart or table for non-technical users. "
            "Use only the supplied evidence. If a pattern is weak or uncertain, say that clearly."
        ),
        "audience": "non-technical website users",
        "style_rules": [
            "Write one concise paragraph per asset.",
            "Keep the explanation concrete and friendly.",
            "Avoid heavy jargon. If a term matters, explain it in simple words.",
            "Do not mention OpenAI, prompting, or the model itself in the explanations.",
            "Do not invent numbers or trends that are not in the provided data.",
            "For each asset, clearly cover: what it shows, how to read it, the main takeaway, and one practical caution or limitation when relevant.",
            "Use concrete numbers, ranks, or feature names whenever they are available in the provided evidence.",
            "Keep the explanation short enough to fit in a compact chart caption.",
        ],
        "languages": ["en", "zh_TW"],
        "assets": explainable_assets,
        "report_context": report_context,
        "asset_evidence": asset_evidence,
        "asset_evidence_file": ASSET_EVIDENCE_FILENAME,
    }


def _asset_scoped_report_context(report_context: Dict[str, Any]) -> Dict[str, Any]:
    """Keep per-asset explanation prompts small; global context is only for overview."""
    if not isinstance(report_context, dict):
        return {}
    compact: Dict[str, Any] = {}
    for key in (
        "report_id",
        "best_model",
        "selected_sheet",
        "rows_after_preprocessing",
        "metrics",
    ):
        value = report_context.get(key)
        if value not in (None, "", [], {}):
            compact[key] = value
    return compact


def _chunk_assets(items: List[Dict[str, Any]], chunk_size: int) -> List[List[Dict[str, Any]]]:
    return [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)]


def _report_claim_schema() -> Dict[str, Any]:
    scalar_or_null = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "null"},
        ]
    }
    string_array_or_null = {
        "anyOf": [
            {
                "type": "array",
                "items": {"type": "string"},
            },
            {"type": "null"},
        ]
    }
    return {
        "type": "object",
        "properties": {
            "claim_id": {"type": "string"},
            "claim_text": {"type": "string"},
            "claim_type": {"type": "string", "enum": list(CANONICAL_CLAIM_TYPES)},
            "span_category": {"type": "string"},
            "is_numeric": {"type": "boolean"},
            "requires_grounding_from": {"type": "string"},
            "confidence": {"type": "number"},
            "subject": {"type": ["string", "null"]},
            "predicate": {"type": ["string", "null"]},
            "object": scalar_or_null,
            "metric": {"type": ["string", "null"]},
            "value": scalar_or_null,
            "unit": {"type": ["string", "null"]},
            "ordered_items": string_array_or_null,
            "feature_count": {"type": ["integer", "null"]},
            "hedged": {"type": "boolean"},
        },
        "required": [
            "claim_id",
            "claim_text",
            "claim_type",
            "span_category",
            "is_numeric",
            "requires_grounding_from",
            "confidence",
            "subject",
            "predicate",
            "object",
            "metric",
            "value",
            "unit",
            "ordered_items",
            "feature_count",
            "hedged",
        ],
        "additionalProperties": False,
    }


def _report_benchmark_payload_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "explanation_short": {"type": "string"},
            "explanation_full": {"type": "string"},
            "claims": {
                "type": "array",
                "items": _report_claim_schema(),
            },
        },
        "required": [
            "explanation_short",
            "explanation_full",
            "claims",
        ],
        "additionalProperties": False,
    }


def _normalize_benchmark_payload(
    asset_key: str,
    raw_payload: Any,
    english_text: str,
) -> Dict[str, Any]:
    if not isinstance(raw_payload, dict):
        raise ValueError(f"Asset '{asset_key}' is missing benchmark_payload.")

    explanation_short = str(raw_payload.get("explanation_short") or "").strip()
    explanation_full = str(raw_payload.get("explanation_full") or "").strip()
    claims = raw_payload.get("claims")

    if not explanation_short:
        explanation_short = english_text.split(".")[0].strip() or english_text
    if not explanation_full:
        explanation_full = english_text
    if not isinstance(claims, list):
        claims = []
    normalized_claims = []
    for claim in claims:
        if isinstance(claim, dict):
            claim = dict(claim)
            if not isinstance(claim.get("ordered_items"), list):
                claim["ordered_items"] = []
        normalized_claims.append(_json_safe_value(claim))

    return {
        "explanation_short": explanation_short,
        "explanation_full": english_text,
        "claims": normalized_claims,
    }


def _normalize_asset_explanation_item(item: Dict[str, Any]) -> Dict[str, Any]:
    asset_key = str(item.get("key") or "").strip()
    if not asset_key:
        raise ValueError("OpenAI explanation response omitted the asset key.")

    english_text = str(item.get("en") or "").strip()
    raw_benchmark_payload = item.get("benchmark_payload")
    if not english_text and isinstance(raw_benchmark_payload, dict):
        english_text = str(
            raw_benchmark_payload.get("explanation_full")
            or raw_benchmark_payload.get("explanation_short")
            or ""
        ).strip()
    if not english_text:
        raise ValueError(f"Asset '{asset_key}' returned an empty English explanation.")

    return {
        "en": english_text,
        "zh_TW": str(item.get("zh_TW") or "").strip(),
        "benchmark_payload": _normalize_benchmark_payload(
            asset_key=asset_key,
            raw_payload=raw_benchmark_payload,
            english_text=english_text,
        ),
    }


def _build_response_schema(
    explainable_keys: List[str],
    *,
    include_overview: bool = False,
) -> Dict[str, Any]:
    properties: Dict[str, Any] = {
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "enum": explainable_keys},
                    "en": {"type": "string"},
                    "zh_TW": {"type": "string"},
                    "benchmark_payload": _report_benchmark_payload_schema(),
                },
                "required": ["key", "en", "zh_TW", "benchmark_payload"],
                "additionalProperties": False,
            },
        },
    }
    required = ["assets"]

    if include_overview:
        properties["overview"] = {
            "type": "object",
            "properties": {
                "en": {"type": "string"},
                "zh_TW": {"type": "string"},
            },
            "required": ["en", "zh_TW"],
            "additionalProperties": False,
        }
        required.insert(0, "overview")

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "report_explanations",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required,
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


def _build_ollama_json_only_instruction(
    response_schema: Dict[str, Any],
    *,
    allowed_keys: List[str] | None = None,
) -> str:
    schema = response_schema["json_schema"]["schema"]
    compact_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    instructions = [
        "Return ONLY one valid JSON object.",
        "Do not output markdown, explanations, headings, or prose outside JSON.",
        "The JSON must exactly match this schema:",
        compact_schema,
        "If any field is uncertain, use an empty string or an empty array, but keep the JSON valid.",
    ]
    if allowed_keys:
        instructions.append(
            "Allowed asset keys for this request: " + ", ".join(allowed_keys) + "."
        )
        instructions.append(
            "Include every listed key exactly once in the assets array."
        )
    return " ".join(instructions)


def _report_retry_after_seconds(response: requests.Response | None) -> float | None:
    if response is None:
        return None

    retry_after = str(response.headers.get("Retry-After") or "").strip()
    if not retry_after:
        return None

    try:
        return max(0.0, float(retry_after))
    except ValueError:
        return None


def _groq_retry_after_seconds(response: requests.Response | None) -> float | None:
    retry_after = _report_retry_after_seconds(response)
    if retry_after is not None:
        return retry_after
    if response is None:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    message = str((payload.get("error") or {}).get("message") or payload.get("message") or "")
    match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return max(0.0, float(match.group(1)))
    except ValueError:
        return None


def _response_error_payload(response: requests.Response | None) -> Dict[str, Any]:
    if response is None:
        return {}
    try:
        payload = response.json()
    except ValueError:
        text = str(getattr(response, "text", "") or "").strip()
        return {"message": text[:1000]} if text else {}
    return payload if isinstance(payload, dict) else {}


def _format_http_error(exc: requests.HTTPError, provider: str) -> str:
    response = exc.response
    status_code = response.status_code if response is not None else "unknown"
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    message = str(
        error_payload.get("message")
        or payload.get("message")
        or getattr(response, "text", "")
        or exc
    ).strip()
    code = str(error_payload.get("code") or payload.get("code") or "").strip()
    detail = f"{provider} request failed with HTTP {status_code}"
    if code:
        detail += f" ({code})"
    if message:
        detail += f": {message[:1000]}"
    return detail


def _is_groq_json_validate_failed(response: requests.Response | None) -> bool:
    if response is None or response.status_code != 400:
        return False
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = str(error_payload.get("code") or payload.get("code") or "").strip()
    return code == "json_validate_failed"


def _is_groq_rate_limit_error(response: requests.Response | None) -> bool:
    if response is None:
        return False
    if response.status_code == 429:
        return True
    if response.status_code != 413:
        return False
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = str(error_payload.get("code") or payload.get("code") or "").strip().lower()
    message = str(error_payload.get("message") or payload.get("message") or "").lower()
    return code == "rate_limit_exceeded" or "tokens per minute" in message


def _report_error_status_code(error: Exception) -> int | None:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        return int(error.response.status_code)
    return None


def _report_retry_reason(error: Exception, provider_label: str = "OpenAI") -> str:
    status_code = _report_error_status_code(error)
    if status_code in {413, 429}:
        return f"{provider_label} rate limit"
    if status_code is not None and status_code >= 500:
        return f"{provider_label} server error"
    return f"{provider_label} request retry"


def _format_retry_status_message(
    scope_label: str,
    attempt: int,
    max_attempts: int,
    wait_seconds: float,
    error: Exception,
    provider_label: str = "OpenAI",
) -> str:
    reason = _report_retry_reason(error, provider_label=provider_label)
    status_code = _report_error_status_code(error)
    status_text = f"HTTP {status_code}" if status_code is not None else "request error"
    max_attempts_text = "∞" if int(max_attempts) <= 0 else str(int(max_attempts))
    return (
        f"{reason} while {scope_label}. "
        f"Retry {attempt}/{max_attempts_text} in {wait_seconds:.1f}s ({status_text})."
    )


def _build_retry_payload(
    scope_label: str,
    attempt: int,
    max_attempts: int,
    wait_seconds: float,
    error: Exception,
    provider_label: str = "OpenAI",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "scope": scope_label,
        "attempt": int(attempt),
        "max_attempts": int(max_attempts),
        "retry_forever": int(max_attempts) <= 0,
        "wait_seconds": round(float(wait_seconds), 1),
        "reason": _report_retry_reason(error, provider_label=provider_label),
    }
    status_code = _report_error_status_code(error)
    if status_code is not None:
        payload["status_code"] = status_code
    return payload


def _call_openai(
    payload: Dict[str, Any],
    api_key: str,
    on_retry: Callable[[int, int, float, Exception], None] | None = None,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(1, OPENAI_REPORT_MAX_RETRIES + 1):
        try:
            with shared_openai_request_gate().request_slot(
                OPENAI_REPORT_MIN_REQUEST_INTERVAL_SECONDS,
                OPENAI_REPORT_RETRY_JITTER_SECONDS,
            ):
                response = requests.post(
                    _get_openai_chat_completions_url(),
                    headers=headers,
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
            return _extract_json_object(content, "openai")
        except requests.HTTPError as exc:
            last_error = exc
            status_code = exc.response.status_code if exc.response is not None else None
            should_retry = status_code == 429 or (status_code is not None and status_code >= 500)
            if not should_retry or attempt >= OPENAI_REPORT_MAX_RETRIES:
                raise
            retry_after_seconds = _report_retry_after_seconds(exc.response)
        except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= OPENAI_REPORT_MAX_RETRIES:
                raise
            retry_after_seconds = None

        wait_seconds = max(
            retry_after_seconds or 0.0,
            OPENAI_REPORT_RETRY_BACKOFF_SECONDS * attempt,
        ) + random.uniform(0.0, OPENAI_REPORT_RETRY_JITTER_SECONDS)
        shared_openai_request_gate().push_cooldown(wait_seconds)
        if on_retry is not None:
            on_retry(attempt, OPENAI_REPORT_MAX_RETRIES, wait_seconds, last_error)
        print(
            f"⚠️ OpenAI request attempt {attempt}/{OPENAI_REPORT_MAX_RETRIES} failed: "
            f"{last_error}. Retrying in {wait_seconds:.1f}s."
        )
        time.sleep(wait_seconds)

    raise RuntimeError(f"OpenAI request failed after {OPENAI_REPORT_MAX_RETRIES} attempts: {last_error}")


def _chat_message_content(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        text_parts: List[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content") or ""
            if isinstance(text, str) and text.strip():
                text_parts.append(text)
        return "".join(text_parts).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _call_groq(
    payload: Dict[str, Any],
    api_keys: Any,
    on_retry: Callable[[int, int, float, Exception], None] | None = None,
) -> Dict[str, Any]:
    key_pool = GroqApiKeyPool(parse_groq_api_keys(api_keys))
    last_error: Exception | None = None
    attempt = 0
    while True:
        attempt += 1
        key_pool.wait_for_available_key(GROQ_REPORT_MAX_RETRY_WAIT_SECONDS)
        key_index, api_key = key_pool.next_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            with shared_openai_request_gate().request_slot(
                GROQ_REPORT_MIN_REQUEST_INTERVAL_SECONDS,
                GROQ_REPORT_RETRY_JITTER_SECONDS,
            ):
                response = requests.post(
                    _get_groq_chat_completions_url(),
                    headers=headers,
                    json=payload,
                    timeout=300,
                )
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]
            message = choice.get("message") or {}
            parsed = message.get("parsed")
            if isinstance(parsed, dict):
                return parsed

            content = _chat_message_content(message)
            if not content:
                finish_reason = choice.get("finish_reason")
                if finish_reason == "length":
                    raise ValueError(
                        "Groq response hit finish_reason='length' before emitting JSON. "
                        "Increase max_completion_tokens or reduce prompt size."
                    )
                raise ValueError("Groq response did not contain a text JSON payload.")
            return _extract_json_object(content, "groq")
        except requests.HTTPError as exc:
            last_error = exc
            status_code = exc.response.status_code if exc.response is not None else None
            should_retry = (
                _is_groq_rate_limit_error(exc.response)
                or (status_code is not None and status_code >= 500)
                or _is_groq_json_validate_failed(exc.response)
            )
            if not should_retry or (not GROQ_REPORT_RETRY_FOREVER and attempt >= GROQ_REPORT_MAX_RETRIES):
                raise RuntimeError(_format_http_error(exc, "Groq")) from exc
            retry_after_seconds = (
                None
                if _is_groq_json_validate_failed(exc.response)
                else _groq_retry_after_seconds(exc.response)
            )
            if _is_groq_rate_limit_error(exc.response):
                key_pool.mark_rate_limited(
                    key_index,
                    retry_after_seconds or GROQ_REPORT_MAX_RETRY_WAIT_SECONDS,
                )
        except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            if not GROQ_REPORT_RETRY_FOREVER and attempt >= GROQ_REPORT_MAX_RETRIES:
                raise
            retry_after_seconds = None

        has_ready_key = key_pool.has_available_key()
        wait_seconds = max(
            retry_after_seconds or 0.0,
            GROQ_REPORT_RETRY_BACKOFF_SECONDS * attempt,
            (
                0.0
                if has_ready_key and key_pool.size > 1
                else GROQ_REPORT_MAX_RETRY_WAIT_SECONDS
                if GROQ_REPORT_RETRY_FOREVER
                else 0.0
            ),
        ) + random.uniform(0.0, GROQ_REPORT_RETRY_JITTER_SECONDS)
        wait_seconds = min(wait_seconds, GROQ_REPORT_MAX_RETRY_WAIT_SECONDS)
        if wait_seconds > 0:
            shared_openai_request_gate().push_cooldown(wait_seconds)
        max_attempts_for_status = 0 if GROQ_REPORT_RETRY_FOREVER else GROQ_REPORT_MAX_RETRIES
        if on_retry is not None:
            on_retry(attempt, max_attempts_for_status, wait_seconds, last_error)
        error_text = (
            _format_http_error(last_error, "Groq")
            if isinstance(last_error, requests.HTTPError)
            else str(last_error)
        )
        print(
            f"⚠️ Groq request attempt {attempt}/"
            f"{'∞' if GROQ_REPORT_RETRY_FOREVER else GROQ_REPORT_MAX_RETRIES} failed: "
            f"{error_text}. {key_pool.label(key_index)} will rotate if another key is available. "
            f"Retrying in {wait_seconds:.1f}s."
        )
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    raise RuntimeError(f"Groq request failed after {GROQ_REPORT_MAX_RETRIES} attempts: {last_error}")


def _call_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    def _post(chat_payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            _get_ollama_chat_url(),
            headers={"Content-Type": "application/json"},
            json=chat_payload,
            timeout=300,
        )
        response.raise_for_status()
        return response.json()

    def _repair(raw_content: str, original_payload: Dict[str, Any]) -> Dict[str, Any]:
        repair_payload = {
            "model": original_payload["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Convert the provided content into one valid JSON object only. "
                        "Do not add markdown or commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        _build_ollama_json_only_instruction(
                            {
                                "json_schema": {
                                    "schema": original_payload["format"],
                                }
                            }
                        )
                        + "\n\nContent to convert:\n"
                        + raw_content
                    ),
                },
            ],
            "stream": False,
            "format": original_payload["format"],
            "options": {
                "temperature": 0,
                "num_predict": max(
                    int((original_payload.get("options") or {}).get("num_predict") or 2400),
                    2400,
                ),
                "num_ctx": max(
                    int((original_payload.get("options") or {}).get("num_ctx") or _get_ollama_num_ctx()),
                    8192,
                ),
            },
        }
        repair_data = _post(repair_payload)
        repair_content = ((repair_data.get("message") or {}).get("content") or "").strip()
        if not repair_content:
            raise ValueError("Ollama repair response returned empty content.")
        return _extract_json_object(repair_content, "ollama")

    last_error: Exception | None = None
    for attempt_index in range(3):
        request_payload = copy.deepcopy(payload)
        if attempt_index > 0 and request_payload.get("messages"):
            retry_message = (
                "Your previous response was empty or invalid. "
                "Return only one valid JSON object that matches the requested schema."
            )
            first_message = dict(request_payload["messages"][0])
            first_message["content"] = f"{first_message.get('content', '')} {retry_message}".strip()
            request_payload["messages"][0] = first_message

        try:
            data = _post(request_payload)
            message = data.get("message") or {}
            content = message.get("content")
            if not isinstance(content, str):
                raise ValueError("Ollama response did not contain a text JSON payload.")
            if not content.strip():
                raise ValueError("Ollama response returned empty content.")
            try:
                return _extract_json_object(content, "ollama")
            except ValueError:
                return _repair(content, request_payload)
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise ValueError("Ollama request failed for an unknown reason.")


def _call_llm(
    provider: str,
    payload: Dict[str, Any],
    api_key: Any | None = None,
    on_retry: Callable[[int, int, float, Exception], None] | None = None,
) -> Dict[str, Any]:
    if provider == "ollama":
        return _call_ollama(payload)
    if provider == "groq":
        if not api_key:
            raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not configured on the predict-service server.")
        return _call_groq(payload, api_key, on_retry=on_retry)
    if provider == "openai":
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured on the predict-service server.")
        return _call_openai(payload, api_key, on_retry=on_retry)
    raise RuntimeError(f"Unsupported LLM provider: {provider}")


def _build_llm_request_payload(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    response_schema: Dict[str, Any],
    *,
    max_completion_tokens: int,
    reasoning_effort: str = "low",
    verbosity: str = "low",
) -> Dict[str, Any]:
    if provider == "ollama":
        return {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": response_schema["json_schema"]["schema"],
            "options": {
                "temperature": 0,
                "num_predict": int(max_completion_tokens),
                "num_ctx": _get_ollama_num_ctx(),
            },
        }

    if provider == "groq":
        request_payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_completion_tokens": int(max_completion_tokens),
        }
        if str(model).startswith("openai/gpt-oss") and reasoning_effort in {"low", "medium", "high"}:
            request_payload["reasoning_effort"] = reasoning_effort
        return request_payload

    return {
        "model": model,
        "messages": messages,
        "response_format": response_schema,
        "reasoning_effort": reasoning_effort,
        "verbosity": verbosity,
        "max_completion_tokens": max_completion_tokens,
    }


def _truncate_for_prompt(value: Any, max_chars: int = 360) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _compact_overview_rows(
    rows: Any,
    *,
    limit: int,
    fields: Sequence[str],
) -> List[Dict[str, Any]]:
    compact_rows: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        return compact_rows
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        compact: Dict[str, Any] = {}
        for field in fields:
            value = row.get(field)
            if value in (None, "", [], {}):
                continue
            compact[field] = _truncate_for_prompt(value, 90) if isinstance(value, str) else value
        if not compact:
            for field, value in list(row.items())[:4]:
                if value not in (None, "", [], {}):
                    compact[str(field)] = _truncate_for_prompt(value, 90) if isinstance(value, str) else value
        if compact:
            compact_rows.append(compact)
    return compact_rows


def _compact_overview_payload(
    prompt_payload: Dict[str, Any],
    asset_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    report_context = dict(prompt_payload.get("report_context") or {})
    compact_context: Dict[str, Any] = {}
    for key in (
        "report_id",
        "best_model",
        "selected_sheet",
        "rows_after_preprocessing",
        "metrics",
        "top_features",
    ):
        value = report_context.get(key)
        if value not in (None, "", [], {}):
            compact_context[key] = value

    overview_tables = (
        (
            "model_comparison_table",
            5,
            ("model", "r2_score", "rmse", "mse", "mae"),
        ),
        (
            "gra_ranking",
            5,
            ("rank", "feature", "score", "grade", "value"),
        ),
        (
            "feature_importance_table",
            5,
            ("feature", "importance", "rank", "value"),
        ),
        (
            "shap_importance_table",
            5,
            ("feature", "mean_abs_shap", "importance", "rank", "value"),
        ),
        (
            "target_correlations",
            5,
            ("feature", "target", "correlation", "value"),
        ),
        (
            "incremental_feature_table",
            4,
            ("n_features", "feature_subset", "KNN_R2", "KNN_MSE", "SVM_R2", "RF_R2", "XGBoost_R2"),
        ),
    ):
        compact_rows = _compact_overview_rows(
            report_context.get(key),
            limit=limit,
            fields=fields,
        )
        if compact_rows:
            compact_context[key] = compact_rows

    if report_context.get("results_summary_excerpt"):
        compact_context["results_summary_excerpt"] = _truncate_for_prompt(
            report_context.get("results_summary_excerpt"),
            360,
        )
    if report_context.get("analysis_summary_excerpt"):
        compact_context["analysis_summary_excerpt"] = _truncate_for_prompt(
            report_context.get("analysis_summary_excerpt"),
            360,
        )

    evidence_lookup = {
        str(item.get("key") or ""): item
        for item in list(prompt_payload.get("asset_evidence") or [])
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    }
    compact_assets: List[Dict[str, Any]] = []
    for asset in list(prompt_payload.get("assets") or []):
        if not isinstance(asset, dict):
            continue
        key = str(asset.get("key") or "").strip()
        if not key:
            continue
        explanation = asset_map.get(key) or {}
        evidence = evidence_lookup.get(key) or {}
        benchmark_payload = explanation.get("benchmark_payload")
        generated = _truncate_for_prompt(
            explanation.get("en")
            or (
                benchmark_payload.get("explanation_short")
                if isinstance(benchmark_payload, dict)
                else ""
            )
            or evidence.get("result_text"),
            140,
        )
        if generated:
            compact_assets.append(
                {
                    "key": key,
                    "title": _truncate_for_prompt(asset.get("title") or evidence.get("title") or key, 80),
                    "summary": generated,
                }
            )

    priority_assets = {
        "metrics_overview",
        "model_comparison_table",
        "fig5_model_comparison",
        "feature_importance",
        "feature_importance_table",
        "fig3a_gra_ranking",
        "gra_ranking",
        "fig3b_shap_analysis",
        "predicted_vs_actual",
        "residuals",
        "time_series",
    }
    compact_assets.sort(
        key=lambda item: (
            0 if str(item.get("key") or "") in priority_assets else 1,
            str(item.get("key") or ""),
        )
    )
    compact_assets = compact_assets[:10]

    return {
        "task": "Write one compact whole-report overview for a non-technical reader.",
        "audience": prompt_payload.get("audience"),
        "languages": prompt_payload.get("languages"),
        "report_context": _json_safe_value(compact_context),
        "asset_summaries": _json_safe_value(compact_assets),
        "style_rules": [
            "Write one cohesive overview in each language.",
            "Use exactly 2 short paragraphs in each language, returned as one string with one newline between paragraphs.",
            "Paragraph 1 summarizes dataset scope, winning model, and model-comparison metrics.",
            "Paragraph 2 summarizes feature story and the most important caution.",
            "Synthesize the report; do not list every chart.",
            "Use concrete numbers, model names, feature names, ranks, and metrics only when supplied.",
            "Do not use bullet lists.",
        ],
    }


def _generate_global_overview(
    prompt_payload: Dict[str, Any],
    asset_map: Dict[str, Dict[str, Any]],
    provider: str,
    model: str,
    api_key: Any | None = None,
    on_retry: Callable[[int, int, float, Exception], None] | None = None,
) -> Dict[str, str]:
    overview_payload = _compact_overview_payload(prompt_payload, asset_map)

    response_schema = _build_overview_response_schema()
    messages = [
        {
                "role": "system",
                "content": (
                    _build_ollama_json_only_instruction(response_schema)
                    if _needs_inline_json_schema_instruction(provider, model)
                    else (
                        "You are a bilingual machine-learning report summarizer for non-technical users. "
                        "Return strict JSON only."
                )
            ),
        },
        {
            "role": "user",
            "content": json.dumps(overview_payload, ensure_ascii=False),
        },
    ]
    request_payload = _build_llm_request_payload(
        provider=provider,
        model=model,
        messages=messages,
        response_schema=response_schema,
        max_completion_tokens=(
            2800
            if provider == "ollama"
            else GROQ_REPORT_OVERVIEW_MAX_COMPLETION_TOKENS
            if provider == "groq"
            else OPENAI_REPORT_OVERVIEW_MAX_COMPLETION_TOKENS
        ),
        reasoning_effort="low",
        verbosity="medium",
    )

    parsed = _call_llm(provider, request_payload, api_key=api_key, on_retry=on_retry)
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


def update_report_explanation_status(
    report_info: Dict[str, Any],
    status: str,
    message: str = "",
    report_root: str | Path | None = None,
    started_at: str | None = None,
    progress: float | None = None,
    phase: str | None = None,
    step_index: int | None = None,
    total_steps: int | None = None,
    current_items: List[str] | None = None,
    retry_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    report_id = str(report_info.get("report_id") or "").strip()
    if not report_id:
        return {}

    report_dir = Path(report_root or Path(__file__).resolve().parents[1] / "reports") / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "summary.json"

    payload: Dict[str, Any] = {
        "status": str(status).strip() or "pending",
        "message": str(message or "").strip(),
        "updated_at": datetime.now().isoformat(),
    }

    existing = {}
    if summary_path.exists():
        summary = _read_json(summary_path)
        existing = dict(summary.get("llm_explanations_status") or {})
        payload["started_at"] = started_at or existing.get("started_at") or payload["updated_at"]

        optional_fields = {
            "progress": max(0.0, min(100.0, round(float(progress), 1))) if progress is not None else existing.get("progress"),
            "phase": str(phase).strip() if phase is not None else existing.get("phase"),
            "step_index": int(step_index) if step_index is not None else existing.get("step_index"),
            "total_steps": int(total_steps) if total_steps is not None else existing.get("total_steps"),
            "current_items": list(current_items) if current_items is not None else existing.get("current_items"),
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value
        if retry_payload:
            payload["retry"] = retry_payload
        summary["llm_explanations_status"] = payload
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        payload["started_at"] = started_at or payload["updated_at"]
        if progress is not None:
            payload["progress"] = max(0.0, min(100.0, round(float(progress), 1)))
        if phase is not None:
            payload["phase"] = str(phase).strip()
        if step_index is not None:
            payload["step_index"] = int(step_index)
        if total_steps is not None:
            payload["total_steps"] = int(total_steps)
        if current_items is not None:
            payload["current_items"] = list(current_items)
        if retry_payload:
            payload["retry"] = retry_payload

    report_info["llm_explanations_status"] = payload
    return payload


def generate_report_explanations(
    report_info: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    runtime: Dict[str, Any] | None = None,
    report_root: str | Path | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    groq_api_keys: Any | None = None,
) -> Dict[str, Any] | None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
    provider = _get_llm_provider(llm_provider)
    provider_label = _provider_display_name(provider)
    model = _get_report_model(provider, llm_model)
    api_key: Any | None = None
    if provider == "openai":
        api_key = _get_openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured on the predict-service server.")
    elif provider == "groq":
        api_key = _get_groq_api_keys(groq_api_keys)
        if not api_key:
            raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not configured on the predict-service server.")

    report_id = str(report_info.get("report_id") or "").strip()
    if not report_id:
        raise RuntimeError("Training report metadata is missing report_id.")

    report_dir = Path(report_root or Path(__file__).resolve().parents[1] / "reports") / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    prompt_payload = _build_prompt_payload(
        report_dir=report_dir,
        report_info=report_info,
        pipeline_result=pipeline_result,
        runtime=runtime,
    )
    all_assets = list(prompt_payload["assets"])
    asset_batches = _chunk_assets(
        all_assets,
        1 if provider in {"ollama", "groq"} else OPENAI_REPORT_ASSET_BATCH_SIZE,
    )
    total_steps = len(asset_batches) + 3
    update_report_explanation_status(
        report_info=report_info,
        status="pending",
        message=(
            f"Prepared {len(all_assets)} charts/tables for AI explanation "
            f"with {provider_label} ({model})."
        ),
        report_root=report_root,
        progress=10,
        phase="preparing",
        step_index=1,
        total_steps=total_steps,
        current_items=[str(item.get("title") or item.get("key") or "") for item in all_assets[:2]],
    )
    overview = {"en": "", "zh_TW": ""}
    asset_map: Dict[str, Dict[str, Any]] = {}

    asset_evidence_lookup = {
        str(item.get("key") or ""): item
        for item in prompt_payload.get("asset_evidence", [])
        if str(item.get("key") or "").strip()
    }

    for batch_index, asset_batch in enumerate(asset_batches):
        batch_keys = [item["key"] for item in asset_batch]
        batch_payload = dict(prompt_payload)
        batch_payload["assets"] = asset_batch
        batch_payload["asset_evidence"] = [
            asset_evidence_lookup[key]
            for key in batch_keys
            if key in asset_evidence_lookup
        ]
        batch_payload["report_context"] = _asset_scoped_report_context(
            dict(prompt_payload.get("report_context") or {})
        )
        batch_payload["style_rules"] = list(prompt_payload["style_rules"]) + [
            "For each chart or table, write exactly 2 short sentences in each language.",
            "The English en field must be at most 55 words total.",
            "The zh_TW field must be at most 120 Traditional Chinese characters total.",
            "For the overview, write about 3-4 sentences in each language.",
            "Do not use bullets. Write complete, readable prose.",
            "Use the per-asset result_text as the authoritative textual summary for that chart or table.",
            "For each asset, also return benchmark_payload.explanation_short as a one-sentence English summary with at most 22 words.",
            "For each asset, return benchmark_payload.explanation_full as exactly the same English text you returned in en.",
            "For this report explanation step, set benchmark_payload.claims to an empty array.",
            "Do not include claim objects here; the benchmark phase extracts and validates claims separately.",
            f"Use only these benchmark claim_type values: {', '.join(CANONICAL_CLAIM_TYPES)}.",
            "Unsupported or weakly grounded claims must be omitted rather than guessed.",
        ]

        response_format = _build_response_schema(batch_keys, include_overview=False)
        messages = [
            {
                "role": "system",
                "content": (
                    _build_ollama_json_only_instruction(response_format, allowed_keys=batch_keys)
                    if _needs_inline_json_schema_instruction(provider, model)
                    else (
                        "You are a bilingual machine-learning report explainer for non-technical users. "
                        "Return strict JSON only."
                    )
                ),
            },
            {
                "role": "user",
                "content": json.dumps(batch_payload, ensure_ascii=False),
            },
        ]
        request_payload = _build_llm_request_payload(
            provider=provider,
            model=model,
            messages=messages,
            response_schema=response_format,
            max_completion_tokens=(
                GROQ_REPORT_ASSET_MAX_COMPLETION_TOKENS
                if provider == "groq"
                else OPENAI_REPORT_ASSET_MAX_COMPLETION_TOKENS
            ),
            reasoning_effort="low",
            verbosity="low",
        )

        current_titles = [str(item.get("title") or item.get("key") or "") for item in asset_batch]
        batch_start_progress = 25 + ((batch_index / max(1, len(asset_batches))) * 65)
        batch_end_progress = 25 + (((batch_index + 1) / max(1, len(asset_batches))) * 65)
        update_report_explanation_status(
            report_info=report_info,
            status="pending",
            message=f"Generating explanations for batch {batch_index + 1}/{len(asset_batches)}.",
            report_root=report_root,
            progress=batch_start_progress,
            phase="assets",
            step_index=batch_index + 2,
            total_steps=total_steps,
            current_items=current_titles,
        )

        try:
            parsed = _call_llm(
                provider,
                request_payload,
                api_key,
                on_retry=(
	                    lambda attempt, max_attempts, wait_seconds, error, batch_index=batch_index, current_titles=current_titles, batch_start_progress=batch_start_progress: update_report_explanation_status(
	                        report_info=report_info,
	                        status="pending",
	                        message=_format_retry_status_message(
	                            f"generating explanations for batch {batch_index + 1}/{len(asset_batches)}",
	                            attempt,
	                            max_attempts,
	                            wait_seconds,
	                            error,
	                            provider_label,
	                        ),
	                        report_root=report_root,
	                        progress=batch_start_progress,
	                        phase="assets",
	                        step_index=batch_index + 2,
	                        total_steps=total_steps,
                        current_items=current_titles,
                        retry_payload=_build_retry_payload(
	                            f"batch {batch_index + 1}/{len(asset_batches)}",
	                            attempt,
	                            max_attempts,
	                            wait_seconds,
	                            error,
	                            provider_label,
	                        ),
	                    )
	                    if provider in {"openai", "groq"}
	                    else None
	                ),
	            )
        except Exception as exc:
            raise RuntimeError(
                f"{provider_label} explanation generation failed on batch {batch_index + 1}: {exc}"
            ) from exc

        for item in parsed.get("assets", []):
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            asset_map[key] = _normalize_asset_explanation_item(item)

        update_report_explanation_status(
            report_info=report_info,
            status="pending",
            message=f"Completed batch {batch_index + 1}/{len(asset_batches)}.",
            report_root=report_root,
            progress=batch_end_progress,
            phase="assets",
            step_index=batch_index + 2,
            total_steps=total_steps,
            current_items=current_titles,
        )

    try:
        update_report_explanation_status(
            report_info=report_info,
            status="pending",
            message=f"Generating the overall AI overview with {provider_label}.",
            report_root=report_root,
            progress=90,
            phase="overview",
            step_index=len(asset_batches) + 2,
            total_steps=total_steps,
            current_items=["AI Report Overview"],
        )
        overview = _generate_global_overview(
            prompt_payload,
            asset_map=asset_map,
            provider=provider,
            model=model,
            api_key=api_key,
            on_retry=(
                lambda attempt, max_attempts, wait_seconds, error: update_report_explanation_status(
                    report_info=report_info,
                    status="pending",
	                    message=_format_retry_status_message(
	                        "generating the overall AI overview",
	                        attempt,
	                        max_attempts,
	                        wait_seconds,
	                        error,
	                        provider_label,
	                    ),
                    report_root=report_root,
                    progress=90,
                    phase="overview",
                    step_index=len(asset_batches) + 2,
                    total_steps=total_steps,
                    current_items=["AI Report Overview"],
                    retry_payload=_build_retry_payload(
	                        "overall overview",
	                        attempt,
	                        max_attempts,
	                        wait_seconds,
	                        error,
	                        provider_label,
	                    ),
	                )
	                if provider in {"openai", "groq"}
	                else None
	            ),
	        )
    except Exception as exc:
        print(f"⚠️ {provider_label} global overview generation failed: {exc}")

    explanation_payload = {
        "provider": provider,
        "model": model,
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
        update_report_explanation_status(
            report_info=report_info,
            status="pending",
            message="Saving explanation output to the report.",
            report_root=report_root,
            progress=95,
            phase="finalizing",
            step_index=total_steps,
            total_steps=total_steps,
        )
        _update_summary_file(summary_path, explanation_payload)
        update_report_explanation_status(
            report_info=report_info,
            status="success",
            message="AI explanations generated successfully.",
            report_root=report_root,
            progress=100,
            phase="completed",
            step_index=total_steps,
            total_steps=total_steps,
        )

    files = dict(report_info.get("files") or {})
    files["llm_explanations"] = EXPLANATIONS_FILENAME
    report_info["files"] = files
    report_info["llm_explanations"] = explanation_payload

    return explanation_payload
