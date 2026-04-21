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
    $selectedBenchmarkExplanations = is_array($selectedBenchmarkExplanations ?? null)
        ? $selectedBenchmarkExplanations
        : [];
    $llmExplanationStatus = is_array($summary['llm_explanations_status'] ?? null)
        ? $summary['llm_explanations_status']
        : [];
    $benchmarkSummary = is_array($summary['benchmark_summary'] ?? null)
        ? $summary['benchmark_summary']
        : [];
    $benchmarkStatusPayload = is_array($summary['benchmark_status'] ?? null)
        ? $summary['benchmark_status']
        : [];
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
        'benchmark_manifest' => 'Benchmark Manifest JSONL',
        'benchmark_run_metadata' => 'Benchmark Run Metadata JSON',
        'benchmark_leaderboard_json' => 'Benchmark Leaderboard JSON',
        'benchmark_leaderboard_csv' => 'Benchmark Leaderboard CSV',
        'benchmark_selected_explanations' => 'Benchmark-selected Explanations JSON',
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
        'benchmark_selected_explanations',
        'benchmark_leaderboard_json',
        'benchmark_leaderboard_csv',
        'benchmark_run_metadata',
        'benchmark_manifest',
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
    $overviewRaw = trim((string) (($llmExplanations['overview'][$explanationLocale] ?? $llmExplanations['overview']['en'] ?? $llmExplanations['overview']['zh_TW'] ?? '')));
    // Strip the other language if the LLM accidentally merged both into one string.
    if ($explanationLocale === 'en' && preg_match('/\bzh_TW\s*[：:]/u', $overviewRaw)) {
        $overviewRaw = trim(preg_replace('/\bzh_TW\s*[：:].*$/su', '', $overviewRaw));
    } elseif ($explanationLocale === 'zh_TW' && preg_match('/\bzh_TW\s*[：:]/u', $overviewRaw)) {
        $overviewRaw = trim(preg_replace('/^.*?\bzh_TW\s*[：:]\s*/su', '', $overviewRaw));
    }
    $overviewExplanation = $overviewRaw;
    $llmStatus = strtolower(trim((string) ($llmExplanationStatus['status'] ?? '')));
    $llmStatusMessage = trim((string) ($llmExplanationStatus['message'] ?? ''));
    $llmProgress = (float) ($llmExplanationStatus['progress'] ?? 0);
    $llmProgress = max(0, min(100, $llmProgress));
    $llmPhase = trim((string) ($llmExplanationStatus['phase'] ?? ''));
    $llmStepIndex = isset($llmExplanationStatus['step_index']) ? (int) $llmExplanationStatus['step_index'] : null;
    $llmTotalSteps = isset($llmExplanationStatus['total_steps']) ? (int) $llmExplanationStatus['total_steps'] : null;
    $llmCurrentItems = is_array($llmExplanationStatus['current_items'] ?? null)
        ? array_values(array_filter(array_map('strval', $llmExplanationStatus['current_items'])))
        : [];
    $formatRetryText = function (array $retry): string {
        $attempt = isset($retry['attempt']) ? (int) $retry['attempt'] : 0;
        $maxAttempts = isset($retry['max_attempts']) ? (int) $retry['max_attempts'] : 0;
        $waitSeconds = isset($retry['wait_seconds']) ? round((float) $retry['wait_seconds'], 1) : null;
        $reason = trim((string) ($retry['reason'] ?? ''));
        $statusCode = isset($retry['status_code']) ? (int) $retry['status_code'] : null;
        if ($attempt <= 0 || $maxAttempts <= 0) {
            return '';
        }

        $parts = ["Retry {$attempt} / {$maxAttempts}"];
        if ($waitSeconds !== null) {
            $parts[] = "waiting " . number_format($waitSeconds, 1) . "s";
        }
        if ($reason !== '') {
            $parts[] = $reason;
        }
        if ($statusCode !== null) {
            $parts[] = "HTTP {$statusCode}";
        }

        return implode(' • ', $parts);
    };
    $llmRetryPayload = is_array($llmExplanationStatus['retry'] ?? null)
        ? $llmExplanationStatus['retry']
        : [];
    $llmRetryText = $formatRetryText($llmRetryPayload);
    $llmStartedAt = null;
    $llmPendingTooLong = false;
    if ($llmStatus === 'pending' && !empty($llmExplanationStatus['started_at'])) {
        try {
            $llmStartedAt = \Carbon\Carbon::parse($llmExplanationStatus['started_at']);
            $llmPendingTooLong = $llmStartedAt->lt(now()->subMinutes(5));
        } catch (\Throwable $e) {
            $llmStartedAt = null;
        }
    }
    $recentlyTrainedWithoutExplanations = false;
    if (empty($llmExplanations) && $trainedAt) {
        try {
            $recentlyTrainedWithoutExplanations = \Carbon\Carbon::parse($trainedAt)->gt(now()->subMinutes(15));
        } catch (\Throwable $e) {
            $recentlyTrainedWithoutExplanations = false;
        }
    }
    $shouldPollLlm = !empty($summaryPublicUrl) && (
        $llmStatus === 'pending'
        || $llmStatus === ''
        || ($llmStatus === 'success' && empty($llmExplanations))
        || $recentlyTrainedWithoutExplanations
    );
    $benchmarkStatus = strtolower(trim((string) ($benchmarkStatusPayload['status'] ?? '')));
    $benchmarkStatusMessage = trim((string) ($benchmarkStatusPayload['message'] ?? ''));
    $benchmarkProgress = (float) ($benchmarkStatusPayload['progress'] ?? 0);
    $benchmarkProgress = max(0, min(100, $benchmarkProgress));
    $benchmarkPhase = trim((string) ($benchmarkStatusPayload['phase'] ?? ''));
    $benchmarkStepIndex = isset($benchmarkStatusPayload['step_index']) ? (int) $benchmarkStatusPayload['step_index'] : null;
    $benchmarkTotalSteps = isset($benchmarkStatusPayload['total_steps']) ? (int) $benchmarkStatusPayload['total_steps'] : null;
    $benchmarkCurrentItems = is_array($benchmarkStatusPayload['current_items'] ?? null)
        ? array_values(array_filter(array_map('strval', $benchmarkStatusPayload['current_items'])))
        : [];
    $benchmarkRetryPayload = is_array($benchmarkStatusPayload['retry'] ?? null)
        ? $benchmarkStatusPayload['retry']
        : [];
    $benchmarkRetryText = $formatRetryText($benchmarkRetryPayload);
    $benchmarkStartedAt = null;
    $benchmarkPendingTooLong = false;
    if ($benchmarkStatus === 'pending' && !empty($benchmarkStatusPayload['started_at'])) {
        try {
            $benchmarkStartedAt = \Carbon\Carbon::parse($benchmarkStatusPayload['started_at']);
            $benchmarkPendingTooLong = $benchmarkStartedAt->lt(now()->subMinutes(5));
        } catch (\Throwable $e) {
            $benchmarkStartedAt = null;
        }
    }
    $recentlyTrainedWithoutBenchmark = false;
    if (empty($benchmarkSummary) && $trainedAt) {
        try {
            $recentlyTrainedWithoutBenchmark = \Carbon\Carbon::parse($trainedAt)->gt(now()->subMinutes(15));
        } catch (\Throwable $e) {
            $recentlyTrainedWithoutBenchmark = false;
        }
    }
    $shouldPollBenchmark = !empty($summaryPublicUrl) && (
        $benchmarkStatus === 'pending'
        || ($benchmarkStatus === 'success' && empty($benchmarkSummary))
        || ($benchmarkStatus === '' && $recentlyTrainedWithoutBenchmark)
    );
    $benchmarkPreviewRows = is_array($benchmarkSummary['leaderboard_preview'] ?? null)
        ? $benchmarkSummary['leaderboard_preview']
        : [];
    $benchmarkBestOverall = is_array($benchmarkSummary['best_overall'] ?? null)
        ? $benchmarkSummary['best_overall']
        : [];
    $benchmarkBaselineRow = is_array($benchmarkSummary['baseline_row'] ?? null)
        ? $benchmarkSummary['baseline_row']
        : [];
    $benchmarkSelectedRow = is_array($benchmarkSummary['selected_explanations'] ?? null)
        ? $benchmarkSummary['selected_explanations']
        : [];
    $benchmarkWarnings = is_array($benchmarkSummary['warnings'] ?? null)
        ? array_values(array_filter(array_map('strval', $benchmarkSummary['warnings'])))
        : [];
    $benchmarkLeaderboardJson = $reportAssets['benchmark_leaderboard_json'] ?? null;
    $benchmarkLeaderboardCsv = $reportAssets['benchmark_leaderboard_csv'] ?? null;
    $rawLlmExplanationsExist = is_array($summary['llm_explanations'] ?? null) && !empty($summary['llm_explanations']);
    $awaitingBenchmarkSelection = empty($llmExplanations)
        && ($llmStatus === 'success' || $rawLlmExplanationsExist)
        && in_array($benchmarkStatus, ['', 'pending'], true);
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

@if(!empty($selectedBenchmarkExplanations))
    <div class="alert alert-success">
        <div class="fw-bold mb-1">Displaying benchmark-selected explanations</div>
        <div class="small">
            The report is currently using the best verified benchmark row
            @if(!empty($benchmarkSelectedRow['arm']) || !empty($benchmarkSelectedRow['input_condition']))
                : {{ $benchmarkSelectedRow['arm'] ?? 'n/a' }} · {{ $benchmarkSelectedRow['input_condition'] ?? 'n/a' }}
            @endif
            .
        </div>
    </div>
@endif

@if($awaitingBenchmarkSelection)
    <div class="alert alert-info">
        <div class="fw-bold mb-1">Waiting for benchmark comparison before showing explanations</div>
        <div class="small">
            The raw AI explanation has been generated, but the report will only render explanation text after benchmark comparison across the configured arms finishes and the winning explanation is selected.
        </div>
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

@if(($llmStatus === 'pending' || ($llmStatus === '' && empty($llmExplanations) && !empty($reportAssets)) || ($llmStatus === 'success' && empty($llmExplanations))) && !empty($reportAssets))
    <div
        class="alert {{ $llmPendingTooLong ? 'alert-warning' : 'alert-info' }}"
        id="llmProgressAlert"
        data-summary-url="{{ $summaryPublicUrl }}"
        data-should-poll="{{ $shouldPollLlm ? 'true' : 'false' }}"
    >
        <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="fw-bold" id="llmProgressTitle">
                {{ $llmPendingTooLong ? 'AI explanations are delayed' : 'AI explanations are being generated' }}
            </div>
            <div class="small fw-bold" id="llmProgressPercent">{{ number_format($llmProgress, 0) }}%</div>
        </div>
        <div class="progress" style="height: 10px;">
            <div
                id="llmProgressBar"
                class="progress-bar {{ $llmPendingTooLong ? 'bg-warning' : 'progress-bar-striped progress-bar-animated' }}"
                role="progressbar"
                style="width: {{ $llmProgress }}%;"
                aria-valuenow="{{ (int) round($llmProgress) }}"
                aria-valuemin="0"
                aria-valuemax="100"
            ></div>
        </div>
        <div class="small mt-2" id="llmProgressMessage">
            {{ $llmStatusMessage !== '' ? $llmStatusMessage : 'The AI explanation job is starting in the background.' }}
        </div>
        <div class="small text-muted mt-1" id="llmProgressMeta">
            @if($llmStepIndex && $llmTotalSteps)
                Step {{ $llmStepIndex }} / {{ $llmTotalSteps }}
                @if($llmPhase !== '')
                    • {{ ucfirst($llmPhase) }}
                @endif
            @elseif($llmPhase !== '')
                {{ ucfirst($llmPhase) }}
            @endif
        </div>
        <div class="small text-muted mt-1" id="llmProgressItems">
            @if(!empty($llmCurrentItems))
                {{ implode(' • ', $llmCurrentItems) }}
            @endif
        </div>
        <div class="small text-warning mt-1" id="llmProgressRetry">
            {{ $llmRetryText }}
        </div>
        @if($llmPendingTooLong)
            <div class="small mt-2">Open the predict-service logs on the server to check the exact LLM/API error.</div>
        @endif
    </div>
@elseif($llmStatus === 'error' && !empty($reportAssets))
    <div class="alert alert-danger">
        <div class="fw-bold mb-1">AI explanations failed</div>
        <div class="small">
            {{ $llmStatusMessage !== '' ? $llmStatusMessage : 'The explanation job failed on the server.' }}
        </div>
    </div>
@elseif(empty($llmExplanations) && !empty($reportAssets))
    <div class="alert alert-secondary">
        <div class="fw-bold mb-1">AI explanations are unavailable</div>
        <div class="small">The report does not currently include explanation output, and no active background explanation status was found.</div>
    </div>
@endif

@if($benchmarkStatus === 'pending')
    <div
        class="alert {{ $benchmarkPendingTooLong ? 'alert-warning' : 'alert-info' }}"
        id="benchmarkProgressAlert"
        data-summary-url="{{ $summaryPublicUrl }}"
        data-should-poll="{{ $shouldPollBenchmark ? 'true' : 'false' }}"
    >
        <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="fw-bold" id="benchmarkProgressTitle">
                {{ $benchmarkPendingTooLong ? 'Benchmark evaluation is delayed' : 'Benchmark evaluation is running' }}
            </div>
            <div class="small fw-bold" id="benchmarkProgressPercent">{{ number_format($benchmarkProgress, 0) }}%</div>
        </div>
        <div class="progress" style="height: 10px;">
            <div
                id="benchmarkProgressBar"
                class="progress-bar {{ $benchmarkPendingTooLong ? 'bg-warning' : 'progress-bar-striped progress-bar-animated' }}"
                role="progressbar"
                style="width: {{ $benchmarkProgress }}%;"
                aria-valuenow="{{ (int) round($benchmarkProgress) }}"
                aria-valuemin="0"
                aria-valuemax="100"
            ></div>
        </div>
        <div class="small mt-2" id="benchmarkProgressMessage">
            {{ $benchmarkStatusMessage !== '' ? $benchmarkStatusMessage : 'The benchmark job is waiting for the report bundle.' }}
        </div>
        <div class="small text-muted mt-1" id="benchmarkProgressMeta">
            @if($benchmarkStepIndex && $benchmarkTotalSteps)
                Step {{ $benchmarkStepIndex }} / {{ $benchmarkTotalSteps }}
                @if($benchmarkPhase !== '')
                    • {{ ucfirst($benchmarkPhase) }}
                @endif
            @elseif($benchmarkPhase !== '')
                {{ ucfirst($benchmarkPhase) }}
            @endif
        </div>
        <div class="small text-muted mt-1" id="benchmarkProgressItems">
            @if(!empty($benchmarkCurrentItems))
                {{ implode(' • ', $benchmarkCurrentItems) }}
            @endif
        </div>
        <div class="small text-warning mt-1" id="benchmarkProgressRetry">
            {{ $benchmarkRetryText }}
        </div>
        @if($benchmarkPendingTooLong)
            <div class="small mt-2">Open the predict-service logs on the server to inspect the benchmark runner output.</div>
        @endif
    </div>
@elseif($benchmarkStatus === 'error')
    <div class="alert alert-danger">
        <div class="fw-bold mb-1">Benchmark evaluation failed</div>
        <div class="small">
            {{ $benchmarkStatusMessage !== '' ? $benchmarkStatusMessage : 'The benchmark job failed on the server.' }}
        </div>
    </div>
@endif

@if(!empty($benchmarkSummary))
    <div class="card mb-3">
        <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
            <strong><i class="bi bi-speedometer2"></i> Benchmark Evaluation</strong>
            <div class="small">
                @if(!empty($benchmarkSummary['generated_at']))
                    {{ $benchmarkSummary['generated_at'] }}
                @endif
            </div>
        </div>
        <div class="card-body">
            <div class="row g-3 mb-3">
                <div class="col-lg-4">
                    <div class="border rounded p-3 h-100">
                        <div class="text-muted small mb-1">Best Leaderboard Row</div>
                        @if(!empty($benchmarkBestOverall))
                            <div class="fw-bold">{{ $benchmarkBestOverall['arm'] ?? 'n/a' }} · {{ $benchmarkBestOverall['input_condition'] ?? 'n/a' }}</div>
                            <div class="small mt-2">
                                Fact F1={{ number_format((float) ($benchmarkBestOverall['fact_f1'] ?? 0), 3) }},
                                Precision={{ number_format((float) ($benchmarkBestOverall['fact_precision'] ?? 0), 3) }},
                                Recall={{ number_format((float) ($benchmarkBestOverall['fact_recall'] ?? 0), 3) }}
                            </div>
                        @else
                            <div class="text-muted small">No leaderboard rows were written.</div>
                        @endif
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="border rounded p-3 h-100">
                        <div class="text-muted small mb-1">Baseline Arm</div>
                        @if(!empty($benchmarkBaselineRow))
                            <div class="fw-bold">{{ $benchmarkBaselineRow['arm'] ?? 'n/a' }} · {{ $benchmarkBaselineRow['input_condition'] ?? 'n/a' }}</div>
                            <div class="small mt-2">
                                Fact F1={{ number_format((float) ($benchmarkBaselineRow['fact_f1'] ?? 0), 3) }},
                                Unsupported={{ number_format((float) ($benchmarkBaselineRow['unsupported_claim_rate'] ?? 0), 3) }},
                                Contradiction={{ number_format((float) ($benchmarkBaselineRow['contradiction_rate'] ?? 0), 3) }}
                            </div>
                        @else
                            <div class="text-muted small">No baseline row was available in this run.</div>
                        @endif
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="border rounded p-3 h-100">
                        <div class="text-muted small mb-1">Run Summary</div>
                        <div class="small">
                            Artifacts: {{ (int) ($benchmarkSummary['artifact_count'] ?? 0) }}<br>
                            Generations: {{ (int) ($benchmarkSummary['generation_count'] ?? 0) }}<br>
                            Rows: {{ (int) ($benchmarkSummary['row_count'] ?? 0) }}
                            @if(!empty($benchmarkSummary['baseline_arm']))
                                <br>Baseline: {{ $benchmarkSummary['baseline_arm'] }}
                            @endif
                            @if(!empty($benchmarkSelectedRow))
                                <br>Website uses: {{ $benchmarkSelectedRow['arm'] ?? 'n/a' }} · {{ $benchmarkSelectedRow['input_condition'] ?? 'n/a' }}
                            @endif
                        </div>
                        <div class="mt-2">
                            @if($benchmarkLeaderboardJson)
                                <a href="{{ $benchmarkLeaderboardJson['url'] }}" target="_blank" rel="noopener" class="btn btn-outline-primary btn-sm me-2 mb-2">Leaderboard JSON</a>
                            @endif
                            @if($benchmarkLeaderboardCsv)
                                <a href="{{ $benchmarkLeaderboardCsv['url'] }}" target="_blank" rel="noopener" class="btn btn-outline-primary btn-sm mb-2">Leaderboard CSV</a>
                            @endif
                        </div>
                    </div>
                </div>
            </div>

            @if(!empty($benchmarkPreviewRows))
                <div class="table-responsive">
                    <table class="table table-sm align-middle">
                        <thead>
                            <tr>
                                <th>Arm</th>
                                <th>Condition</th>
                                <th>Fact F1</th>
                                <th>Precision</th>
                                <th>Unsupported</th>
                                <th>Coverage</th>
                            </tr>
                        </thead>
                        <tbody>
                            @foreach($benchmarkPreviewRows as $row)
                                <tr>
                                    <td>{{ $row['arm'] ?? 'n/a' }}</td>
                                    <td>{{ $row['input_condition'] ?? 'n/a' }}</td>
                                    <td>{{ number_format((float) ($row['fact_f1'] ?? 0), 3) }}</td>
                                    <td>{{ number_format((float) ($row['fact_precision'] ?? 0), 3) }}</td>
                                    <td>{{ number_format((float) ($row['unsupported_claim_rate'] ?? 0), 3) }}</td>
                                    <td>{{ number_format((float) ($row['coverage_of_salient_facts'] ?? 0), 3) }}</td>
                                </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
            @endif

            @if(!empty($benchmarkWarnings))
                <div class="alert alert-light border mb-0">
                    <div class="fw-bold mb-1">Benchmark Warnings</div>
                    <div class="small">
                        @foreach($benchmarkWarnings as $warning)
                            <div>{{ $warning }}</div>
                        @endforeach
                    </div>
                </div>
            @endif
        </div>
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
@if($shouldPollLlm || $shouldPollBenchmark)
<script>
(() => {
    const pollers = [];

    const registerPoller = (config) => {
        const alertBox = document.getElementById(config.alertId);
        if (!alertBox || alertBox.dataset.shouldPoll !== 'true') {
            return;
        }

        pollers.push({
            ...config,
            alertBox,
            titleEl: document.getElementById(config.titleId),
            percentEl: document.getElementById(config.percentId),
            barEl: document.getElementById(config.barId),
            messageEl: document.getElementById(config.messageId),
            metaEl: document.getElementById(config.metaId),
            itemsEl: document.getElementById(config.itemsId),
            retryEl: document.getElementById(config.retryId),
            stopped: false,
        });
    };

    registerPoller({
        alertId: 'llmProgressAlert',
        titleId: 'llmProgressTitle',
        percentId: 'llmProgressPercent',
        barId: 'llmProgressBar',
        messageId: 'llmProgressMessage',
        metaId: 'llmProgressMeta',
        itemsId: 'llmProgressItems',
        retryId: 'llmProgressRetry',
        statusKey: 'llm_explanations_status',
        dataKey: 'llm_explanations',
        activeTitle: 'AI explanations are being generated',
        completedTitle: 'AI explanations completed',
        failedTitle: 'AI explanations failed',
        runningMessage: 'The AI explanation job is running.',
        waitingMessage: 'Waiting for the explanation status from the server...',
    });
    registerPoller({
        alertId: 'benchmarkProgressAlert',
        titleId: 'benchmarkProgressTitle',
        percentId: 'benchmarkProgressPercent',
        barId: 'benchmarkProgressBar',
        messageId: 'benchmarkProgressMessage',
        metaId: 'benchmarkProgressMeta',
        itemsId: 'benchmarkProgressItems',
        retryId: 'benchmarkProgressRetry',
        statusKey: 'benchmark_status',
        dataKey: 'benchmark_summary',
        activeTitle: 'Benchmark evaluation is running',
        completedTitle: 'Benchmark evaluation completed',
        failedTitle: 'Benchmark evaluation failed',
        runningMessage: 'The benchmark job is running.',
        waitingMessage: 'Waiting for the benchmark status from the server...',
    });

    if (!pollers.length) {
        return;
    }

    const summaryUrl = pollers[0].alertBox.dataset.summaryUrl;
    if (!summaryUrl) {
        return;
    }

    const setAlertClass = (poller, className) => {
        poller.alertBox.className = className;
    };

    const formatRetryText = (retryPayload) => {
        if (!retryPayload || typeof retryPayload !== 'object') {
            return '';
        }

        const attempt = Number(retryPayload.attempt || 0);
        const maxAttempts = Number(retryPayload.max_attempts || 0);
        if (attempt <= 0 || maxAttempts <= 0) {
            return '';
        }

        const parts = [`Retry ${attempt} / ${maxAttempts}`];
        const waitSeconds = Number(retryPayload.wait_seconds);
        if (Number.isFinite(waitSeconds) && waitSeconds > 0) {
            parts.push(`waiting ${waitSeconds.toFixed(1)}s`);
        }

        const reason = String(retryPayload.reason || '').trim();
        if (reason !== '') {
            parts.push(reason);
        }

        const statusCode = Number(retryPayload.status_code || 0);
        if (statusCode > 0) {
            parts.push(`HTTP ${statusCode}`);
        }

        return parts.join(' • ');
    };

    const updateDom = (poller, summary) => {
        const statusPayload = summary[poller.statusKey] || {};
        const hasData = !!summary[poller.dataKey];
        const status = String(statusPayload.status || '').toLowerCase();
        const progress = Math.max(0, Math.min(100, Number(statusPayload.progress || 0)));
        const phase = String(statusPayload.phase || '').trim();
        const stepIndex = Number(statusPayload.step_index || 0);
        const totalSteps = Number(statusPayload.total_steps || 0);
        const items = Array.isArray(statusPayload.current_items) ? statusPayload.current_items.filter(Boolean) : [];
        const message = String(statusPayload.message || '').trim();
        const retryText = formatRetryText(statusPayload.retry);

        if (poller.percentEl) {
            poller.percentEl.textContent = `${Math.round(progress)}%`;
        }
        if (poller.barEl) {
            poller.barEl.style.width = `${progress}%`;
            poller.barEl.setAttribute('aria-valuenow', String(Math.round(progress)));
        }
        if (poller.messageEl) {
            poller.messageEl.textContent = message || poller.runningMessage;
        }
        if (poller.metaEl) {
            const stepText = stepIndex > 0 && totalSteps > 0 ? `Step ${stepIndex} / ${totalSteps}` : '';
            const phaseText = phase ? `${phase.charAt(0).toUpperCase()}${phase.slice(1)}` : '';
            poller.metaEl.textContent = [stepText, phaseText].filter(Boolean).join(' • ');
        }
        if (poller.itemsEl) {
            poller.itemsEl.textContent = items.join(' • ');
        }
        if (poller.retryEl) {
            poller.retryEl.textContent = retryText;
        }

        if (status === 'success' && hasData) {
            setAlertClass(poller, 'alert alert-success');
            if (poller.titleEl) {
                poller.titleEl.textContent = poller.completedTitle;
            }
            if (poller.messageEl) {
                poller.messageEl.textContent = message || 'Reloading the report to display the new results.';
            }
            if (poller.barEl) {
                poller.barEl.className = 'progress-bar bg-success';
                poller.barEl.style.width = '100%';
            }
            if (poller.retryEl) {
                poller.retryEl.textContent = '';
            }
            poller.stopped = true;
            window.setTimeout(() => window.location.reload(), 1200);
            return;
        }

        if (status === 'error') {
            setAlertClass(poller, 'alert alert-danger');
            if (poller.titleEl) {
                poller.titleEl.textContent = poller.failedTitle;
            }
            if (poller.barEl) {
                poller.barEl.className = 'progress-bar bg-danger';
            }
            if (poller.retryEl) {
                poller.retryEl.textContent = '';
            }
            poller.stopped = true;
            return;
        }

        if (poller.titleEl) {
            poller.titleEl.textContent = poller.activeTitle;
        }
        setAlertClass(poller, 'alert alert-info');
        if (poller.barEl) {
            poller.barEl.className = 'progress-bar progress-bar-striped progress-bar-animated';
        }
    };

    const poll = async () => {
        if (!pollers.some((poller) => !poller.stopped)) {
            return;
        }

        try {
            const response = await fetch(summaryUrl, { headers: { Accept: 'application/json' }, cache: 'no-store' });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const summary = await response.json();
            pollers.forEach((poller) => {
                if (!poller.stopped) {
                    updateDom(poller, summary);
                }
            });
        } catch (error) {
            pollers.forEach((poller) => {
                if (!poller.stopped && poller.messageEl) {
                    poller.messageEl.textContent = poller.waitingMessage;
                }
            });
        }

        if (pollers.some((poller) => !poller.stopped)) {
            window.setTimeout(poll, 3500);
        }
    };

    window.setTimeout(poll, 1500);
})();
</script>
@endif
@endsection
