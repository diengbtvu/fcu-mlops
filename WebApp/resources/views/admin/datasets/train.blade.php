@extends('layouts.app')

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('content')
@php
    $routePrefix = auth()->user()->role_id == 1 ? 'admin' : 'user';
@endphp
<div class="container mt-4">
    <div class="row">
        <div class="col-md-12">
            <h2 class="mb-4">
                <i class="bi bi-cpu"></i> {{ __('datasets.train_ml_model') }}
            </h2>

            <!-- Breadcrumb -->
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ route($routePrefix . '.dashboard') }}">{{ __('dashboard.title') }}</a></li>
                    <li class="breadcrumb-item"><a href="{{ route($routePrefix . '.datasets.index') }}">{{ __('nav.datasets') }}</a></li>
                    <li class="breadcrumb-item active">{{ __('datasets.train_model') }}</li>
                </ol>
            </nav>

            <!-- Dataset Info Card -->
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0"><i class="bi bi-database"></i> {{ __('datasets.dataset_information') }}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>{{ __('datasets.dataset_name') }}:</strong> {{ $dataset->DatasetName }}</p>
                            <p><strong>{{ __('datasets.description') }}:</strong> {{ $dataset->Description ?? __('models.na') }}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>{{ __('datasets.uploaded_by') }}:</strong> {{ $dataset->user->FullName ?? __('datasets.unknown_user') }}</p>
                            <p><strong>{{ __('datasets.upload_date') }}:</strong> {{ $dataset->UploadDate }}</p>
                            <p><strong>{{ __('datasets.file_path') }}:</strong> <code>{{ $dataset->FilePath }}</code></p>
                            <p><strong>Selected sheet:</strong> {{ $dataset->SelectedSheet ?: 'CSV / default sheet' }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Training Configuration Form -->
            <div class="card mb-4">
                <div class="card-header bg-success text-white">
                    <h5 class="mb-0"><i class="bi bi-gear"></i> {{ __('datasets.training_configuration') }}</h5>
                </div>
                <div class="card-body">
                    <form id="trainingForm" action="{{ route($routePrefix . '.datasets.train', $dataset->DatasetId) }}" method="POST">
                        @csrf

                        <!-- Model Type Selection -->
                        <div class="row mb-4">
                            <div class="col-md-12">
                                <label class="form-label fw-bold">{{ __('datasets.model_type_required') }}</label>
                                <select name="model_type" id="model_type" class="form-select" required>
                                    <option value="random_forest" selected>Random Forest (RF)</option>
                                    <option value="xgboost">XGBoost</option>
                                    <option value="svm">Support Vector Machine (SVM)</option>
                                    <option value="knn">K-Nearest Neighbors (KNN)</option>
                                    <option value="decision_tree">Decision Tree (DT)</option>
                                </select>
                                <small class="text-muted">
                                    Paper models: <strong>SVM</strong> | <strong>DT</strong> | <strong>RF</strong> | <strong>KNN</strong> | <strong>XGBoost</strong>
                                </small>
                            </div>
                        </div>

                        <!-- Training Method & Model Name -->
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label class="form-label fw-bold">{{ __('datasets.training_scope') }}</label>
                                <select name="training_scope" id="training_scope" class="form-select">
                                    <option value="single_model">{{ __('datasets.training_scope_single') }}</option>
                                    <option value="all_models_compare" selected>{{ __('datasets.training_scope_compare') }}</option>
                                </select>
                                <small class="text-muted">{{ __('datasets.training_scope_note') }}</small>
                            </div>

                            <div class="col-md-4">
                                <label class="form-label fw-bold">{{ __('datasets.training_method') }}</label>
                                <select name="training_method" id="training_method" class="form-select">
                                    <option value="process">{{ __('datasets.training_method_process') }}</option>
                                    <option value="api" selected>{{ __('datasets.training_method_api') }}</option>
                                </select>
                                <small class="text-muted">{{ __('datasets.training_method_api_note') }}</small>
                            </div>

                            <div class="col-md-4">
                                <label class="form-label fw-bold">{{ __('datasets.model_name_optional') }}</label>
                                <input type="text" name="model_name" id="model_name" class="form-control" 
                                       placeholder="{{ __('datasets.auto_generated') }}"
                                       value="Model_{{ $dataset->DatasetName }}_{{ date('Ymd') }}">
                            </div>
                        </div>

                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label for="llm_provider" class="form-label fw-bold">AI provider</label>
                                <select name="llm_provider" id="llm_provider" class="form-select">
                                    <option value="groq" selected>Groq API</option>
                                </select>
                                <small class="text-muted">Docker deployment uses Groq only.</small>
                            </div>

                            <div class="col-md-8">
                                <label for="llm_model" class="form-label fw-bold">AI model for explanations and benchmark</label>
                                <select name="llm_model" id="llm_model" class="form-select"></select>
                                <small class="text-muted">Used for AI report explanations and Arm A/B/C benchmark generation.</small>
                            </div>
                        </div>

                        <!-- Hyperparameters -->
                        <h6 class="border-bottom pb-2 mb-3">{{ __('datasets.hyperparameters') }}</h6>
                        
                        <!-- Random Forest / XGBoost / Decision Tree Parameters -->
                        <div id="tree_params" class="hyperparameter-group">
                            <div class="row mb-3">
                                <div class="col-md-4" id="n_estimators_group">
                                    <label for="n_estimators" class="form-label">{{ __('datasets.n_estimators') }}</label>
                                    <input type="number" name="n_estimators" id="n_estimators" 
                                           class="form-control" value="100" min="10" max="1000">
                                    <small class="text-muted">{{ __('datasets.default') }}: 100</small>
                                </div>

                                <div class="col-md-4">
                                    <label for="max_depth" class="form-label">{{ __('datasets.max_depth') }}</label>
                                    <input type="number" name="max_depth" id="max_depth" 
                                           class="form-control" placeholder="None (unlimited)" min="1" max="50">
                                    <small class="text-muted">{{ __('datasets.max_depth_unlimited') }}</small>
                                </div>

                                <div class="col-md-4" id="learning_rate_group">
                                    <label for="learning_rate" class="form-label">{{ __('datasets.learning_rate') }} <span class="xgboost-only text-muted">({{ __('datasets.xgboost_only') }})</span></label>
                                    <input type="number" name="learning_rate" id="learning_rate" 
                                           class="form-control" value="0.1" min="0.001" max="1" step="0.01" disabled>
                                    <small class="text-muted">{{ __('datasets.default') }}: 0.1</small>
                                </div>
                            </div>
                        </div>

                        <!-- SVM Parameters -->
                        <div id="svm_params" class="hyperparameter-group" style="display: none;">
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="C" class="form-label">C</label>
                                    <input type="number" name="C" id="C" class="form-control" value="1.0" min="0.0001" max="1000" step="0.1">
                                    <small class="text-muted">{{ __('datasets.default') }}: 1.0</small>
                                </div>

                                <div class="col-md-4">
                                    <label for="gamma" class="form-label">Gamma</label>
                                    <select name="gamma" id="gamma" class="form-select">
                                        <option value="scale" selected>scale</option>
                                        <option value="auto">auto</option>
                                    </select>
                                    <small class="text-muted">{{ __('datasets.default') }}: scale</small>
                                </div>

                                <div class="col-md-4">
                                    <label for="kernel" class="form-label">Kernel</label>
                                    <select name="kernel" id="kernel" class="form-select">
                                        <option value="rbf" selected>rbf</option>
                                        <option value="linear">linear</option>
                                        <option value="poly">poly</option>
                                        <option value="sigmoid">sigmoid</option>
                                    </select>
                                    <small class="text-muted">{{ __('datasets.default') }}: rbf</small>
                                </div>
                            </div>
                        </div>

                        <!-- KNN Parameters -->
                        <div id="knn_params" class="hyperparameter-group" style="display: none;">
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="n_neighbors" class="form-label">n_neighbors</label>
                                    <input type="number" name="n_neighbors" id="n_neighbors" 
                                           class="form-control" value="5" min="1" max="100">
                                    <small class="text-muted">{{ __('datasets.default') }}: 5</small>
                                </div>
                            </div>
                        </div>

                        <!-- Common Parameters -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label for="test_size" class="form-label">{{ __('datasets.test_size') }}</label>
                                <input type="number" name="test_size" id="test_size" 
                                       class="form-control" value="20" min="10" max="50" step="5">
                                <small class="text-muted">{{ __('datasets.default') }}: 20%</small>
                            </div>

                            <div class="col-md-6">
                                <label for="random_state" class="form-label">{{ __('datasets.random_state') }}</label>
                                <input type="number" name="random_state" id="random_state" 
                                       class="form-control" value="42" min="0">
                                <small class="text-muted">{{ __('datasets.random_state_desc') }}</small>
                            </div>
                        </div>

                        <!-- Action Buttons -->
                        <div class="d-flex justify-content-between align-items-center mt-4">
                            <a href="{{ route($routePrefix . '.datasets.index') }}" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> {{ __('datasets.back_to_datasets') }}
                            </a>
                            
                            <div>
                                <!-- <button type="button" class="btn btn-outline-primary me-2" id="validateBtn">
                                    <i class="bi bi-check-circle"></i> {{ __('datasets.validate_settings') }}
                                </button> -->
                                <button type="submit" class="btn btn-success" id="trainBtn">
                                    <i class="bi bi-play-circle"></i> {{ __('datasets.start_training') }}
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Training Progress Modal -->
            <div class="modal fade" id="progressModal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-labelledby="progressModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title" id="progressModalLabel">
                                <i class="bi bi-hourglass-split"></i> {{ __('datasets.training_progress') }}
                            </h5>
                        </div>
                        <div class="modal-body">
                            <div class="progress mb-3" style="height: 35px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated bg-info" 
                                     role="progressbar" style="width: 0%" id="progressBar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                    <strong style="font-size: 1.1em;">0%</strong>
                                </div>
                            </div>
                            <div id="progressMessage" class="text-center mb-3">
                                <h6 class="mb-0">{{ __('datasets.initializing_training') }}</h6>
                            </div>
                            <div class="card">
                                <div class="card-header bg-light">
                                    <strong><i class="bi bi-terminal"></i> {{ __('datasets.training_logs') }}</strong>
                                </div>
                                <div class="card-body p-2" id="trainingLog" style="max-height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.85em; background-color: #1e1e1e; color: #d4d4d4;">
                                    <div style="color: #858585;">⏳ {{ __('datasets.waiting_to_start') }}</div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <small class="text-muted me-auto">
                                <i class="bi bi-info-circle"></i> {{ __('datasets.do_not_close') }}
                            </small>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>
</div>
@endsection

@section('scripts')
<script>
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎬 Training page JavaScript loaded!');
    
    const form = document.getElementById('trainingForm');
    const trainBtn = document.getElementById('trainBtn');
    const modelTypeSelect = document.getElementById('model_type');
    const trainingScopeSelect = document.getElementById('training_scope');
    const modelNameInput = document.getElementById('model_name');
    const llmProviderSelect = document.getElementById('llm_provider');
    const llmModelSelect = document.getElementById('llm_model');
    const treeParams = document.getElementById('tree_params');
    const svmParams = document.getElementById('svm_params');
    const knnParams = document.getElementById('knn_params');
    const nEstimatorsGroup = document.getElementById('n_estimators_group');
    const learningRateGroup = document.getElementById('learning_rate_group');
    const nEstimatorsInput = document.getElementById('n_estimators');
    const maxDepthInput = document.getElementById('max_depth');
    const cInput = document.getElementById('C');
    const gammaInput = document.getElementById('gamma');
    const kernelInput = document.getElementById('kernel');
    const nNeighborsInput = document.getElementById('n_neighbors');
    const learningRateInput = document.getElementById('learning_rate');
    const progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    const trainingLog = document.getElementById('trainingLog');

    console.log('Progress modal:', progressModal);
    console.log('Train button:', trainBtn);

    const PREDICT_SERVICE_URL = '{{ config("services.predict_service.url") }}';
    const PREDICT_SERVICE_PUBLIC_URL = '{{ config("services.predict_service.public_url") }}';
    const DATASETS_INDEX_URL = '{{ route($routePrefix . ".datasets.index", [], false) }}';
    const REPORT_PAGE_TEMPLATE = '{{ route($routePrefix . ".models.report", ["model" => "__MODEL_ID__"], false) }}';
    const TRAINING_PROGRESS_SESSION_URL = '{{ route("training.progress.session", [], false) }}';
    const TRAINING_PROGRESS_URL_TEMPLATE = '{{ route("training.progress.show", ["sessionId" => "__SESSION_ID__"], false) }}';
    const CSRF_TOKEN = '{{ csrf_token() }}';
    
    console.log('PREDICT_SERVICE_URL:', PREDICT_SERVICE_URL);
    console.log('DATASETS_INDEX_URL:', DATASETS_INDEX_URL);

    let sessionId = null;
    let progressInterval = null;

    const llmModelsByProvider = {
        groq: [
            { value: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B' },
            { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B Versatile' }
        ]
    };

    function updateLlmModelOptions() {
        if (!llmProviderSelect || !llmModelSelect) {
            return;
        }
        const provider = llmProviderSelect.value || 'groq';
        const models = llmModelsByProvider[provider] || [];
        llmModelSelect.innerHTML = '';
        models.forEach(function(model) {
            const option = document.createElement('option');
            option.value = model.value;
            option.textContent = model.label;
            llmModelSelect.appendChild(option);
        });
    }

    function buildTrainingProgressUrl(sid) {
        return TRAINING_PROGRESS_URL_TEMPLATE.replace('__SESSION_ID__', encodeURIComponent(String(sid)));
    }

    function summarizeResponseBody(rawBody) {
        return String(rawBody || '')
            .replace(/\s+/g, ' ')
            .trim()
            .slice(0, 240);
    }

    async function readJsonResponse(response, fallbackMessage) {
        const rawBody = await response.text();
        let payload = null;

        if (rawBody.trim()) {
            try {
                payload = JSON.parse(rawBody);
            } catch (error) {
                const preview = summarizeResponseBody(rawBody);
                const invalidMessage = response.ok
                    ? `${fallbackMessage}: server returned a non-JSON response`
                    : (preview || fallbackMessage);
                throw new Error(invalidMessage);
            }
        }

        if (!response.ok) {
            const errorMessage = payload && typeof payload === 'object'
                ? (payload.error || payload.message || '')
                : '';
            throw new Error(String(errorMessage || summarizeResponseBody(rawBody) || fallbackMessage));
        }

        if (!payload || typeof payload !== 'object') {
            throw new Error(`${fallbackMessage}: empty response`);
        }

        return payload;
    }

    function buildReportAssetUrl(reportInfo, filename) {
        const routePrefixRaw = String(reportInfo?.route_prefix || '').trim();
        const routePrefix = routePrefixRaw.startsWith('/') ? routePrefixRaw : `/${routePrefixRaw}`;
        const encodedFile = String(filename || '').split('/').map(encodeURIComponent).join('/');
        return `${routePrefix}/${encodedFile}`;
    }

    function buildReportPageUrl(modelId) {
        if (!modelId) {
            return '';
        }
        return REPORT_PAGE_TEMPLATE.replace('__MODEL_ID__', encodeURIComponent(String(modelId)));
    }

    function renderReportLinks(reportInfo, modelId) {
        if (!reportInfo || !reportInfo.files || typeof reportInfo.files !== 'object') {
            const reportPageUrl = buildReportPageUrl(modelId);
            if (!reportPageUrl) {
                return '';
            }
            return `
                <div class="mt-3 text-start">
                    <div class="fw-bold mb-2">Training Report</div>
                    <a class="btn btn-primary btn-sm me-2 mb-2" href="${reportPageUrl}">Open Full Report</a>
                </div>
            `;
        }

        const labelMap = {
            open_full_report: 'Open Full Report',
            training_bundle_zip: 'Training Bundle ZIP',
            llm_explanations: 'AI Explanations JSON',
            summary: 'Summary',
            best_model_summary: 'Best Model Summary',
            analysis_summary: 'Analysis Report (TXT)',
            results_summary: 'Paper Results Summary',
            table1_incremental_results: 'Incremental Results CSV',
            model_comparison_bars: 'Model Comparison',
            model_comparison_table: 'Comparison CSV',
            predicted_vs_actual: 'Predicted vs Actual',
            residuals: 'Residuals',
            feature_importance: 'Feature Importance',
            feature_importance_table: 'Feature Importance CSV',
            descriptive_statistics: 'Descriptive Stats CSV',
            correlation_matrix: 'Correlation Matrix CSV',
            correlation_heatmap: 'Correlation Heatmap',
            feature_distributions: 'Feature Distributions',
            feature_vs_target: 'Feature vs Target',
            boxplots: 'Boxplots',
            time_series: 'Time Series',
            gra_ranking: 'GRA Ranking'
        };

        const preferredOrder = [
            'open_full_report',
            'training_bundle_zip',
            'summary',
            'best_model_summary',
            'results_summary',
            'analysis_summary',
            'table1_incremental_results',
            'model_comparison_bars',
            'model_comparison_table',
            'predicted_vs_actual',
            'residuals',
            'feature_importance',
            'feature_importance_table',
            'correlation_heatmap',
            'feature_distributions',
            'feature_vs_target',
            'boxplots',
            'time_series',
            'descriptive_statistics',
            'correlation_matrix',
            'gra_ranking'
        ];

        const entries = Object.entries(reportInfo.files);
        const reportPageUrl = buildReportPageUrl(modelId);
        if (reportPageUrl) {
            entries.unshift(['open_full_report', reportPageUrl]);
        }

        const links = entries
        .sort(([keyA], [keyB]) => {
            const idxA = preferredOrder.indexOf(keyA);
            const idxB = preferredOrder.indexOf(keyB);
            const rankA = idxA === -1 ? 999 : idxA;
            const rankB = idxB === -1 ? 999 : idxB;
            return rankA - rankB;
        })
        .map(([key, value]) => {
            const href = key === 'open_full_report'
                ? String(value)
                : buildReportAssetUrl(reportInfo, value);
            const label = labelMap[key] || key;
            return `<a class="btn btn-outline-primary btn-sm me-2 mb-2" href="${href}" target="_blank" rel="noopener">${label}</a>`;
        });

        if (links.length === 0) {
            return '';
        }

        return `
            <div class="mt-3 text-start">
                <div class="fw-bold mb-2">Training Report Files</div>
                ${links.join('')}
            </div>
        `;
    }

    function updateModelUI(modelType) {
        const isTreeModel = ['random_forest', 'xgboost', 'decision_tree', 'dt'].includes(modelType);
        const isSvmModel = modelType === 'svm';
        const isKnnModel = modelType === 'knn';
        const isXgboost = modelType === 'xgboost';
        const isRandomForest = modelType === 'random_forest';

        treeParams.style.display = isTreeModel ? 'block' : 'none';
        svmParams.style.display = isSvmModel ? 'block' : 'none';
        knnParams.style.display = isKnnModel ? 'block' : 'none';

        nEstimatorsGroup.style.display = (isRandomForest || isXgboost) ? 'block' : 'none';
        learningRateGroup.style.display = isXgboost ? 'block' : 'none';

        // Disable hidden model-specific controls to avoid native browser
        // validation errors like "invalid form control is not focusable".
        maxDepthInput.disabled = !isTreeModel;
        nEstimatorsInput.disabled = !(isRandomForest || isXgboost);
        learningRateInput.disabled = !isXgboost;
        cInput.disabled = !isSvmModel;
        gammaInput.disabled = !isSvmModel;
        kernelInput.disabled = !isSvmModel;
        nNeighborsInput.disabled = !isKnnModel;

        // Update model name prefix
        const datasetName = '{{ $dataset->DatasetName }}';
        const date = '{{ date("Ymd") }}';
        let prefix = 'Model';

        if (modelType === 'random_forest') {
            prefix = 'RF';
        } else if (modelType === 'xgboost') {
            prefix = 'XGB';
        } else if (modelType === 'svm') {
            prefix = 'SVM';
        } else if (modelType === 'knn') {
            prefix = 'KNN';
        } else if (modelType === 'decision_tree' || modelType === 'dt') {
            prefix = 'DT';
        }

        modelNameInput.value = `${prefix}_${datasetName}_${date}`;
    }

    // Handle model type change
    modelTypeSelect.addEventListener('change', function() {
        updateModelUI(this.value);
    });
    updateModelUI(modelTypeSelect.value);
    if (llmProviderSelect) {
        llmProviderSelect.addEventListener('change', updateLlmModelOptions);
        updateLlmModelOptions();
    }

    // Function to start progress polling
    function startProgressPolling(sid) {
        progressInterval = setInterval(async function() {
            try {
                const response = await fetch(buildTrainingProgressUrl(sid), {
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await readJsonResponse(response, 'Failed to load training progress');
                
                if (data.success && data.progress) {
                    const progress = data.progress;
                    
                    // Update progress bar
                    const progressPercent = Math.round(progress.progress);
                    progressBar.style.width = progressPercent + '%';
                    progressBar.textContent = progressPercent + '%';
                    
                    // Update message
                    progressMessage.innerHTML = `<p class="mb-0">${progress.message}</p>`;
                    
                    // Add log entry with color coding
                    const logEntry = document.createElement('div');
                    logEntry.style.marginBottom = '4px';
                    logEntry.style.color = '#4EC9B0'; // Cyan color for logs
                    const timestamp = new Date().toLocaleTimeString();
                    logEntry.innerHTML = `<span style="color: #858585;">[${timestamp}]</span> <span style="color: #DCDCAA;">${progress.message}</span>`;
                    trainingLog.appendChild(logEntry);
                    trainingLog.scrollTop = trainingLog.scrollHeight;
                    
                    // Check if completed or failed
                    if (progress.status === 'completed') {
                        clearInterval(progressInterval);
                        progressBar.classList.remove('progress-bar-animated', 'bg-info');
                        progressBar.classList.add('bg-success');
                        
                        const resultPayload = progress.result || {};
                        const reportInfo = resultPayload.report_info || null;
                        const reportLinksHtml = renderReportLinks(reportInfo, resultPayload.database_id || null);
                        const hasReport = Boolean(reportLinksHtml);
                        const redirectDelay = hasReport ? 12000 : 3000;

                        progressMessage.innerHTML = `
                            <h6 class="mb-0 text-success"><i class="bi bi-check-circle"></i> Training completed successfully!</h6>
                            ${reportLinksHtml}
                            <div class="mt-2 small text-muted">
                                Redirecting to datasets page in ${Math.round(redirectDelay / 1000)} seconds...
                            </div>
                        `;
                        
                        setTimeout(function() {
                            progressModal.hide();
                            window.location.href = DATASETS_INDEX_URL;
                        }, redirectDelay);
                    } else if (progress.status === 'failed') {
                        clearInterval(progressInterval);
                        progressBar.classList.remove('progress-bar-animated', 'bg-info');
                        progressBar.classList.add('bg-danger');
                        progressMessage.innerHTML = `<h6 class="mb-0 text-danger"><i class="bi bi-x-circle"></i> ${progress.error || 'Training failed'}</h6>`;
                        
                        trainBtn.disabled = false;
                        trainBtn.innerHTML = '<i class="bi bi-play-circle"></i> Start Training';
                        
                        setTimeout(function() {
                            progressModal.hide();
                        }, 5000);
                    }
                }
            } catch (error) {
                console.error('Error fetching progress:', error);
            }
        }, 1000); // Poll every 1 second
    }

    // Form submission with real progress tracking
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const modelType = modelTypeSelect.value;
        const trainingScope = trainingScopeSelect ? trainingScopeSelect.value : 'all_models_compare';
        const llmProvider = llmProviderSelect ? llmProviderSelect.value : 'groq';
        const llmModel = llmModelSelect ? llmModelSelect.value : '';
        const modelNameMap = {
            random_forest: 'Random Forest',
            xgboost: 'XGBoost',
            svm: 'SVM',
            knn: 'KNN',
            decision_tree: 'Decision Tree',
            dt: 'Decision Tree'
        };
        const modelName = modelNameMap[modelType] || 'model';
        const scopeLabel = trainingScope === 'single_model'
            ? 'single model mode (no comparison)'
            : 'all-model comparison mode (SVM/DT/RF/KNN/XGBoost)';
        
        if (!confirm(`Start training ${modelName} model in ${scopeLabel} using ${llmProvider}:${llmModel}? This may take several minutes.`)) {
            return;
        }

        try {
            console.log('🚀 Starting training process...');
            console.log('Predict Service URL:', PREDICT_SERVICE_URL);

            // Generate session ID
            console.log('📝 Generating session ID...');
            const sessionResponse = await fetch(TRAINING_PROGRESS_SESSION_URL, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': CSRF_TOKEN,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            console.log('Session response status:', sessionResponse.status);
            const sessionData = await readJsonResponse(sessionResponse, 'Failed to generate training session');
            console.log('Session data:', sessionData);
            
            if (!sessionData.success) {
                throw new Error('Failed to generate session ID');
            }
            
            sessionId = sessionData.session_id;
            console.log('✅ Generated session ID:', sessionId);
            
            // Show progress modal
            progressModal.show();
            trainBtn.disabled = true;
            trainBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Training...';
            
            console.log('✅ Progress modal shown');
            
            // Clear previous logs and reset progress
            trainingLog.innerHTML = '<div style="color: #858585;">⏳ Initializing training session...</div>';
            progressBar.style.width = '0%';
            progressBar.innerHTML = '<strong style="font-size: 1.1em;">0%</strong>';
            progressBar.classList.remove('bg-success', 'bg-danger');
            progressBar.classList.add('bg-info', 'progress-bar-animated');
            
            // Start polling for progress
            console.log('🔄 Starting progress polling...');
            startProgressPolling(sessionId);
            
            // Get form data
            const formData = new FormData(form);
            const formDataObj = {};
            formData.forEach((value, key) => {
                formDataObj[key] = value;
            });
            
            // Add session_id to form data
            formDataObj.session_id = sessionId;
            
            // Submit form via AJAX
            console.log('📤 Submitting training request...');
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': CSRF_TOKEN,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(formDataObj)
            });
            
            console.log('Training response status:', response.status);

            const responseData = await readJsonResponse(response, 'Failed to start training');
            console.log('✅ Training submitted successfully:', responseData);
            
        } catch (error) {
            console.error('❌ Error starting training:', error);
            alert('Failed to start training: ' + error.message);
            trainBtn.disabled = false;
            trainBtn.innerHTML = '<i class="bi bi-play-circle"></i> Start Training';
            progressModal.hide();
            
            // Stop polling if started
            if (progressInterval) {
                clearInterval(progressInterval);
            }
        }
    });
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (progressInterval) {
            clearInterval(progressInterval);
        }
    });
});
</script>
@endsection
