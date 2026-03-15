@extends('layouts.app')

@section('title', __('predict.title'))
@section('page-title', __('predict.title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('user.dashboard') }}">{{ __('predict.breadcrumb_dashboard') }}</a></li>
    <li class="breadcrumb-item active">{{ __('predict.breadcrumb_predict') }}</li>
@endsection

@section('sidebar')
    <x-navigation.user-sidebar />
@endsection

@section('styles')
<link rel="stylesheet" href="{{ asset('css/prediction-form.css') }}">
@endsection

@section('content')
@php
    $featureFields = [
        ['name' => 'ph', 'label' => 'pH', 'icon' => 'bi-droplet', 'min' => 3, 'max' => 8, 'step' => '0.01', 'unit' => '-', 'placeholder' => 'e.g. 6.5'],
        ['name' => 'vss', 'label' => 'VSS', 'icon' => 'bi-bar-chart', 'min' => 0, 'max' => 10000, 'step' => '0.1', 'unit' => 'mg/L', 'placeholder' => 'e.g. 3500'],
        ['name' => 'ethanol', 'label' => 'Ethanol', 'icon' => 'bi-beaker', 'min' => 0, 'max' => 100, 'step' => '0.01', 'unit' => 'mM', 'placeholder' => 'e.g. 12.5'],
        ['name' => 'acetate', 'label' => 'Acetate', 'icon' => 'bi-beaker', 'min' => 0, 'max' => 200, 'step' => '0.01', 'unit' => 'mM', 'placeholder' => 'e.g. 25'],
        ['name' => 'propionate', 'label' => 'Propionate', 'icon' => 'bi-beaker', 'min' => 0, 'max' => 100, 'step' => '0.01', 'unit' => 'mM', 'placeholder' => 'e.g. 8'],
        ['name' => 'butyrate', 'label' => 'Butyrate', 'icon' => 'bi-beaker', 'min' => 0, 'max' => 200, 'step' => '0.01', 'unit' => 'mM', 'placeholder' => 'e.g. 35'],
        ['name' => 'sucrose_degradation', 'label' => 'Sucrose Degradation', 'icon' => 'bi-percent', 'min' => 0, 'max' => 100, 'step' => '0.01', 'unit' => '%', 'placeholder' => 'e.g. 72'],
        ['name' => 'orp_mid', 'label' => 'ORP Mid', 'icon' => 'bi-activity', 'min' => -500, 'max' => 100, 'step' => '0.1', 'unit' => 'mV', 'placeholder' => 'e.g. -180'],
        ['name' => 'orp_low', 'label' => 'ORP Low', 'icon' => 'bi-activity', 'min' => -500, 'max' => 100, 'step' => '0.1', 'unit' => 'mV', 'placeholder' => 'e.g. -220'],
        ['name' => 'vfa', 'label' => 'VFA', 'icon' => 'bi-graph-up', 'min' => 0, 'max' => 500, 'step' => '0.01', 'unit' => 'mM', 'placeholder' => 'e.g. 90'],
        ['name' => 'cod_o', 'label' => 'COD-O', 'icon' => 'bi-speedometer2', 'min' => 0, 'max' => 50000, 'step' => '1', 'unit' => 'mg/L', 'placeholder' => 'e.g. 12000'],
    ];
@endphp
<div class="prediction-form-container">
<div class="loading-overlay" id="loadingOverlay">
    <div class="spinner"></div>
</div>

<div class="row">
    <div class="col-lg-8">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">
                    <i class="bi bi-calculator me-2"></i>
                    Hydrogen Production Rate Prediction
                </h3>
            </div>
            <div class="card-body">
                <form id="predictionForm">
                    @csrf

                    <div class="form-group">
                        <label for="ml_model_id" class="form-label">
                            <i class="bi bi-cpu me-1"></i>
                            AI Model
                        </label>
                        <select class="form-control" id="ml_model_id" name="ml_model_id" required>
                            <option value="">Select a model</option>
                            @foreach($models as $model)
                                <option value="{{ $model->id }}"
                                        data-lib-type="{{ $model->LibType }}"
                                        data-file-size="{{ $model->file_size }}"
                                        data-mlflow-run-id="{{ $model->mlflow_run_id ?? '' }}"
                                        data-has-mlflow="{{ !empty($model->mlflow_run_id) ? 'true' : 'false' }}"
                                        {{ $loop->first ? 'selected' : '' }}>
                                    {{ $model->MLMName }} ({{ ucfirst($model->LibType) }})
                                    @if($model->file_size > 0)
                                        - {{ $model->file_size }}MB
                                    @endif
                                </option>
                            @endforeach
                        </select>

                        <div class="model-info-card" id="selectedModelInfo">
                            <div class="d-flex align-items-center justify-content-between">
                                <div>
                                    <h6 class="mb-1">
                                        <i class="bi bi-robot me-1"></i>
                                        <span id="selectedModelName">-</span>
                                        <span id="mlflowBadge" class="badge bg-info ms-1" style="display: none;">MLflow</span>
                                    </h6>
                                    <small class="text-muted">
                                        Library <span class="model-badge" id="selectedModelBadge">-</span>
                                        | Size <strong id="selectedModelSize">-</strong>
                                    </small>
                                    <div id="mlflowRunInfo" style="display: none;" class="mt-1">
                                        <small class="text-info">
                                            <i class="bi bi-tag me-1"></i>
                                            Run ID: <code id="mlflowRunId" style="font-size: 10px;">-</code>
                                        </small>
                                    </div>
                                </div>
                                <div class="text-end">
                                    <i class="bi bi-check-circle-fill text-success icon-24"></i>
                                </div>
                            </div>
                        </div>
                    </div>

                    @if($models->count() === 0)
                        <div class="no-models-alert">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            <strong>No active model available</strong>
                            <p class="mb-0 mt-2">Please ask admin to activate or train a model first.</p>
                        </div>
                    @endif

                    <div class="row">
                        @foreach($featureFields as $field)
                            <div class="col-md-6">
                                <div class="form-group">
                                    <label for="{{ $field['name'] }}" class="form-label">
                                        <i class="bi {{ $field['icon'] }} me-1"></i>
                                        {{ $field['label'] }}
                                    </label>
                                    <input
                                        type="number"
                                        class="form-control"
                                        id="{{ $field['name'] }}"
                                        name="{{ $field['name'] }}"
                                        min="{{ $field['min'] }}"
                                        max="{{ $field['max'] }}"
                                        step="{{ $field['step'] }}"
                                        placeholder="{{ $field['placeholder'] }}"
                                        required
                                    >
                                    <small class="form-text text-muted">Range: {{ $field['min'] }} to {{ $field['max'] }} {{ $field['unit'] }}</small>
                                </div>
                            </div>
                        @endforeach
                    </div>

                    <div class="form-group mt-4">
                        <button type="submit" class="btn btn-primary btn-predict w-100"
                                id="predictButton" {{ $models->count() === 0 ? 'disabled' : '' }}>
                            <i class="bi bi-calculator me-2"></i>
                            Predict HPR
                        </button>
                    </div>
                </form>

                <div id="predictionResult" class="mt-4 prediction-result-hidden"></div>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="card guidelines-card">
            <div class="card-header">
                <h3 class="card-title">
                    <i class="bi bi-info-circle me-2"></i>
                    Parameter Guidelines
                </h3>
            </div>
            <div class="card-body">
                <div class="parameter-item mb-3">
                    <h6 class="mb-2">
                        <i class="bi bi-lightbulb me-1"></i>
                        Notes
                    </h6>
                    <p class="mb-0 small">
                        Fill all 11 biochemical inputs and select one active model.
                        The output is predicted Hydrogen Production Rate (HPR).
                    </p>
                </div>

                @foreach($featureFields as $field)
                    <div class="parameter-item">
                        <h6 class="mb-2">
                            <i class="bi {{ $field['icon'] }} me-1"></i>
                            {{ $field['label'] }}
                        </h6>
                        <p class="mb-0 small">
                            <strong>Range:</strong> {{ $field['min'] }} to {{ $field['max'] }} {{ $field['unit'] }}
                        </p>
                    </div>
                @endforeach
            </div>
        </div>
    </div>
</div>
</div>
@endsection

@section('scripts')
<script src="{{ asset('js/prediction-form-config.js') }}"></script>
<script src="{{ asset('js/prediction-form.js') }}"></script>
<script src="{{ asset('js/user-prediction.js') }}"></script>
<script>
window.PredictionFormConfig.register('user-predict', {
    submitUrl: '{{ route('user.predict.make') }}',
    csrfToken: '{{ csrf_token() }}',
    userType: 'user'
});
</script>
@endsection
