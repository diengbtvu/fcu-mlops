"""
Training report generator for Hydrogen Production demo.

The report artifacts mirror the style of `/fcu/Hydrogen-Prediction/comparison_results`
so each training run can output publication-style figures/tables.
"""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import matplotlib

# Headless backend for server/container environments.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

try:
    from xgboost import XGBRegressor

    XGBOOST_AVAILABLE = True
except Exception:
    XGBOOST_AVAILABLE = False


TARGET_COLUMN_NAME = "HPR"


def sanitize_report_id(model_name: str) -> str:
    """Convert model name to a filesystem-safe report id."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(model_name)).strip("_")
    if not cleaned:
        cleaned = f"model_{int(datetime.now().timestamp())}"
    return cleaned[:180]


def _as_1d(values: Any) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim > 1:
        arr = arr.reshape(-1)
    return arr


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    return {
        "r2_score": _safe_float(r2_score(y_true, y_pred)),
        "rmse": _safe_float(np.sqrt(mse)),
        "mse": _safe_float(mse),
        "mae": _safe_float(mean_absolute_error(y_true, y_pred)),
    }


def _save_figure(fig: plt.Figure, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _build_reports_dir() -> str:
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    reports_root = os.path.join(project_root, "app", "reports")
    os.makedirs(reports_root, exist_ok=True)
    return reports_root


def _selected_model_label(model_type: str) -> str:
    mapping = {
        "svm": "SVM",
        "decision_tree": "DT",
        "dt": "DT",
        "random_forest": "RF",
        "knn": "KNN",
        "xgboost": "XGBoost",
    }
    return mapping.get(str(model_type).lower(), str(model_type).upper())


def _benchmark_models(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> Tuple[List[Dict[str, Any]], Dict[str, np.ndarray], Dict[str, Any]]:
    """Train/evaluate 5 paper models on the same split for report comparison."""
    models: Dict[str, Any] = {
        "SVM": SVR(kernel="rbf", C=1.0, gamma="scale"),
        "DT": DecisionTreeRegressor(random_state=42),
        "RF": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        "KNN": KNeighborsRegressor(n_neighbors=5),
    }
    if XGBOOST_AVAILABLE:
        models["XGBoost"] = XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42,
            verbosity=0,
        )

    rows: List[Dict[str, Any]] = []
    predictions: Dict[str, np.ndarray] = {}
    fitted_models: Dict[str, Any] = {}
    y_true = _as_1d(y_test)

    for name, estimator in models.items():
        try:
            estimator.fit(X_train, y_train)
            pred = _as_1d(estimator.predict(X_test))
            metric = _compute_metrics(y_true, pred)
            rows.append({"model": name, **metric})
            predictions[name] = pred
            fitted_models[name] = estimator
        except Exception as exc:
            rows.append(
                {
                    "model": name,
                    "r2_score": None,
                    "rmse": None,
                    "mse": None,
                    "mae": None,
                    "error": str(exc),
                }
            )

    return rows, predictions, fitted_models


def _plot_predicted_vs_actual(
    predictions: Dict[str, np.ndarray], y_true: np.ndarray, save_path: str
) -> bool:
    if not predictions:
        return False

    names = list(predictions.keys())
    n_cols = 3
    n_rows = int(math.ceil(len(names) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    axes = np.array(axes).reshape(-1)

    valid = 0
    for idx, name in enumerate(names):
        ax = axes[idx]
        pred = _as_1d(predictions[name])
        if pred.size != y_true.size:
            ax.set_visible(False)
            continue

        min_val = float(min(np.min(y_true), np.min(pred)))
        max_val = float(max(np.max(y_true), np.max(pred)))
        ax.scatter(y_true, pred, alpha=0.75, s=24, edgecolors="none", color="#1f77b4")
        ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=1.5)

        if len(y_true) > 1:
            z = np.polyfit(y_true, pred, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min_val, max_val, 200)
            ax.plot(x_line, p(x_line), "g-", linewidth=1.3, alpha=0.8)

        metric = _compute_metrics(y_true, pred)
        ax.set_title(f"{name} | R2={metric['r2_score']:.3f}")
        ax.set_xlabel("Actual HPR (scaled)")
        ax.set_ylabel("Predicted HPR (scaled)")
        valid += 1

    for idx in range(len(names), len(axes)):
        axes[idx].set_visible(False)

    if valid == 0:
        plt.close(fig)
        return False

    title_suffix = "All Models" if len(names) > 1 else "Selected Model"
    fig.suptitle(f"Predicted vs Actual ({title_suffix})", fontsize=14, y=1.01)
    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _plot_residuals(
    predictions: Dict[str, np.ndarray], y_true: np.ndarray, save_path: str
) -> bool:
    if not predictions:
        return False

    names = list(predictions.keys())
    n_cols = 3
    n_rows = int(math.ceil(len(names) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    axes = np.array(axes).reshape(-1)

    valid = 0
    for idx, name in enumerate(names):
        ax = axes[idx]
        pred = _as_1d(predictions[name])
        if pred.size != y_true.size:
            ax.set_visible(False)
            continue

        residuals = y_true - pred
        ax.scatter(pred, residuals, alpha=0.7, s=24, edgecolors="none", color="#E15759")
        ax.axhline(0.0, color="black", linestyle="--", linewidth=1.2)
        ax.set_title(f"{name} Residuals")
        ax.set_xlabel("Predicted HPR (scaled)")
        ax.set_ylabel("Residual (actual - predicted)")
        valid += 1

    for idx in range(len(names), len(axes)):
        axes[idx].set_visible(False)

    if valid == 0:
        plt.close(fig)
        return False

    title_suffix = "All Models" if len(names) > 1 else "Selected Model"
    fig.suptitle(f"Residual Analysis ({title_suffix})", fontsize=14, y=1.01)
    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _plot_correlation_heatmap(corr_matrix: pd.DataFrame, save_path: str) -> bool:
    if corr_matrix.empty:
        return False

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(corr_matrix.values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    ax.set_xticks(np.arange(len(corr_matrix.columns)))
    ax.set_yticks(np.arange(len(corr_matrix.index)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr_matrix.index)
    ax.set_title("Feature Correlation Heatmap")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _plot_feature_distributions(df: pd.DataFrame, features: List[str], save_path: str) -> bool:
    if len(features) == 0:
        return False

    n_cols = 4
    n_rows = int(math.ceil(len(features) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3.8 * n_rows))
    axes = np.array(axes).reshape(-1)

    for idx, feature in enumerate(features):
        ax = axes[idx]
        ax.hist(df[feature].dropna().values, bins=24, color="#4E79A7", alpha=0.85)
        ax.set_title(feature)
        ax.set_xlabel("Value")
        ax.set_ylabel("Count")

    for idx in range(len(features), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle("Feature Distributions", fontsize=14, y=1.01)
    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _plot_feature_vs_target(
    df: pd.DataFrame, features: List[str], target: str, save_path: str
) -> bool:
    if len(features) == 0 or target not in df.columns:
        return False

    n_cols = 4
    n_rows = int(math.ceil(len(features) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3.8 * n_rows))
    axes = np.array(axes).reshape(-1)

    y = df[target].values
    for idx, feature in enumerate(features):
        ax = axes[idx]
        x = df[feature].values
        ax.scatter(x, y, alpha=0.65, s=20, edgecolors="none", color="#76B7B2")
        if len(x) > 1:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(np.nanmin(x), np.nanmax(x), 200)
            ax.plot(x_line, p(x_line), "r--", linewidth=1.3)
        ax.set_title(f"{feature} vs {target}")
        ax.set_xlabel(feature)
        ax.set_ylabel(target)

    for idx in range(len(features), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle("Feature vs Target Relationships", fontsize=14, y=1.01)
    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _plot_boxplots(df: pd.DataFrame, features: List[str], save_path: str) -> bool:
    if len(features) == 0:
        return False

    fig, ax = plt.subplots(figsize=(14, 8))
    df[features].boxplot(ax=ax, grid=True, notch=False, rot=40)
    ax.set_title("Feature Boxplots")
    ax.set_ylabel("Scaled Value")
    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _plot_time_series(
    df: pd.DataFrame, features: List[str], target: str, save_path: str
) -> bool:
    if target not in df.columns:
        return False

    x = np.arange(len(df))
    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)

    axes[0].plot(x, df[target].values, "b-", linewidth=1.5, label=target)
    axes[0].set_title("Target Over Samples")
    axes[0].set_ylabel(target)
    axes[0].legend(loc="best")

    top_features = features[:3]
    if top_features:
        for feat in top_features:
            axes[1].plot(x, df[feat].values, linewidth=1.3, label=feat)
        axes[1].set_title("Top Features Over Samples")
        axes[1].set_ylabel("Scaled Value")
        axes[1].legend(loc="best")

    if "pH" in df.columns:
        axes[2].plot(x, df["pH"].values, "g-", linewidth=1.4, label="pH")
    if "VSS" in df.columns:
        axes[2].plot(x, df["VSS"].values, "r-", linewidth=1.4, label="VSS")
    axes[2].set_title("pH / VSS Trends")
    axes[2].set_xlabel("Sample Index")
    axes[2].set_ylabel("Scaled Value")
    if axes[2].lines:
        axes[2].legend(loc="best")

    fig.tight_layout()
    _save_figure(fig, save_path)
    return True


def _build_analysis_summary(
    stats_df: pd.DataFrame,
    corr_matrix: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    selected_metrics: Dict[str, Any],
    feature_names: List[str],
) -> str:
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("HYDROGEN PRODUCTION PREDICTION - ANALYSIS SUMMARY REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append("1. DATASET OVERVIEW")
    lines.append("-" * 50)
    total_samples = int(stats_df.loc[TARGET_COLUMN_NAME, "count"]) if TARGET_COLUMN_NAME in stats_df.index else 0
    lines.append(f"Total samples: {total_samples}")
    lines.append(f"Number of features: {len(feature_names)}")
    lines.append(f"Target variable: {TARGET_COLUMN_NAME}")
    lines.append("")
    lines.append("2. SELECTED MODEL METRICS")
    lines.append("-" * 50)
    lines.append(
        f"R2={_safe_float(selected_metrics.get('r2_score')):.5f}, "
        f"RMSE={_safe_float(selected_metrics.get('rmse')):.5f}, "
        f"MSE={_safe_float(selected_metrics.get('mse')):.6f}, "
        f"MAE={_safe_float(selected_metrics.get('mae')):.5f}"
    )
    lines.append("")
    lines.append("3. TOP CORRELATED FEATURES WITH HPR")
    lines.append("-" * 50)
    if TARGET_COLUMN_NAME in corr_matrix.columns:
        top_corr = corr_matrix[TARGET_COLUMN_NAME].drop(TARGET_COLUMN_NAME, errors="ignore")
        top_corr = top_corr.sort_values(ascending=False).head(5)
        for feat, score in top_corr.items():
            lines.append(f"{feat}: {float(score):.4f}")
    else:
        lines.append("No correlation matrix available.")
    lines.append("")
    lines.append("4. MODEL PERFORMANCE COMPARISON")
    lines.append("-" * 50)
    if benchmark_df.empty:
        lines.append("No benchmark model results available.")
    else:
        lines.append(benchmark_df.to_string(index=False))
    lines.append("")
    lines.append("5. BEST BENCHMARK MODEL")
    lines.append("-" * 50)
    if not benchmark_df.empty and "r2_score" in benchmark_df.columns:
        tmp = benchmark_df.dropna(subset=["r2_score"])
        if not tmp.empty:
            best = tmp.sort_values("r2_score", ascending=False).iloc[0]
            lines.append(f"Model: {best['model']}")
            lines.append(f"R2: {_safe_float(best['r2_score']):.5f}")
            lines.append(f"MSE: {_safe_float(best['mse']):.6f}")
        else:
            lines.append("No valid benchmark metrics available.")
    else:
        lines.append("No valid benchmark metrics available.")
    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)
    return "\n".join(lines)


def generate_training_report(
    model_name: str,
    model_type: str,
    trained_model: Any,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    selected_metrics: Dict[str, Any],
    gra_ranking: List[Dict[str, Any]] | None = None,
    include_comparison: bool = True,
) -> Dict[str, Any]:
    """Generate report artifacts and return metadata for API response."""
    report_id = sanitize_report_id(model_name)
    reports_root = _build_reports_dir()
    report_dir = os.path.join(reports_root, report_id)
    os.makedirs(report_dir, exist_ok=True)

    feature_names = (
        list(X_test.columns)
        if hasattr(X_test, "columns")
        else [f"feature_{i}" for i in range(np.asarray(X_test).shape[1])]
    )

    y_true = _as_1d(y_test)
    y_pred = _as_1d(trained_model.predict(X_test))
    selected_label = _selected_model_label(model_type)

    files: Dict[str, str] = {}

    benchmark_rows: List[Dict[str, Any]] = []
    benchmark_predictions: Dict[str, np.ndarray] = {selected_label: y_pred}
    benchmark_models: Dict[str, Any] = {}

    if include_comparison:
        benchmark_rows, benchmark_predictions, benchmark_models = _benchmark_models(
            X_train, X_test, y_train, y_test
        )

        # Keep benchmark table aligned with the actually selected trained model metrics.
        selected_row = {
            "model": selected_label,
            "r2_score": _safe_float(selected_metrics.get("r2_score")),
            "rmse": _safe_float(selected_metrics.get("rmse")),
            "mse": _safe_float(selected_metrics.get("mse")),
            "mae": _safe_float(selected_metrics.get("mae")),
        }
        replaced = False
        for idx, row in enumerate(benchmark_rows):
            if row.get("model") == selected_label:
                benchmark_rows[idx] = selected_row
                replaced = True
                break
        if not replaced:
            benchmark_rows.append(selected_row)
        benchmark_predictions[selected_label] = y_pred

    benchmark_df = pd.DataFrame(benchmark_rows)

    # ------------------------------------------------------------------
    # Paper-style output tables
    # ------------------------------------------------------------------
    if include_comparison and not benchmark_df.empty:
        model_cmp_name = "table_model_comparison.csv"
        benchmark_df.to_csv(os.path.join(report_dir, model_cmp_name), index=False)
        files["model_comparison_table"] = model_cmp_name

    # Selected-model feature importance table (if available)
    importance_df = pd.DataFrame(columns=["feature", "importance"])
    try:
        model_for_importance = trained_model
        if include_comparison and not hasattr(model_for_importance, "feature_importances_"):
            model_for_importance = benchmark_models.get("RF")

        if model_for_importance is not None and hasattr(model_for_importance, "feature_importances_"):
            importances = _as_1d(getattr(model_for_importance, "feature_importances_"))
            if len(importances) == len(feature_names):
                importance_df = (
                    pd.DataFrame(
                        {"feature": feature_names, "importance": [float(v) for v in importances]}
                    )
                    .sort_values("importance", ascending=False)
                    .reset_index(drop=True)
                )
    except Exception:
        importance_df = pd.DataFrame(columns=["feature", "importance"])

    if not importance_df.empty:
        fi_table_name = "table_feature_importance.csv"
        importance_df.to_csv(os.path.join(report_dir, fi_table_name), index=False)
        files["feature_importance_table"] = fi_table_name

    # ------------------------------------------------------------------
    # Paper-style model figures
    # ------------------------------------------------------------------
    if include_comparison:
        try:
            ok_df = benchmark_df.dropna(subset=["r2_score", "rmse", "mse", "mae"], how="any")
            if not ok_df.empty:
                metric_configs = [
                    ("r2_score", "R2 Comparison", "#76B7B2"),
                    ("rmse", "RMSE Comparison", "#E15759"),
                    ("mse", "MSE Comparison", "#F28E2B"),
                    ("mae", "MAE Comparison", "#59A14F"),
                ]
                fig, axes = plt.subplots(2, 2, figsize=(14, 10))
                axes = np.array(axes).reshape(-1)
                for idx, (metric, title, color) in enumerate(metric_configs):
                    ax = axes[idx]
                    ax.bar(ok_df["model"], ok_df[metric], color=color)
                    ax.set_title(title)
                    ax.set_ylabel(metric.upper())
                    ax.tick_params(axis="x", rotation=25)
                    if metric == "r2_score":
                        ymax = max(1.0, float(ok_df[metric].max()) * 1.1)
                        ax.set_ylim(0, ymax)
                fig.tight_layout()
                cmp_name = "fig_model_comparison_bars.png"
                _save_figure(fig, os.path.join(report_dir, cmp_name))
                files["model_comparison_bars"] = cmp_name
        except Exception:
            pass

    try:
        pva_name = "fig_predicted_vs_actual.png"
        if _plot_predicted_vs_actual(
            benchmark_predictions, y_true, os.path.join(report_dir, pva_name)
        ):
            files["predicted_vs_actual"] = pva_name
    except Exception:
        pass

    try:
        residual_name = "fig_residuals.png"
        if _plot_residuals(benchmark_predictions, y_true, os.path.join(report_dir, residual_name)):
            files["residuals"] = residual_name
    except Exception:
        pass

    try:
        if not importance_df.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            top_df = importance_df.head(12).iloc[::-1]
            ax.barh(top_df["feature"], top_df["importance"], color="#59A14F")
            ax.set_title("Feature Importance")
            ax.set_xlabel("Importance")
            fi_name = "fig_feature_importance.png"
            _save_figure(fig, os.path.join(report_dir, fi_name))
            files["feature_importance"] = fi_name
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Dataset analysis outputs (similar to Hydrogen-Prediction/comparison_results)
    # ------------------------------------------------------------------
    stats_df = pd.DataFrame()
    corr_matrix = pd.DataFrame()

    try:
        X_all = pd.concat([X_train, X_test], axis=0).sort_index()
        y_all = pd.concat([y_train, y_test], axis=0).sort_index()
        full_df = X_all.copy()
        full_df[TARGET_COLUMN_NAME] = y_all.reindex(X_all.index).values
        full_df = full_df.dropna()

        stats_df = full_df.describe().transpose()
        stats_name = "table_descriptive_statistics.csv"
        stats_df.to_csv(os.path.join(report_dir, stats_name))
        files["descriptive_statistics"] = stats_name

        corr_matrix = full_df.corr(numeric_only=True)
        corr_name = "table_correlation_matrix.csv"
        corr_matrix.to_csv(os.path.join(report_dir, corr_name))
        files["correlation_matrix"] = corr_name

        heatmap_name = "fig_correlation_heatmap.png"
        if _plot_correlation_heatmap(corr_matrix, os.path.join(report_dir, heatmap_name)):
            files["correlation_heatmap"] = heatmap_name

        dist_name = "fig_feature_distributions.png"
        if _plot_feature_distributions(full_df, feature_names, os.path.join(report_dir, dist_name)):
            files["feature_distributions"] = dist_name

        rel_name = "fig_feature_vs_target.png"
        if _plot_feature_vs_target(
            full_df, feature_names, TARGET_COLUMN_NAME, os.path.join(report_dir, rel_name)
        ):
            files["feature_vs_target"] = rel_name

        box_name = "fig_boxplots.png"
        if _plot_boxplots(full_df, feature_names, os.path.join(report_dir, box_name)):
            files["boxplots"] = box_name

        ts_name = "fig_time_series.png"
        if _plot_time_series(full_df, feature_names, TARGET_COLUMN_NAME, os.path.join(report_dir, ts_name)):
            files["time_series"] = ts_name
    except Exception:
        pass

    # GRA ranking chart (if provided)
    if isinstance(gra_ranking, list) and len(gra_ranking) > 0:
        try:
            rank_labels = [str(item.get("feature", "")) for item in gra_ranking]
            rank_scores = [_safe_float(item.get("score")) for item in gra_ranking]
            fig, ax = plt.subplots(figsize=(9, 6))
            ax.barh(rank_labels[::-1], rank_scores[::-1], color="#F28E2B")
            ax.set_title("GRA Feature Ranking")
            ax.set_xlabel("Grey Relation Degree")
            gra_name = "fig_gra_ranking.png"
            _save_figure(fig, os.path.join(report_dir, gra_name))
            files["gra_ranking"] = gra_name
        except Exception:
            pass

    # Text summary report
    try:
        summary_text = _build_analysis_summary(
            stats_df=stats_df,
            corr_matrix=corr_matrix,
            benchmark_df=benchmark_df,
            selected_metrics=selected_metrics,
            feature_names=feature_names,
        )
        summary_text_name = "analysis_summary_report.txt"
        with open(os.path.join(report_dir, summary_text_name), "w", encoding="utf-8") as f:
            f.write(summary_text)
        files["analysis_summary"] = summary_text_name
    except Exception:
        pass

    # JSON summary metadata
    summary = {
        "model_name": model_name,
        "model_type": model_type,
        "model_label": selected_label,
        "comparison_enabled": bool(include_comparison),
        "created_at": datetime.now().isoformat(),
        "selected_model_metrics": {
            "r2_score": _safe_float(selected_metrics.get("r2_score")),
            "rmse": _safe_float(selected_metrics.get("rmse")),
            "mse": _safe_float(selected_metrics.get("mse")),
            "mae": _safe_float(selected_metrics.get("mae")),
        },
        "feature_names": feature_names,
        "benchmark_models": benchmark_rows,
        "files": files,
    }

    summary_name = "summary.json"
    with open(os.path.join(report_dir, summary_name), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    files["summary"] = summary_name

    return {
        "report_id": report_id,
        "route_prefix": f"/train/reports/{report_id}",
        "files": files,
        "generated_at": datetime.now().isoformat(),
    }
