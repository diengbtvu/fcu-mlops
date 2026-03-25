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
    $featureFields = config('prediction.features', []);
    $fieldTranslations = [
        'ph' => ['label' => 'predict.ph', 'placeholder' => 'predict.ph_placeholder'],
        'vss' => ['label' => 'predict.vss', 'placeholder' => 'predict.vss_placeholder'],
        'ethanol' => ['label' => 'predict.ethanol', 'placeholder' => 'predict.ethanol_placeholder'],
        'acetate' => ['label' => 'predict.acetate', 'placeholder' => 'predict.acetate_placeholder'],
        'propionate' => ['label' => 'predict.propionate', 'placeholder' => 'predict.propionate_placeholder'],
        'butyrate' => ['label' => 'predict.butyrate', 'placeholder' => 'predict.butyrate_placeholder'],
        'sucrose_degradation' => ['label' => 'predict.sucrose_degradation', 'placeholder' => 'predict.sucrose_degradation_placeholder'],
        'orp_mid' => ['label' => 'predict.orp_mid', 'placeholder' => 'predict.orp_mid_placeholder'],
        'orp_low' => ['label' => 'predict.orp_low', 'placeholder' => 'predict.orp_low_placeholder'],
        'vfa' => ['label' => 'predict.vfa', 'placeholder' => 'predict.vfa_placeholder'],
        'cod_o' => ['label' => 'predict.cod_o', 'placeholder' => 'predict.cod_o_placeholder'],
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
                    {{ __('predict.page_title') }}
                </h3>
            </div>
            <div class="card-body">
                <form id="predictionForm">
                    @csrf

                    <div class="form-group">
                        <label for="ml_model_id" class="form-label">
                            <i class="bi bi-cpu me-1"></i>
                            {{ __('predict.ai_model') }}
                        </label>
                        <select class="form-control" id="ml_model_id" name="ml_model_id" required>
                            <option value="">{{ __('predict.select_model') }}</option>
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
                                        <span id="mlflowBadge" class="badge bg-info ms-1" style="display: none;">{{ __('predict.mlflow_badge') }}</span>
                                    </h6>
                                    <small class="text-muted">
                                        {{ __('predict.library') }} <span class="model-badge" id="selectedModelBadge">-</span>
                                        | {{ __('predict.size') }} <strong id="selectedModelSize">-</strong>
                                    </small>
                                    <div id="mlflowRunInfo" style="display: none;" class="mt-1">
                                        <small class="text-info">
                                            <i class="bi bi-tag me-1"></i>
                                            {{ __('predict.run_id') }} <code id="mlflowRunId" style="font-size: 10px;">-</code>
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
                            <strong>{{ __('predict.no_models_alert_title') }}</strong>
                            <p class="mb-0 mt-2">{{ __('predict.no_models_alert_desc_user') }}</p>
                        </div>
                    @endif

                    <div class="row">
                        @foreach($featureFields as $fieldName => $field)
                            @php
                                $translationKeys = $fieldTranslations[$fieldName] ?? [];
                                $labelKey = $translationKeys['label'] ?? null;
                                $placeholderKey = $translationKeys['placeholder'] ?? null;
                                $translatedLabel = $labelKey ? __($labelKey) : $field['label'];
                                $translatedPlaceholder = $placeholderKey ? __($placeholderKey) : $field['placeholder'];
                                if ($labelKey && $translatedLabel === $labelKey) {
                                    $translatedLabel = $field['label'];
                                }
                                if ($placeholderKey && $translatedPlaceholder === $placeholderKey) {
                                    $translatedPlaceholder = $field['placeholder'];
                                }
                            @endphp
                            <div class="col-md-6">
                                <div class="form-group">
                                    <label for="{{ $fieldName }}" class="form-label">
                                        <i class="bi {{ $field['icon'] }} me-1"></i>
                                        {{ $translatedLabel }}
                                    </label>
                                    <input
                                        type="number"
                                        class="form-control"
                                        id="{{ $fieldName }}"
                                        name="{{ $fieldName }}"
                                        min="{{ $field['min'] }}"
                                        max="{{ $field['max'] }}"
                                        step="{{ $field['step'] }}"
                                        data-label="{{ $translatedLabel }}"
                                        placeholder="{{ $translatedPlaceholder }}"
                                        required
                                    >
                                    <small class="form-text text-muted">
                                        {{ __('predict.range') }}
                                        {{ __('predict.range_value', ['min' => $field['min'], 'max' => $field['max'], 'unit' => $field['unit']]) }}
                                    </small>
                                </div>
                            </div>
                        @endforeach
                    </div>

                    <div class="form-group mt-4">
                        <button type="submit" class="btn btn-primary btn-predict w-100"
                                id="predictButton" {{ $models->count() === 0 ? 'disabled' : '' }}>
                            <i class="bi bi-calculator me-2"></i>
                            {{ __('predict.predict_button') }}
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
                    {{ __('predict.parameter_guidelines') }}
                </h3>
            </div>
            <div class="card-body">
                <div class="parameter-item mb-3">
                    <h6 class="mb-2">
                        <i class="bi bi-lightbulb me-1"></i>
                        {{ __('predict.notes') }}
                    </h6>
                    <p class="mb-0 small">
                        {{ __('predict.user_notes_text') }}
                    </p>
                </div>

                @foreach($featureFields as $fieldName => $field)
                    @php
                        $translationKeys = $fieldTranslations[$fieldName] ?? [];
                        $labelKey = $translationKeys['label'] ?? null;
                        $translatedLabel = $labelKey ? __($labelKey) : $field['label'];
                        if ($labelKey && $translatedLabel === $labelKey) {
                            $translatedLabel = $field['label'];
                        }
                    @endphp
                    <div class="parameter-item">
                        <h6 class="mb-2">
                            <i class="bi {{ $field['icon'] }} me-1"></i>
                            {{ $translatedLabel }}
                        </h6>
                        <p class="mb-0 small">
                            <strong>{{ __('predict.range') }}</strong>
                            {{ __('predict.range_value', ['min' => $field['min'], 'max' => $field['max'], 'unit' => $field['unit']]) }}
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
    userType: 'user',
    defaultSubmitLabel: @json(__('predict.predict_button')),
    processingLabel: @json(__('predict.processing')),
    messages: @json([
        'selectModelError' => __('predict.error_select_model'),
        'fieldRequired' => __('predict.error_required'),
        'fieldBetween' => __('predict.error_between'),
        'predictionResultTitle' => __('predict.prediction_result_title'),
        'hydrogenProductionRate' => __('predict.hydrogen_production_rate'),
        'predictionCompletedUsing' => __('predict.prediction_completed_using'),
        'predictionUsing' => __('predict.prediction_using'),
        'aiModelFallback' => __('predict.ai_model_fallback'),
        'adminAccess' => __('predict.admin_access'),
        'userAccess' => __('predict.user_access'),
        'mlflowRun' => __('predict.mlflow_run'),
        'errorTitle' => __('predict.error_title'),
        'unknownError' => __('predict.unknown_error'),
        'unknownSize' => __('predict.unknown_size'),
    ])
});
</script>
@endsection
