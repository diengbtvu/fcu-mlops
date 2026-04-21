from __future__ import annotations

import json
import os
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from openai_rate_control import shared_openai_request_gate
from .prompts import ARM_INSTRUCTIONS, build_generation_prompt, build_prompt_context, extract_prompt_context
from .schemas import ArtifactInputs

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_BENCHMARK_MODEL = os.getenv("OPENAI_BENCHMARK_MODEL", os.getenv("OPENAI_REPORT_MODEL", "gpt-5.2"))
OPENAI_BENCHMARK_MAX_RETRIES = max(1, int(os.getenv("OPENAI_BENCHMARK_MAX_RETRIES", "8")))
OPENAI_BENCHMARK_RETRY_BACKOFF_SECONDS = max(
    1.0,
    float(os.getenv("OPENAI_BENCHMARK_RETRY_BACKOFF_SECONDS", "8")),
)
OPENAI_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0,
    float(os.getenv("OPENAI_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS", "6")),
)
OPENAI_BENCHMARK_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("OPENAI_BENCHMARK_RETRY_JITTER_SECONDS", "1.0")),
)
OPENAI_BENCHMARK_TIMEOUT_SECONDS = max(60, int(os.getenv("OPENAI_BENCHMARK_TIMEOUT_SECONDS", "240")))


def _as_float(value: Any) -> float:
    return float(str(value).strip())


def _round_number(value: float) -> float:
    return round(value, 6)


class BaseLLMClient(ABC):
    name = "base"
    model_name: str | None = None

    @abstractmethod
    def generate_json(self, prompt: str) -> dict[str, Any]:
        """Return a JSON-like dictionary for the benchmark prompt."""

    def generate_artifact(
        self,
        inputs: ArtifactInputs,
        arms: list[str],
        conditions: list[str],
    ) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []
        for arm in arms:
            for condition in conditions:
                prompt = build_generation_prompt(inputs=inputs, arm=arm, condition=condition)
                outputs.append(self.generate_json(prompt))
        return outputs

    def metadata(self) -> dict[str, Any]:
        return {
            "client": self.name,
            "model": self.model_name,
        }


class FixtureLLMClient(BaseLLMClient):
    """Deterministic local client for tests and smoke runs."""

    name = "fixture"

    def generate_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        if context.get("chart_asset"):
            return self._chart_output(context)
        artifact_type = str(context["artifact_type"])
        if artifact_type == "model_comparison/main":
            return self._model_comparison_output(context)
        if artifact_type == "incremental_feature_analysis/main":
            return self._incremental_output(context)
        if artifact_type == "feature_ranking/gra":
            return self._ranking_output(context)
        raise ValueError(f"Unsupported artifact type for fixture client: {artifact_type}")

    def _chart_output(self, context: dict[str, Any]) -> dict[str, Any]:
        chart_asset = dict(context.get("chart_asset") or {})
        family = str(chart_asset.get("asset_family") or "").strip()
        if family == "model_comparison_chart":
            return self._chart_model_comparison_output(context, chart_asset)
        if family == "incremental_feature_analysis_chart":
            return self._chart_incremental_output(context, chart_asset)
        if family == "feature_ranking":
            return self._chart_ranking_output(context, chart_asset)
        if family == "feature_story_shap":
            return self._feature_story_output(
                context,
                chart_asset,
                source_key="top_shap_features",
                value_key="mean_abs_shap",
                metric="mean_abs_shap",
                label="SHAP",
            )
        if family == "feature_story_importance":
            return self._feature_story_output(
                context,
                chart_asset,
                source_key="top_feature_importance",
                value_key="importance",
                metric="importance",
                label="feature importance",
            )
        if family == "feature_analysis_combined":
            return self._combined_feature_output(context, chart_asset)
        if family == "correlation":
            return self._correlation_output(context, chart_asset)
        if family == "distribution":
            return self._distribution_output(context, chart_asset)
        if family in {"prediction_overview", "prediction_residuals", "prediction_scatter"}:
            return self._prediction_metrics_output(context, chart_asset)
        if family == "prediction_sequence":
            return self._prediction_sequence_output(context, chart_asset)
        raise ValueError(f"Unsupported chart family for fixture client: {family}")

    def _chart_model_comparison_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        model_metrics = dict(evidence.get("model_metrics") or {})
        rows = list(model_metrics.get("benchmark_models_sorted") or context.get("asset_tables", {}).get("table_model_comparison.csv", []))
        ranked_rows = sorted(rows, key=lambda row: _as_float(row["r2_score"]), reverse=True)
        best_row = ranked_rows[0]
        ranking = [str(row["model"]) for row in ranked_rows[:3]]
        best_model = str(best_row["model"])
        best_r2 = _round_number(_as_float(best_row["r2_score"]))
        explanation_full = (
            f"{best_model} leads this model-comparison chart with R2={best_r2:.6f}. "
            f"The R2 ordering is {' > '.join(ranking)}."
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{best_model} leads the chart-level model comparison.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "best-model",
                    "claim_text": f"{best_model} is the best model in the chart comparison.",
                    "claim_type": "best_model",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "object": best_model,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{best_model} achieved R2={best_r2:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "subject": best_model,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The R2 ranking is {' > '.join(ranking)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "metric": "r2_score",
                    "ordered_items": ranking,
                },
            ],
        }

    def _chart_incremental_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        incremental_story = dict(evidence.get("incremental_story") or {})
        best_steps = list(incremental_story.get("best_step_per_model") or [])
        best_by_r2 = max(best_steps, key=lambda item: _as_float(item["best_r2"]))
        ranked_models = [
            str(item["model"])
            for item in sorted(best_steps, key=lambda item: _as_float(item["best_r2"]), reverse=True)[:3]
        ]
        model_name = str(best_by_r2["model"])
        feature_count = int(best_by_r2["best_n_features"])
        best_r2 = _round_number(_as_float(best_by_r2["best_r2"]))
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{model_name} has the strongest best-step result at {feature_count} features.",
            "explanation_full": (
                f"{model_name} has the strongest best-step result at {feature_count} features "
                f"with R2={best_r2:.6f}. The best-step ranking by R2 is {' > '.join(ranked_models)}."
            ),
            "claims": [
                {
                    "claim_id": "optimum-subset",
                    "claim_text": f"{model_name} reaches its best subset at {feature_count} features.",
                    "claim_type": "feature_subset_optimum",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.96,
                    "subject": model_name,
                    "feature_count": feature_count,
                    "object": str(best_by_r2["best_feature_subset"]),
                    "value": feature_count,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{model_name} reaches R2={best_r2:.6f} at its best step.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.96,
                    "subject": model_name,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The best-step R2 ranking is {' > '.join(ranked_models)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "metric": "r2_score",
                    "ordered_items": ranked_models,
                },
            ],
        }

    def _feature_story_output(
        self,
        context: dict[str, Any],
        chart_asset: dict[str, Any],
        *,
        source_key: str,
        value_key: str,
        metric: str,
        label: str,
    ) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        feature_story = dict(evidence.get("feature_story") or {})
        rows = sorted(
            list(feature_story.get(source_key) or []),
            key=lambda item: _as_float(item[value_key]),
            reverse=True,
        )
        top_item = rows[0]
        ordered_items = [str(item["feature"]) for item in rows[:3]]
        top_feature = str(top_item["feature"])
        top_value = _round_number(_as_float(top_item[value_key]))
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_feature} leads the {label} chart.",
            "explanation_full": (
                f"{top_feature} leads the {label} chart with {metric}={top_value:.6f}. "
                f"The top ordering is {' > '.join(ordered_items)}."
            ),
            "claims": [
                {
                    "claim_id": "top-feature",
                    "claim_text": f"{top_feature} is the top feature by {metric}.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "object": top_feature,
                    "metric": metric,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The {metric} ordering is {' > '.join(ordered_items)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "metric": metric,
                    "ordered_items": ordered_items,
                },
                {
                    "claim_id": "top-score",
                    "claim_text": f"{top_feature} has {metric}={top_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "subject": top_feature,
                    "metric": metric,
                    "value": top_value,
                },
            ],
        }

    def _chart_ranking_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        asset_json_payloads = dict(context.get("asset_json_payloads") or {})
        ranking = list(asset_json_payloads.get("gra_ranking.json") or [])
        if not ranking:
            evidence = dict(chart_asset.get("evidence") or {})
            feature_story = dict(evidence.get("feature_story") or {})
            ranking = list(feature_story.get("top_gra_features") or [])
            for index, item in enumerate(ranking, start=1):
                item.setdefault("rank", index)
        ranking = sorted(ranking, key=lambda item: int(item.get("rank", 10_000)))
        ranking_context = dict(context)
        ranking_context["gra_ranking"] = ranking
        return self._ranking_output(ranking_context)

    def _combined_feature_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        feature_story = dict(evidence.get("feature_story") or {})
        correlation_story = dict(evidence.get("correlation_story") or {})
        top_gra = max(list(feature_story.get("top_gra_features") or []), key=lambda item: _as_float(item["score"]))
        top_importance = max(
            list(feature_story.get("top_feature_importance") or []),
            key=lambda item: _as_float(item["importance"]),
        )
        top_shap = max(
            list(feature_story.get("top_shap_features") or []),
            key=lambda item: _as_float(item["mean_abs_shap"]),
        )
        top_target = max(
            list(correlation_story.get("top_target_correlations") or []),
            key=lambda item: _as_float(item["abs_correlation"]),
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": "The combined feature chart highlights different leaders across lenses.",
            "explanation_full": (
                f"GRA is led by {top_gra['feature']}, feature importance by {top_importance['feature']}, "
                f"SHAP by {top_shap['feature']}, and target correlation by {top_target['feature']}."
            ),
            "claims": [
                {
                    "claim_id": "gra-top",
                    "claim_text": f"{top_gra['feature']} is the top feature by gra_score.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "object": str(top_gra["feature"]),
                    "metric": "gra_score",
                },
                {
                    "claim_id": "importance-top",
                    "claim_text": f"{top_importance['feature']} is the top feature by importance.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "object": str(top_importance["feature"]),
                    "metric": "importance",
                },
                {
                    "claim_id": "shap-top",
                    "claim_text": f"{top_shap['feature']} is the top feature by mean_abs_shap.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "object": str(top_shap["feature"]),
                    "metric": "mean_abs_shap",
                },
                {
                    "claim_id": "target-correlation-top",
                    "claim_text": f"{top_target['feature']} is the top feature by target_correlation.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.91,
                    "object": str(top_target["feature"]),
                    "metric": "target_correlation",
                },
            ],
        }

    def _correlation_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        correlation_story = dict(evidence.get("correlation_story") or {})
        target_rows = sorted(
            list(correlation_story.get("top_target_correlations") or []),
            key=lambda item: _as_float(item["abs_correlation"]),
            reverse=True,
        )
        pair_rows = sorted(
            list(correlation_story.get("strongest_correlations") or []),
            key=lambda item: _as_float(item["abs_correlation"]),
            reverse=True,
        )
        top_target = target_rows[0]
        top_pair = pair_rows[0]
        ordered_items = [str(item["feature"]) for item in target_rows[:3]]
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_target['feature']} has the strongest listed target correlation.",
            "explanation_full": (
                f"{top_target['feature']} has the strongest listed target correlation, while the "
                f"strongest pairwise correlation is {top_pair['pair']} at {float(top_pair['correlation']):.6f}."
            ),
            "claims": [
                {
                    "claim_id": "top-target-feature",
                    "claim_text": f"{top_target['feature']} is the top feature by target_correlation.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "object": str(top_target["feature"]),
                    "metric": "target_correlation",
                },
                {
                    "claim_id": "target-ranking",
                    "claim_text": f"The target_correlation ordering is {' > '.join(ordered_items)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "metric": "target_correlation",
                    "ordered_items": ordered_items,
                },
                {
                    "claim_id": "top-pair",
                    "claim_text": f"{top_pair['pair']} has correlation={float(top_pair['correlation']):.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "subject": str(top_pair["pair"]),
                    "metric": "correlation",
                    "value": _round_number(_as_float(top_pair["correlation"])),
                },
            ],
        }

    def _distribution_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        distribution_story = dict(evidence.get("distribution_story") or {})
        rows = list(distribution_story.get("descriptive_statistics_sample") or [])
        mean_rows = sorted(rows, key=lambda item: _as_float(item["mean"]), reverse=True)
        std_rows = sorted(rows, key=lambda item: _as_float(item["std"]), reverse=True)
        top_mean = mean_rows[0]
        top_std = std_rows[0]
        ordered_mean = [str(item["Unnamed: 0"]) for item in mean_rows[:3]]
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_mean['Unnamed: 0']} has the highest mean in the sample summary.",
            "explanation_full": (
                f"{top_mean['Unnamed: 0']} has the highest mean, while {top_std['Unnamed: 0']} has the highest std. "
                f"The leading mean ordering is {' > '.join(ordered_mean)}."
            ),
            "claims": [
                {
                    "claim_id": "top-mean",
                    "claim_text": f"{top_mean['Unnamed: 0']} is the top feature by mean.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "object": str(top_mean["Unnamed: 0"]),
                    "metric": "mean",
                },
                {
                    "claim_id": "mean-ranking",
                    "claim_text": f"The mean ordering is {' > '.join(ordered_mean)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.89,
                    "metric": "mean",
                    "ordered_items": ordered_mean,
                },
                {
                    "claim_id": "top-std",
                    "claim_text": f"{top_std['Unnamed: 0']} is the top feature by std.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "object": str(top_std["Unnamed: 0"]),
                    "metric": "std",
                },
            ],
        }

    def _prediction_metrics_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        model_metrics = dict(evidence.get("model_metrics") or {})
        prediction_story = dict(evidence.get("prediction_story") or {})
        if str(chart_asset.get("asset_family")) == "prediction_scatter":
            model_name = str(model_metrics.get("model_name") or "").strip()
            metrics_row = dict(model_metrics.get("metrics") or {})
            diagnostics = dict(prediction_story.get("diagnostics") or {})
            third_metric = "linear_fit_slope"
        else:
            model_name = str(model_metrics.get("winning_model") or "").strip()
            metrics_row = dict(model_metrics.get("best_model_metrics") or {})
            diagnostics = dict(prediction_story.get("winning_model_diagnostics") or {})
            third_metric = "residual_std" if str(chart_asset.get("asset_family")) == "prediction_residuals" else "max_abs_residual"

        r2_value = _round_number(_as_float(metrics_row["r2_score"]))
        correlation_value = _round_number(_as_float(diagnostics["pred_actual_correlation"]))
        third_value = _round_number(_as_float(diagnostics[third_metric]))
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{model_name} diagnostics show a strong overall fit.",
            "explanation_full": (
                f"{model_name} reaches R2={r2_value:.6f}, pred_actual_correlation={correlation_value:.6f}, "
                f"and {third_metric}={third_value:.6f}."
            ),
            "claims": [
                {
                    "claim_id": "r2",
                    "claim_text": f"{model_name} has r2_score={r2_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "subject": model_name,
                    "metric": "r2_score",
                    "value": r2_value,
                },
                {
                    "claim_id": "correlation",
                    "claim_text": f"{model_name} has pred_actual_correlation={correlation_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.94,
                    "subject": model_name,
                    "metric": "pred_actual_correlation",
                    "value": correlation_value,
                },
                {
                    "claim_id": "third-metric",
                    "claim_text": f"{model_name} has {third_metric}={third_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "subject": model_name,
                    "metric": third_metric,
                    "value": third_value,
                },
            ],
        }

    def _prediction_sequence_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        model_metrics = dict(evidence.get("model_metrics") or {})
        sequence_story = dict(evidence.get("sequence_story") or {})
        model_name = str(model_metrics.get("winning_model") or "").strip()
        diagnostics = dict(sequence_story.get("winning_model_sequence_diagnostics") or {})
        sequence_correlation = _round_number(_as_float(diagnostics["sequence_correlation"]))
        mean_abs_gap = _round_number(_as_float(diagnostics["mean_abs_gap"]))
        actual_peak_index = int(diagnostics["actual_peak_index"])
        predicted_peak_index = int(diagnostics["predicted_peak_index"])
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{model_name} tracks the overall sequence well but misses peak timing.",
            "explanation_full": (
                f"{model_name} reaches sequence_correlation={sequence_correlation:.6f} with "
                f"mean_abs_gap={mean_abs_gap:.6f}; the actual peak is at index {actual_peak_index} "
                f"while the predicted peak is at index {predicted_peak_index}."
            ),
            "claims": [
                {
                    "claim_id": "sequence-correlation",
                    "claim_text": f"{model_name} has sequence_correlation={sequence_correlation:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "subject": model_name,
                    "metric": "sequence_correlation",
                    "value": sequence_correlation,
                },
                {
                    "claim_id": "mean-gap",
                    "claim_text": f"{model_name} has mean_abs_gap={mean_abs_gap:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.94,
                    "subject": model_name,
                    "metric": "mean_abs_gap",
                    "value": mean_abs_gap,
                },
                {
                    "claim_id": "actual-peak-index",
                    "claim_text": f"{model_name} has actual_peak_index={actual_peak_index}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "subject": model_name,
                    "metric": "actual_peak_index",
                    "value": actual_peak_index,
                },
                {
                    "claim_id": "predicted-peak-index",
                    "claim_text": f"{model_name} has predicted_peak_index={predicted_peak_index}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "subject": model_name,
                    "metric": "predicted_peak_index",
                    "value": predicted_peak_index,
                },
            ],
        }

    def _model_comparison_output(self, context: dict[str, Any]) -> dict[str, Any]:
        rows = list(context.get("table_model_comparison", []))
        ranked_rows = sorted(rows, key=lambda row: _as_float(row["r2_score"]), reverse=True)
        best_row = ranked_rows[0]
        second_row = ranked_rows[1] if len(ranked_rows) > 1 else ranked_rows[0]
        ranking = [str(row["model"]) for row in ranked_rows[:3]]
        best_model = str(best_row["model"])
        best_r2 = _round_number(_as_float(best_row["r2_score"]))
        gap = _round_number(_as_float(best_row["r2_score"]) - _as_float(second_row["r2_score"]))

        explanation_full = (
            f"{best_model} is the best-performing model in this comparison with "
            f"R2={best_r2:.6f}. The leading order by R2 is "
            f"{' > '.join(ranking)}. The R2 gap between {best_model} and "
            f"{second_row['model']} is {gap:.6f}."
        )
        if context.get("input_condition") == "image_table_summary":
            explanation_full += " Summary text was available, but the table remained the primary source."
        elif context.get("chart_files"):
            explanation_full += " Chart files were available as secondary evidence."

        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{best_model} leads the model comparison on R2 and error metrics.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "best-model",
                    "claim_text": f"{best_model} is the best model in the comparison.",
                    "claim_type": "best_model",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.98,
                    "object": best_model,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{best_model} achieved R2={best_r2:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.98,
                    "subject": best_model,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The leading R2 ranking is {' > '.join(ranking)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.94,
                    "metric": "r2_score",
                    "ordered_items": ranking,
                },
            ],
        }

    def _incremental_output(self, context: dict[str, Any]) -> dict[str, Any]:
        rows = list(context.get("table1_incremental_results", []))
        best_model = ""
        best_row: dict[str, Any] = {}
        best_r2 = None
        for row in rows:
            for key, raw_value in row.items():
                if not key.endswith("_R2"):
                    continue
                value = _as_float(raw_value)
                if best_r2 is None or value > best_r2:
                    best_r2 = value
                    best_model = key[:-3]
                    best_row = row
        if best_r2 is None:
            raise ValueError("Fixture client could not find incremental R2 values.")

        best_r2 = _round_number(best_r2)
        feature_count = int(float(best_row["n_features"]))
        feature_subset = str(best_row["feature_subset"])
        explanation_full = (
            f"The strongest incremental result occurs for {best_model} at {feature_count} "
            f"features with R2={best_r2:.6f}. The best subset is {feature_subset}, and "
            f"performance has effectively plateaued from that point onward."
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{best_model} peaks at {feature_count} features.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "optimum-subset",
                    "claim_text": f"{best_model} reaches its best subset at {feature_count} features.",
                    "claim_type": "feature_subset_optimum",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "subject": best_model,
                    "feature_count": feature_count,
                    "object": feature_subset,
                    "value": feature_count,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{best_model} reaches R2={best_r2:.6f} at the optimum subset.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "subject": best_model,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "plateau",
                    "claim_text": f"Performance plateaus after {feature_count} features.",
                    "claim_type": "plateau",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "subject": best_model,
                    "feature_count": feature_count,
                    "value": feature_count,
                },
            ],
        }

    def _ranking_output(self, context: dict[str, Any]) -> dict[str, Any]:
        ranking = sorted(context.get("gra_ranking", []), key=lambda item: int(item.get("rank", 10_000)))
        top = ranking[0]
        ordered_items = [str(item["feature"]) for item in ranking[:3]]
        top_feature = str(top["feature"])
        top_score = _round_number(_as_float(top["score"]))
        explanation_full = (
            f"The GRA ranking is led by {top_feature} with score {top_score:.6f}. "
            f"The top ordering is {' > '.join(ordered_items)}."
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_feature} is the top-ranked GRA feature.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "top-feature",
                    "claim_text": f"{top_feature} is the top feature in the GRA ranking.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.98,
                    "object": top_feature,
                },
                {
                    "claim_id": "rank-order",
                    "claim_text": f"The top GRA ordering is {' > '.join(ordered_items)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "ordered_items": ordered_items,
                },
                {
                    "claim_id": "top-score",
                    "claim_text": f"{top_feature} has GRA score {top_score:.6f}.",
                    "claim_type": "rank_score",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.96,
                    "subject": top_feature,
                    "metric": "gra_score",
                    "value": top_score,
                },
            ],
        }


def _claim_schema() -> dict[str, Any]:
    scalar_or_null = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "integer"},
            {"type": "boolean"},
            {"type": "null"},
        ]
    }
    return {
        "type": "object",
        "properties": {
            "claim_id": {"type": "string"},
            "claim_text": {"type": "string"},
            "claim_type": {"type": "string"},
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
            "ordered_items": {
                "type": "array",
                "items": {"type": "string"},
            },
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


def _generation_schema(allowed_arms: list[str], allowed_conditions: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "artifact_id": {"type": "string"},
            "arm": {"type": "string", "enum": allowed_arms},
            "input_condition": {"type": "string", "enum": allowed_conditions},
            "explanation_short": {"type": "string"},
            "explanation_full": {"type": "string"},
            "claims": {
                "type": "array",
                "items": _claim_schema(),
            },
        },
        "required": [
            "artifact_id",
            "arm",
            "input_condition",
            "explanation_short",
            "explanation_full",
            "claims",
        ],
        "additionalProperties": False,
    }


def _single_generation_schema(allowed_arms: list[str], allowed_conditions: list[str]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_generation",
            "strict": True,
            "schema": _generation_schema(allowed_arms, allowed_conditions),
        },
    }


def _batch_generation_schema(
    *,
    generation_count: int,
    allowed_arms: list[str],
    allowed_conditions: list[str],
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_generation_batch",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "generations": {
                        "type": "array",
                        "items": _generation_schema(allowed_arms, allowed_conditions),
                        "minItems": generation_count,
                        "maxItems": generation_count,
                    }
                },
                "required": ["generations"],
                "additionalProperties": False,
            },
        },
    }


class OpenAILLMClient(BaseLLMClient):
    """Real LLM client for benchmark generation with one request per artifact."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = OPENAI_BENCHMARK_TIMEOUT_SECONDS,
    ) -> None:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
        resolved_api_key = str(api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not resolved_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured for the benchmark client.")
        self.api_key = resolved_api_key
        self.model_name = str(model or os.getenv("OPENAI_BENCHMARK_MODEL") or OPENAI_BENCHMARK_MODEL).strip()
        self.timeout_seconds = max(60, int(timeout_seconds))

    @staticmethod
    def _retry_after_seconds(response: Any) -> float | None:
        if response is None:
            return None

        retry_after = str(response.headers.get("Retry-After") or "").strip()
        if not retry_after:
            return None

        try:
            return max(0.0, float(retry_after))
        except ValueError:
            return None

    def _call_openai(self, payload: dict[str, Any]) -> dict[str, Any]:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1, OPENAI_BENCHMARK_MAX_RETRIES + 1):
            try:
                with shared_openai_request_gate().request_slot(
                    OPENAI_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS,
                    OPENAI_BENCHMARK_RETRY_JITTER_SECONDS,
                ):
                    response = requests.post(
                        OPENAI_CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout_seconds,
                    )
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice.get("message") or {}
                parsed = message.get("parsed")
                if isinstance(parsed, dict):
                    return parsed

                content = message.get("content")
                if isinstance(content, list):
                    text_parts: list[str] = []
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        text = item.get("text") or item.get("content") or ""
                        if isinstance(text, str) and text.strip():
                            text_parts.append(text)
                    content = "".join(text_parts)

                if not isinstance(content, str) or not content.strip():
                    finish_reason = choice.get("finish_reason")
                    if finish_reason == "length":
                        raise ValueError(
                            "OpenAI benchmark response hit finish_reason='length' before emitting JSON. "
                            "Increase max_completion_tokens or reduce prompt size."
                        )
                    raise ValueError(
                        "OpenAI benchmark response did not contain a parseable JSON payload."
                    )
                return json.loads(content)
            except requests.HTTPError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                should_retry = status_code == 429 or (status_code is not None and status_code >= 500)
                if not should_retry or attempt >= OPENAI_BENCHMARK_MAX_RETRIES:
                    raise
                retry_after_seconds = self._retry_after_seconds(exc.response)
            except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= OPENAI_BENCHMARK_MAX_RETRIES:
                    raise
                retry_after_seconds = None

            wait_seconds = max(
                retry_after_seconds or 0.0,
                OPENAI_BENCHMARK_RETRY_BACKOFF_SECONDS * attempt,
            ) + random.uniform(0.0, OPENAI_BENCHMARK_RETRY_JITTER_SECONDS)
            shared_openai_request_gate().push_cooldown(wait_seconds)
            print(
                f"⚠️ Benchmark OpenAI request attempt {attempt}/{OPENAI_BENCHMARK_MAX_RETRIES} failed: "
                f"{last_error}. Retrying in {wait_seconds:.1f}s."
            )
            time.sleep(wait_seconds)

        raise RuntimeError(
            f"Benchmark OpenAI request failed after {OPENAI_BENCHMARK_MAX_RETRIES} attempts: {last_error}"
        )

    def generate_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate artifact-grounded ML explanations for offline benchmarking. "
                        "Return strict JSON only. Unsupported claims must be omitted rather than hedged."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": _single_generation_schema(
                allowed_arms=[str(context.get("arm") or "A")],
                allowed_conditions=[str(context.get("input_condition") or "table_only")],
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }
        return self._call_openai(payload)

    def generate_artifact(
        self,
        inputs: ArtifactInputs,
        arms: list[str],
        conditions: list[str],
    ) -> list[dict[str, Any]]:
        requested_outputs: list[dict[str, Any]] = []
        for arm in arms:
            for condition in conditions:
                requested_outputs.append(
                    {
                        "arm": arm,
                        "input_condition": condition,
                        "arm_instruction": ARM_INSTRUCTIONS.get(arm, ARM_INSTRUCTIONS["A"]),
                        "context": build_prompt_context(inputs=inputs, arm=arm, condition=condition),
                    }
                )

        payload = {
            "task": (
                "Generate one explanation output for each requested arm-condition pair. "
                "Each output must stay artifact-grounded and include explicit claims."
            ),
            "rules": [
                "Table/json evidence outranks chart evidence.",
                "Chart evidence outranks summary text.",
                "Do not use llm_explanations.json as ground truth.",
                "Unsupported claims are worse than omissions.",
                "Keep explanation_short to one sentence.",
                "Keep explanation_full concise: roughly 60-100 words per output.",
                "Prefer 2-4 claims per output, but include enough claims to cover the strongest supported facts.",
            ],
            "requested_outputs": requested_outputs,
        }
        request_payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate artifact-grounded ML explanations for offline benchmarking. "
                        "Return strict JSON only. Claims must be evidence-backed."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "response_format": _batch_generation_schema(
                generation_count=len(requested_outputs),
                allowed_arms=arms,
                allowed_conditions=conditions,
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": max(2200, 1200 * len(requested_outputs)),
        }
        parsed = self._call_openai(request_payload)
        generations = parsed.get("generations")
        if not isinstance(generations, list):
            raise ValueError("OpenAI benchmark response did not contain a generations array.")
        return [generation for generation in generations if isinstance(generation, dict)]
