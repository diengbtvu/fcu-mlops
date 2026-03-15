@extends('layouts.app')

@section('title', __('models.machine_learning_models') . ' - Training Report')
@section('page-title', 'Model Training Report')

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.models') }}">{{ __('nav.models') }}</a></li>
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
    $selectedMetrics = is_array($summary['selected_model_metrics'] ?? null) ? $summary['selected_model_metrics'] : [];
    $benchmarkRows = is_array($summary['benchmark_models'] ?? null) ? $summary['benchmark_models'] : [];
    $trainedAt = $model->CreatedDate ?? $model->created_at;

    $keyLabels = [
        'summary' => 'Summary JSON',
        'analysis_summary' => 'Analysis Summary TXT',
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
        'gra_ranking' => 'GRA Ranking',
    ];

    $imageKeys = array_values(array_filter($imageKeys ?? [], fn ($key) => isset($reportAssets[$key])));
@endphp

<div class="row">
    <div class="col-12 mb-3">
        <a href="{{ route('admin.models') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {{ __('back') }} {{ __('nav.models') }}
        </a>
    </div>
</div>

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
            </div>
        </div>
    </div>
</div>

@if($summaryError)
    <div class="alert alert-warning">
        <i class="bi bi-exclamation-triangle"></i> {{ $summaryError }}
    </div>
@endif

<div class="card mb-3">
    <div class="card-header bg-info text-white">
        <strong><i class="bi bi-files"></i> Report Files</strong>
    </div>
    <div class="card-body">
        @if(empty($reportAssets))
            <div class="text-muted">No report artifacts found for this model.</div>
        @else
            @foreach($reportAssets as $key => $asset)
                <a href="{{ $asset['url'] }}" target="_blank" rel="noopener" class="btn btn-outline-primary btn-sm me-2 mb-2">
                    {{ $keyLabels[$key] ?? $key }}
                </a>
            @endforeach
        @endif
    </div>
</div>

@if(!empty($imageKeys))
    <div class="card mb-3">
        <div class="card-header bg-dark text-white">
            <strong><i class="bi bi-image"></i> Training Charts</strong>
        </div>
        <div class="card-body">
            <div class="row">
                @foreach($imageKeys as $key)
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
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>
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
        </div>
    </div>
@endif
@endsection

