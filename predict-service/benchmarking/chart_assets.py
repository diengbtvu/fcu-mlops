from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartAssetSpec:
    key: str
    family: str
    chart_type: str

    @property
    def artifact_type(self) -> str:
        return f"chart/{self.key}"


CHART_ASSET_SPECS: dict[str, ChartAssetSpec] = {
    "fig3a_gra_ranking": ChartAssetSpec(
        key="fig3a_gra_ranking",
        family="feature_ranking",
        chart_type="ranking_chart",
    ),
    "fig3b_shap_analysis": ChartAssetSpec(
        key="fig3b_shap_analysis",
        family="feature_story_shap",
        chart_type="bar_chart",
    ),
    "fig3_feature_analysis": ChartAssetSpec(
        key="fig3_feature_analysis",
        family="feature_analysis_combined",
        chart_type="composite_chart",
    ),
    "fig4_univariate_analysis": ChartAssetSpec(
        key="fig4_univariate_analysis",
        family="correlation",
        chart_type="correlation_chart",
    ),
    "fig5_model_comparison": ChartAssetSpec(
        key="fig5_model_comparison",
        family="model_comparison_chart",
        chart_type="bar_chart",
    ),
    "fig6ab_mse_r2_features": ChartAssetSpec(
        key="fig6ab_mse_r2_features",
        family="incremental_feature_analysis_chart",
        chart_type="line_chart",
    ),
    "fig6c_prediction_time": ChartAssetSpec(
        key="fig6c_prediction_time",
        family="prediction_sequence",
        chart_type="line_chart",
    ),
    "model_svm_scatter": ChartAssetSpec(
        key="model_svm_scatter",
        family="prediction_scatter",
        chart_type="scatter_plot",
    ),
    "model_dt_scatter": ChartAssetSpec(
        key="model_dt_scatter",
        family="prediction_scatter",
        chart_type="scatter_plot",
    ),
    "model_rf_scatter": ChartAssetSpec(
        key="model_rf_scatter",
        family="prediction_scatter",
        chart_type="scatter_plot",
    ),
    "model_knn_scatter": ChartAssetSpec(
        key="model_knn_scatter",
        family="prediction_scatter",
        chart_type="scatter_plot",
    ),
    "model_xgboost_scatter": ChartAssetSpec(
        key="model_xgboost_scatter",
        family="prediction_scatter",
        chart_type="scatter_plot",
    ),
    "model_comparison_bars": ChartAssetSpec(
        key="model_comparison_bars",
        family="model_comparison_chart",
        chart_type="bar_chart",
    ),
    "predicted_vs_actual": ChartAssetSpec(
        key="predicted_vs_actual",
        family="prediction_overview",
        chart_type="scatter_plot",
    ),
    "residuals": ChartAssetSpec(
        key="residuals",
        family="prediction_residuals",
        chart_type="residual_plot",
    ),
    "feature_importance": ChartAssetSpec(
        key="feature_importance",
        family="feature_story_importance",
        chart_type="bar_chart",
    ),
    "correlation_heatmap": ChartAssetSpec(
        key="correlation_heatmap",
        family="correlation",
        chart_type="heatmap",
    ),
    "feature_distributions": ChartAssetSpec(
        key="feature_distributions",
        family="distribution",
        chart_type="distribution_plot",
    ),
    "feature_vs_target": ChartAssetSpec(
        key="feature_vs_target",
        family="correlation",
        chart_type="correlation_chart",
    ),
    "boxplots": ChartAssetSpec(
        key="boxplots",
        family="distribution",
        chart_type="boxplot",
    ),
    "time_series": ChartAssetSpec(
        key="time_series",
        family="prediction_sequence",
        chart_type="time_series",
    ),
}


def get_chart_asset_spec(asset_key: str) -> ChartAssetSpec | None:
    return CHART_ASSET_SPECS.get(asset_key)
