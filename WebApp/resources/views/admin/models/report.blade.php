@extends('layouts.app')

@section('title', __('models.machine_learning_models') . ' - Training Report')
@section('page-title', 'Model Training Report')

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route(($routeNamespace ?? 'admin') . '.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route(($routeNamespace ?? 'admin') . '.models') }}">{{ __('nav.models') }}</a></li>
    <li class="breadcrumb-item active">Training Report</li>
@endsection

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('content')
@php
    $routeNamespace = $routeNamespace ?? 'admin';
    $selectedMetrics = is_array($summary['selected_model_metrics'] ?? null) ? $summary['selected_model_metrics'] : [];
    $benchmarkRows = is_array($summary['benchmark_models'] ?? null) ? $summary['benchmark_models'] : [];
    $trainedAt = $model->CreatedDate ?? $model->created_at;
    $inlineTables = is_array($inlineTables ?? null) ? $inlineTables : [];
    $llmExplanations = is_array($llmExplanations ?? null) ? $llmExplanations : [];
    $explanationAssets = is_array($llmExplanations['assets'] ?? null) ? $llmExplanations['assets'] : [];
    $explanationLocale = str_starts_with(app()->getLocale(), 'zh') ? 'zh_TW' : 'en';
    $resolveExplanation = function (string $key) use ($explanationAssets, $explanationLocale): string {
        $payload = is_array($explanationAssets[$key] ?? null) ? $explanationAssets[$key] : [];
        $preferred = trim((string) ($payload[$explanationLocale] ?? ''));
        if ($preferred !== '') {
            return $preferred;
        }
        $fallback = trim((string) ($payload['en'] ?? $payload['zh_TW'] ?? ''));
        return $fallback;
    };

    $keyLabels = [
        'training_bundle_zip' => 'Training Bundle ZIP',
        'llm_explanations' => 'AI Explanations JSON',
        'summary' => 'Summary JSON',
        'best_model_summary' => 'Best Model Summary JSON',
        'analysis_summary' => 'Analysis Summary TXT',
        'results_summary' => 'Paper Results Summary TXT',
        'table1_incremental_results' => 'Incremental Results CSV',
        'best_model' => 'Best Model PKL',
        'best_model_info' => 'Best Model Info TXT',
        'best_scaler_X' => 'Scaler X PKL',
        'best_scaler_Y' => 'Scaler Y PKL',
        'scaler' => 'Shared Scaler PKL',
        'best_model_shap_importance' => 'SHAP Importance CSV',
        'best_model_shap_values' => 'SHAP Values NPY',
        'model_comparison_bars' => 'Model Comparison',
        'model_comparison_table' => 'Model Comparison CSV',
        'predicted_vs_actual' => 'Predicted vs Actual',
        'residuals' => 'Residuals',
        'feature_importance' => 'Feature Importance',
        'feature_importance_table' => 'Feature Importance CSV',
        'descriptive_statistics' => 'Descriptive Statistics CSV',
        'correlation_matrix' => 'Correlation Matrix CSV',
        'correlation_heatmap' => 'Correlation Heatmap',
        'feature_distributions' => 'Feature Distributions',
        'feature_vs_target' => 'Feature vs Target',
        'boxplots' => 'Boxplots',
        'time_series' => 'Time Series',
        'gra_ranking' => 'GRA Ranking JSON',
        'fig3a_gra_ranking' => 'Figure 3A - GRA Ranking',
        'fig3b_shap_analysis' => 'Figure 3B - SHAP Analysis',
        'fig3_feature_analysis' => 'Figure 3 - Combined Feature Analysis',
        'fig4_univariate_analysis' => 'Figure 4 - Univariate Analysis',
        'fig5_model_comparison' => 'Figure 5 - Model Comparison',
        'fig6ab_mse_r2_features' => 'Figure 6A/B - MSE and R² vs Features',
        'fig6c_prediction_time' => 'Figure 6C - Prediction over Time',
        'model_svm_scatter' => 'SVM Scatter',
        'model_dt_scatter' => 'Decision Tree Scatter',
        'model_rf_scatter' => 'Random Forest Scatter',
        'model_knn_scatter' => 'KNN Scatter',
        'model_xgboost_scatter' => 'XGBoost Scatter',
    ];
    $allAssetKeys = array_keys($reportAssets ?? []);
    $isImageKey = function (string $key) use ($reportAssets): bool {
        $filename = (string) ($reportAssets[$key]['filename'] ?? '');
        return (bool) preg_match('/\.(png|jpe?g|gif|webp|svg)$/i', $filename);
    };
    $orderedKeys = function (array $preferred) use ($reportAssets): array {
        $keys = [];
        foreach ($preferred as $key) {
            if (isset($reportAssets[$key])) {
                $keys[] = $key;
            }
        }
        return $keys;
    };
    $paperFigureKeys = $orderedKeys([
        'fig3a_gra_ranking',
        'fig3b_shap_analysis',
        'fig3_feature_analysis',
        'fig4_univariate_analysis',
        'fig5_model_comparison',
        'fig6ab_mse_r2_features',
        'fig6c_prediction_time',
    ]);
    $scatterImageKeys = $orderedKeys([
        'model_svm_scatter',
        'model_dt_scatter',
        'model_rf_scatter',
        'model_knn_scatter',
        'model_xgboost_scatter',
    ]);
    $supplementaryImageKeys = $orderedKeys([
        'model_comparison_bars',
        'predicted_vs_actual',
        'residuals',
        'feature_importance',
        'correlation_heatmap',
        'feature_distributions',
        'feature_vs_target',
        'boxplots',
        'time_series',
    ]);
    $usedImageKeys = array_merge($paperFigureKeys, $scatterImageKeys, $supplementaryImageKeys);
    $otherImageKeys = array_values(array_filter(
        $allAssetKeys,
        function ($key) use ($usedImageKeys, $isImageKey) {
            return $isImageKey($key) && !in_array($key, $usedImageKeys, true);
        }
    ));
    $downloadPriorityKeys = $orderedKeys([
        'training_bundle_zip',
        'results_summary',
        'analysis_summary',
        'summary',
        'best_model_summary',
        'table1_incremental_results',
        'model_comparison_table',
        'feature_importance_table',
        'descriptive_statistics',
        'correlation_matrix',
        'best_model_shap_importance',
        'gra_ranking',
        'best_model',
        'best_model_info',
        'best_scaler_X',
        'best_scaler_Y',
        'scaler',
        'best_model_shap_values',
    ]);
    $remainingDownloadKeys = array_values(array_filter(
        $allAssetKeys,
        function ($key) use ($downloadPriorityKeys, $isImageKey) {
            return !in_array($key, $downloadPriorityKeys, true) && !$isImageKey($key);
        }
    ));
    $downloadKeys = array_merge($downloadPriorityKeys, $remainingDownloadKeys);
    $bundleAsset = $reportAssets['training_bundle_zip'] ?? null;
    $overviewExplanation = trim((string) (($llmExplanations['overview'][$explanationLocale] ?? $llmExplanations['overview']['en'] ?? $llmExplanations['overview']['zh_TW'] ?? '')));
@endphp

<div class="row">
    <div class="col-12 mb-3">
        <a href="{{ route($routeNamespace . '.models') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {{ __('back') }} {{ __('nav.models') }}
        </a>
        @if($bundleAsset)
            <a href="{{ $bundleAsset['url'] }}" class="btn btn-primary ms-2" target="_blank" rel="noopener">
                <i class="bi bi-download"></i> Download Training ZIP
            </a>
        @endif
    </div>
</div>

@if($overviewExplanation !== '')
    <div class="alert alert-primary">
        <div class="fw-bold mb-1">AI Report Overview</div>
        <div style="white-space: pre-line;">{{ $overviewExplanation }}</div>
    </div>
@endif

<div class="row">
    <div class="col-lg-6">
        <div class="card mb-3">
            <div class="card-header bg-primary text-white">
                <strong><i class="bi bi-cpu"></i> Model Information</strong>
            </div>
            <div class="card-body">
                <table class="table table-sm mb-0">
                    <tr>
                        <th style="width: 180px;">{{ __('models.name') }}</th>
                        <td>{{ $model->MLMName }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.library_type') }}</th>
                        <td>{{ $model->LibType }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.dataset') }}</th>
                        <td>{{ $model->dataset->DatasetName ?? __('models.na') }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.trained_by') }}</th>
                        <td>{{ $model->trainer->FullName ?? __('models.na') }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.trained_date') }}</th>
                        <td>{{ $trainedAt ? \Carbon\Carbon::parse($trainedAt)->format('Y-m-d H:i:s') : __('models.na') }}</td>
                    </tr>
                    <tr>
                        <th>Report ID</th>
                        <td><code>{{ $reportInfo['report_id'] ?? __('models.na') }}</code></td>
                    </tr>
                </table>
            </div>
        </div>
    </div>

    <div class="col-lg-6">
        <div class="card mb-3">
            <div class="card-header bg-success text-white">
                <strong><i class="bi bi-123"></i> Trained Metrics</strong>
            </div>
            <div class="card-body">
                <div class="row g-2">
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="text-muted small">R²</div>
                            <div class="fw-bold">{{ $model->R2Value !== null ? number_format($model->R2Value, 6) : __('models.na') }}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="text-muted small">RMSE</div>
                            <div class="fw-bold">{{ $model->RMSEValue !== null ? number_format($model->RMSEValue, 6) : __('models.na') }}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="text-muted small">MSE</div>
                            <div class="fw-bold">{{ $model->MSEValue !== null ? number_format($model->MSEValue, 6) : __('models.na') }}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="text-muted small">MAE</div>
                            <div class="fw-bold">{{ $model->MAEValue !== null ? number_format($model->MAEValue, 6) : __('models.na') }}</div>
                        </div>
                    </div>
                </div>

                @if(!empty($selectedMetrics))
                    <hr>
                    <div class="small text-muted mb-1">Selected Model Metrics (from summary.json)</div>
                    <div class="small">
                        R²={{ number_format((float)($selectedMetrics['r2_score'] ?? 0), 6) }},
                        RMSE={{ number_format((float)($selectedMetrics['rmse'] ?? 0), 6) }},
                        MSE={{ number_format((float)($selectedMetrics['mse'] ?? 0), 6) }},
                        MAE={{ number_format((float)($selectedMetrics['mae'] ?? 0), 6) }}
                    </div>
                @endif

                @php $metricsExplanation = $resolveExplanation('metrics_overview'); @endphp
                @if($metricsExplanation !== '')
                    <div class="alert alert-light border mt-3 mb-0 lh-base">
                        <div class="fw-bold mb-1">AI Explanation</div>
                        <div>{{ $metricsExplanation }}</div>
                    </div>
                @endif
            </div>
        </div>
    </div>
</div>

@if($summaryError)
    <div class="alert alert-warning">
        <i class="bi bi-exclamation-triangle"></i> {{ $summaryError }}
    </div>
@endif

@if(empty($llmExplanations) && !empty($reportAssets))
    <div class="alert alert-info">
        <div class="fw-bold mb-1">AI explanations are being generated</div>
        <div class="small">This page will refresh automatically in a few seconds.</div>
    </div>
@endif

<div class="card mb-3">
    <div class="card-header bg-info text-white">
        <strong><i class="bi bi-files"></i> Report Downloads</strong>
    </div>
    <div class="card-body">
        @if(empty($downloadKeys))
            <div class="text-muted">No report artifacts found for this model.</div>
        @else
            @foreach($downloadKeys as $key)
                @php $asset = $reportAssets[$key]; @endphp
                <a href="{{ $asset['url'] }}" target="_blank" rel="noopener" class="btn btn-outline-primary btn-sm me-2 mb-2">
                    {{ $keyLabels[$key] ?? $key }}
                </a>
            @endforeach
        @endif
    </div>
</div>

@if(!empty($paperFigureKeys))
    <div class="card mb-3">
        <div class="card-header bg-dark text-white">
            <strong><i class="bi bi-image"></i> Paper Figures</strong>
        </div>
        <div class="card-body">
            <div class="row">
                @foreach($paperFigureKeys as $key)
                    <div class="col-lg-6 mb-3">
                        <div class="card h-100">
                            <div class="card-header py-2">
                                <small class="fw-bold">{{ $keyLabels[$key] ?? $key }}</small>
                            </div>
                            <div class="card-body text-center">
                                <a href="{{ $reportAssets[$key]['url'] }}" target="_blank" rel="noopener">
                                    <img
                                        src="{{ $reportAssets[$key]['url'] }}"
                                        alt="{{ $keyLabels[$key] ?? $key }}"
                                        class="img-fluid rounded border"
                                        loading="lazy"
                                    >
                                </a>
                                @php $imageExplanation = $resolveExplanation($key); @endphp
                                @if($imageExplanation !== '')
                                    <div class="alert alert-light border mt-3 mb-0 lh-base text-start">
                                        <div class="fw-bold mb-1">AI Explanation</div>
                                        <div>{{ $imageExplanation }}</div>
                                    </div>
                                @endif
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>
        </div>
    </div>
@endif

@if(!empty($scatterImageKeys))
    <div class="card mb-3">
        <div class="card-header bg-secondary text-white">
            <strong><i class="bi bi-graph-up"></i> Model Scatter Charts</strong>
        </div>
        <div class="card-body">
            <div class="row">
                @foreach($scatterImageKeys as $key)
                    <div class="col-lg-4 mb-3">
                        <div class="card h-100">
                            <div class="card-header py-2">
                                <small class="fw-bold">{{ $keyLabels[$key] ?? $key }}</small>
                            </div>
                            <div class="card-body text-center">
                                <a href="{{ $reportAssets[$key]['url'] }}" target="_blank" rel="noopener">
                                    <img
                                        src="{{ $reportAssets[$key]['url'] }}"
                                        alt="{{ $keyLabels[$key] ?? $key }}"
                                        class="img-fluid rounded border"
                                        loading="lazy"
                                    >
                                </a>
                                @php $scatterExplanation = $resolveExplanation($key); @endphp
                                @if($scatterExplanation !== '')
                                    <div class="alert alert-light border mt-3 mb-0 lh-base text-start">
                                        <div class="fw-bold mb-1">AI Explanation</div>
                                        <div>{{ $scatterExplanation }}</div>
                                    </div>
                                @endif
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>
        </div>
    </div>
@endif

@if(!empty($supplementaryImageKeys) || !empty($otherImageKeys))
    <div class="card mb-3">
        <div class="card-header bg-primary text-white">
            <strong><i class="bi bi-bar-chart"></i> Supplementary Charts</strong>
        </div>
        <div class="card-body">
            <div class="row">
                @foreach(array_merge($supplementaryImageKeys, $otherImageKeys) as $key)
                    <div class="col-lg-6 mb-3">
                        <div class="card h-100">
                            <div class="card-header py-2">
                                <small class="fw-bold">{{ $keyLabels[$key] ?? $key }}</small>
                            </div>
                            <div class="card-body text-center">
                                <a href="{{ $reportAssets[$key]['url'] }}" target="_blank" rel="noopener">
                                    <img
                                        src="{{ $reportAssets[$key]['url'] }}"
                                        alt="{{ $keyLabels[$key] ?? $key }}"
                                        class="img-fluid rounded border"
                                        loading="lazy"
                                    >
                                </a>
                                @php $supplementaryExplanation = $resolveExplanation($key); @endphp
                                @if($supplementaryExplanation !== '')
                                    <div class="alert alert-light border mt-3 mb-0 lh-base text-start">
                                        <div class="fw-bold mb-1">AI Explanation</div>
                                        <div>{{ $supplementaryExplanation }}</div>
                                    </div>
                                @endif
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>
        </div>
    </div>
@endif

@if(!empty($inlineTables))
    <div class="card mb-3">
        <div class="card-header bg-info text-white">
            <strong><i class="bi bi-table"></i> Report Data Tables</strong>
        </div>
        <div class="card-body">
            @foreach($inlineTables as $key => $table)
                <div class="mb-4">
                    <div class="fw-bold mb-2">{{ $keyLabels[$key] ?? $key }}</div>
                    <div class="table-responsive border rounded">
                        <table class="table table-sm table-bordered table-striped mb-0">
                            <thead class="table-light">
                                <tr>
                                    @foreach($table['headers'] as $header)
                                        <th>{{ $header }}</th>
                                    @endforeach
                                </tr>
                            </thead>
                            <tbody>
                                @foreach($table['rows'] as $row)
                                    <tr>
                                        @foreach($table['headers'] as $header)
                                            <td>{{ $row[$header] ?? '' }}</td>
                                        @endforeach
                                    </tr>
                                @endforeach
                            </tbody>
                        </table>
                    </div>
                    <div class="small text-muted mt-1">
                        Showing {{ count($table['rows']) }} of {{ $table['row_count'] }} row(s)
                        @if(!empty($table['truncated']))
                            . The table is truncated for display.
                        @endif
                    </div>
                    @php $tableExplanation = $resolveExplanation($key); @endphp
                    @if($tableExplanation !== '')
                        <div class="alert alert-light border mt-2 mb-0 lh-base">
                            <div class="fw-bold mb-1">AI Explanation</div>
                            <div>{{ $tableExplanation }}</div>
                        </div>
                    @endif
                </div>
            @endforeach
        </div>
    </div>
@endif

@if(!empty($benchmarkRows))
    <div class="card mb-3">
        <div class="card-header bg-secondary text-white">
            <strong><i class="bi bi-table"></i> Benchmark Models</strong>
        </div>
        <div class="card-body table-responsive">
            <table class="table table-bordered table-striped table-sm">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>R²</th>
                        <th>RMSE</th>
                        <th>MSE</th>
                        <th>MAE</th>
                    </tr>
                </thead>
                <tbody>
                    @foreach($benchmarkRows as $row)
                        <tr>
                            <td>{{ $row['model'] ?? '-' }}</td>
                            <td>{{ isset($row['r2_score']) ? number_format((float)$row['r2_score'], 6) : '-' }}</td>
                            <td>{{ isset($row['rmse']) ? number_format((float)$row['rmse'], 6) : '-' }}</td>
                            <td>{{ isset($row['mse']) ? number_format((float)$row['mse'], 6) : '-' }}</td>
                            <td>{{ isset($row['mae']) ? number_format((float)$row['mae'], 6) : '-' }}</td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
            @php $benchmarkExplanation = $resolveExplanation('model_comparison_table'); @endphp
            @if($benchmarkExplanation !== '')
                <div class="alert alert-light border mt-3 mb-0 lh-base">
                    <div class="fw-bold mb-1">AI Explanation</div>
                    <div>{{ $benchmarkExplanation }}</div>
                </div>
            @endif
        </div>
    </div>
@endif
@endsection

@section('scripts')
@if(empty($llmExplanations) && !empty($reportAssets))
<script>
setTimeout(function () {
    window.location.reload();
}, 12000);
</script>
@endif
@endsection
