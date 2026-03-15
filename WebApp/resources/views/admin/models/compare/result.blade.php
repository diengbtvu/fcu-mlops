@extends('layouts.app')

@section('title', __('models.comparison'))
@section('page-title', __('models.comparison'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.models') }}">{{ __('nav.models') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.models.compare') }}">{{ __('models.compare_models') }}</a></li>
    <li class="breadcrumb-item active">{{ __('models.comparison_result') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('styles')
<style>
    .winner-badge {
        font-size: 0.9rem;
        padding: 0.25rem 0.5rem;
    }
    .metric-card {
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .winner-glow {
        box-shadow: 0 0 20px rgba(40, 167, 69, 0.3);
        border: 2px solid #28a745;
    }
    .comparison-table th {
        background-color: #f8f9fa;
    }
    .better-value {
        color: #28a745;
        font-weight: bold;
    }
    .worse-value {
        color: #dc3545;
        font-weight: bold;
    }
</style>
@endsection

@section('content')
@php
    $hasCompleteData = ($model1->R2Value !== null && $model2->R2Value !== null);
@endphp

@if(!$hasCompleteData)
<div class="row mb-3">
    <div class="col-12">
        <div class="alert alert-warning alert-dismissible fade show" role="alert">
            <h5 class="alert-heading"><i class="bi bi-exclamation-triangle"></i> {{ __('models.incomplete_metrics_title') }}</h5>
            <p class="mb-0">
                {{ __('models.incomplete_metrics') }}
                <br>
                <small class="text-muted">{{ __('models.rmse_calculated_note') }}</small>
            </p>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    </div>
</div>
@endif

<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h3 class="card-title mb-0">
                    <i class="bi bi-trophy"></i> {{ __('models.winner') }}
                </h3>
            </div>
            <div class="card-body text-center">
                @if($comparison['winner'] === 'model1')
                    <div class="alert alert-success">
                        <h2><i class="bi bi-trophy-fill text-warning"></i> {{ $model1->ModelName }}</h2>
                        <p class="mb-0">{{ __('models.won_metrics', ['count' => $comparison['score']['model1']]) }}</p>
                    </div>
                @elseif($comparison['winner'] === 'model2')
                    <div class="alert alert-success">
                        <h2><i class="bi bi-trophy-fill text-warning"></i> {{ $model2->ModelName }}</h2>
                        <p class="mb-0">{{ __('models.won_metrics', ['count' => $comparison['score']['model2']]) }}</p>
                    </div>
                @else
                    <div class="alert alert-info">
                        <h2><i class="bi bi-dash-circle"></i> {{ __('models.tie') }}</h2>
                        <p class="mb-0">{{ __('models.tie_message') }}</p>
                    </div>
                @endif
            </div>
        </div>
    </div>
</div>

<!-- Model Cards -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card metric-card {{ $comparison['winner'] === 'model1' ? 'winner-glow' : '' }}">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">
                    <i class="bi bi-1-circle-fill"></i> {{ $model1->ModelName }}
                    @if($comparison['winner'] === 'model1')
                        <span class="badge bg-warning float-end"><i class="bi bi-trophy-fill"></i> {{ __('models.winner') }}</span>
                    @endif
                </h4>
            </div>
            <div class="card-body">
                <table class="table table-sm">
                    <tr>
                        <th width="40%">{{ __('models.model_type') }}:</th>
                        <td><span class="badge bg-info">{{ strtoupper($model1->LibraryType) }}</span></td>
                    </tr>
                    <tr>
                        <th>{{ __('models.dataset') }}:</th>
                        <td>{{ $model1->dataset->DatasetName ?? 'N/A' }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.trained_by') }}:</th>
                        <td>{{ $model1->trainer->FullName ?? 'N/A' }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.trained_date') }}:</th>
                        <td>{{ $model1->TrainedDate ? $model1->TrainedDate->format('Y-m-d H:i:s') : 'N/A' }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('status') }}:</th>
                        <td>
                            @if($model1->IsActive)
                                <span class="badge bg-success">{{ __('active') }}</span>
                            @else
                                <span class="badge bg-secondary">{{ __('inactive') }}</span>
                            @endif
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card metric-card {{ $comparison['winner'] === 'model2' ? 'winner-glow' : '' }}">
            <div class="card-header bg-success text-white">
                <h4 class="mb-0">
                    <i class="bi bi-2-circle-fill"></i> {{ $model2->ModelName }}
                    @if($comparison['winner'] === 'model2')
                        <span class="badge bg-warning float-end"><i class="bi bi-trophy-fill"></i> {{ __('models.winner') }}</span>
                    @endif
                </h4>
            </div>
            <div class="card-body">
                <table class="table table-sm">
                    <tr>
                        <th width="40%">{{ __('models.model_type') }}:</th>
                        <td><span class="badge bg-info">{{ strtoupper($model2->LibraryType) }}</span></td>
                    </tr>
                    <tr>
                        <th>{{ __('models.dataset') }}:</th>
                        <td>{{ $model2->dataset->DatasetName ?? 'N/A' }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.trained_by') }}:</th>
                        <td>{{ $model2->trainer->FullName ?? 'N/A' }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('models.trained_date') }}:</th>
                        <td>{{ $model2->TrainedDate ? $model2->TrainedDate->format('Y-m-d H:i:s') : 'N/A' }}</td>
                    </tr>
                    <tr>
                        <th>{{ __('status') }}:</th>
                        <td>
                            @if($model2->IsActive)
                                <span class="badge bg-success">{{ __('active') }}</span>
                            @else
                                <span class="badge bg-secondary">{{ __('inactive') }}</span>
                            @endif
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Metrics Comparison Table -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h4 class="card-title mb-0">
                    <i class="bi bi-graph-up"></i> {{ __('models.metrics_comparison') }}
                </h4>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-bordered comparison-table">
                        <thead class="table-light">
                            <tr>
                                <th width="20%">{{ __('models.metric') }}</th>
                                <th width="25%" class="text-center bg-primary text-white">{{ $model1->ModelName }}</th>
                                <th width="25%" class="text-center bg-success text-white">{{ $model2->ModelName }}</th>
                                <th width="15%" class="text-center">{{ __('models.difference') }}</th>
                                <th width="15%" class="text-center">{{ __('models.winner') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            @foreach(['R2' => __('models.r2_score'), 'RMSE' => __('models.rmse'), 'MAE' => __('models.mae'), 'MSE' => __('models.mse')] as $metric => $label)
                                <tr>
                                    <td><strong>{{ $label }}</strong></td>
                                    <td class="text-center {{ $comparison['metrics'][$metric]['winner'] === 'model1' ? 'better-value' : ($comparison['metrics'][$metric]['winner'] === 'model2' ? 'worse-value' : '') }}">
                                        {{ number_format($comparison['metrics'][$metric]['model1'], 4) }}
                                        @if($comparison['metrics'][$metric]['winner'] === 'model1')
                                            <i class="bi bi-check-circle-fill text-success"></i>
                                        @endif
                                    </td>
                                    <td class="text-center {{ $comparison['metrics'][$metric]['winner'] === 'model2' ? 'better-value' : ($comparison['metrics'][$metric]['winner'] === 'model1' ? 'worse-value' : '') }}">
                                        {{ number_format($comparison['metrics'][$metric]['model2'], 4) }}
                                        @if($comparison['metrics'][$metric]['winner'] === 'model2')
                                            <i class="bi bi-check-circle-fill text-success"></i>
                                        @endif
                                    </td>
                                    <td class="text-center">
                                        {{ number_format($comparison['metrics'][$metric]['difference'], 4) }}
                                        <br>
                                        <small class="text-muted">({{ number_format(abs($comparison['metrics'][$metric]['percentage']), 2) }}%)</small>
                                    </td>
                                    <td class="text-center">
                                        @if($comparison['metrics'][$metric]['winner'] === 'model1')
                                            <span class="badge bg-primary">{{ __('models.model') }} 1</span>
                                        @elseif($comparison['metrics'][$metric]['winner'] === 'model2')
                                            <span class="badge bg-success">{{ __('models.model') }} 2</span>
                                        @else
                                            <span class="badge bg-secondary">{{ __('models.tie') }}</span>
                                        @endif
                                    </td>
                                </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Charts -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="bi bi-bar-chart"></i> {{ __('models.metrics_chart') }}
                </h5>
            </div>
            <div class="card-body">
                <canvas id="metricsChart" height="300"></canvas>
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="bi bi-pie-chart"></i> {{ __('models.score_distribution') }}
                </h5>
            </div>
            <div class="card-body">
                <canvas id="scoreChart" height="300"></canvas>
            </div>
        </div>
    </div>
</div>

<!-- Recommendations -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-info text-white">
                <h4 class="card-title mb-0">
                    <i class="bi bi-lightbulb"></i> {{ __('models.recommendations') }}
                </h4>
            </div>
            <div class="card-body">
                @if($comparison['winner'] === 'model1')
                    <div class="alert alert-success">
                        <h5><i class="bi bi-check-circle"></i> {{ __('models.recommended_model') }}: {{ $model1->ModelName }}</h5>
                        <p>{{ __('models.better_performance_with') }}:</p>
                        <ul>
                            @foreach($comparison['metrics'] as $metric => $data)
                                @if($data['winner'] === 'model1')
                                    <li>{{ __('models.better') }} {{ $metric }}: {{ number_format($data['model1'], 4) }} {{ __('vs') }} {{ number_format($data['model2'], 4) }}</li>
                                @endif
                            @endforeach
                        </ul>
                    </div>
                @elseif($comparison['winner'] === 'model2')
                    <div class="alert alert-success">
                        <h5><i class="bi bi-check-circle"></i> {{ __('models.recommended_model') }}: {{ $model2->ModelName }}</h5>
                        <p>{{ __('models.better_performance_with') }}:</p>
                        <ul>
                            @foreach($comparison['metrics'] as $metric => $data)
                                @if($data['winner'] === 'model2')
                                    <li>{{ __('models.better') }} {{ $metric }}: {{ number_format($data['model2'], 4) }} {{ __('vs') }} {{ number_format($data['model1'], 4) }}</li>
                                @endif
                            @endforeach
                        </ul>
                    </div>
                @else
                    <div class="alert alert-info">
                        <h5><i class="bi bi-info-circle"></i> {{ __('models.similar_performance') }}</h5>
                        <p>{{ __('models.consider_factors') }}:</p>
                        <ul>
                            <li>{{ __('models.factor_training_time') }}</li>
                            <li>{{ __('models.factor_complexity') }}</li>
                            <li>{{ __('models.factor_deployment') }}</li>
                            <li>{{ __('models.factor_dataset') }}</li>
                        </ul>
                    </div>
                @endif

                <div class="mt-3">
                    <h6>{{ __('models.general_tips') }}:</h6>
                    <ul>
                        <li><strong>{{ __('models.r2_score') }}:</strong> {{ __('models.r2_tip') }}</li>
                        <li><strong>{{ __('models.rmse_mae_mse') }}:</strong> {{ __('models.error_metrics_tip') }}</li>
                        <li><strong>{{ __('models.small_differences') }}:</strong> {{ __('models.small_diff_tip') }}</li>
                        <li><strong>{{ __('models.dataset') }}:</strong> {{ __('models.dataset_tip') }}</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Actions -->
<div class="row">
    <div class="col-12 text-center">
        <a href="{{ route('admin.models.compare') }}" class="btn btn-primary">
            <i class="bi bi-arrow-repeat"></i> {{ __('models.compare_other_models') }}
        </a>
        <a href="{{ route('admin.models') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {{ __('back') }} {{ __('nav.models') }}
        </a>
        @if($comparison['winner'] === 'model1')
            <a href="{{ route('admin.models.edit', $model1->id) }}" class="btn btn-success">
                <i class="bi bi-gear"></i> {{ __('models.configure_winner_btn') }} ({{ $model1->ModelName }})
            </a>
        @elseif($comparison['winner'] === 'model2')
            <a href="{{ route('admin.models.edit', $model2->id) }}" class="btn btn-success">
                <i class="bi bi-gear"></i> {{ __('models.configure_winner_btn') }} ({{ $model2->ModelName }})
            </a>
        @endif
    </div>
</div>
@endsection

@section('scripts')
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Prepare data from PHP
    const comparisonData = {!! json_encode([
        'model1' => [
            'name' => $model1->ModelName,
            'r2' => $comparison['metrics']['R2']['model1'] ?? 0,
            'rmse' => $comparison['metrics']['RMSE']['model1'] ?? 0,
            'mae' => $comparison['metrics']['MAE']['model1'] ?? 0,
            'mse' => $comparison['metrics']['MSE']['model1'] ?? 0,
            'score' => $comparison['score']['model1'] ?? 0
        ],
        'model2' => [
            'name' => $model2->ModelName,
            'r2' => $comparison['metrics']['R2']['model2'] ?? 0,
            'rmse' => $comparison['metrics']['RMSE']['model2'] ?? 0,
            'mae' => $comparison['metrics']['MAE']['model2'] ?? 0,
            'mse' => $comparison['metrics']['MSE']['model2'] ?? 0,
            'score' => $comparison['score']['model2'] ?? 0
        ]
    ]) !!};

    // Metrics Comparison Chart
    const metricsCtx = document.getElementById('metricsChart').getContext('2d');
    new Chart(metricsCtx, {
        type: 'bar',
        data: {
            labels: ['R² Score', 'RMSE', 'MAE', 'MSE'],
            datasets: [{
                label: comparisonData.model1.name,
                data: [
                    comparisonData.model1.r2,
                    comparisonData.model1.rmse,
                    comparisonData.model1.mae,
                    comparisonData.model1.mse
                ],
                backgroundColor: 'rgba(13, 110, 253, 0.7)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 2
            }, {
                label: comparisonData.model2.name,
                data: [
                    comparisonData.model2.r2,
                    comparisonData.model2.rmse,
                    comparisonData.model2.mae,
                    comparisonData.model2.mse
                ],
                backgroundColor: 'rgba(25, 135, 84, 0.7)',
                borderColor: 'rgba(25, 135, 84, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: '{{ __('models.side_by_side_comparison') }}'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Score Distribution Chart
    const scoreCtx = document.getElementById('scoreChart').getContext('2d');
    new Chart(scoreCtx, {
        type: 'doughnut',
        data: {
            labels: [comparisonData.model1.name, comparisonData.model2.name],
            datasets: [{
                data: [
                    comparisonData.model1.score,
                    comparisonData.model2.score
                ],
                backgroundColor: [
                    'rgba(13, 110, 253, 0.7)',
                    'rgba(25, 135, 84, 0.7)'
                ],
                borderColor: [
                    'rgba(13, 110, 253, 1)',
                    'rgba(25, 135, 84, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                title: {
                    display: true,
                    text: '{{ __('models.metrics_won_out_of_4') }}'
                }
            }
        }
    });
});
</script>
@endsection
