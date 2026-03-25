/**
 * Prediction Form JavaScript
 * Handles form submission, validation, and model selection
 */

class PredictionForm {
    constructor(formId, options = {}) {
        this.form = document.getElementById(formId);
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.resultDiv = document.getElementById('predictionResult');
        this.options = {
            submitUrl: options.submitUrl || '/predict',
            csrfToken: options.csrfToken || document.querySelector('meta[name="csrf-token"]')?.getAttribute('content'),
            userType: options.userType || 'user',
            ...options
        };

        this.init();
    }

    init() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            this.setupInputValidation();
            this.setupModelSelection();
        }
    }

    getMessage(key, fallback) {
        return this.options.messages?.[key] || fallback;
    }

    formatMessage(template, replacements = {}) {
        return Object.entries(replacements).reduce((message, [key, value]) => {
            return message.replaceAll(`:${key}`, value);
        }, template);
    }

    async handleSubmit(e) {
        e.preventDefault();

        this.showLoading();
        this.hideResult();

        try {
            const formData = new FormData(this.form);
            const data = this.prepareData(formData);

            this.validateData(data);

            const response = await fetch(this.options.submitUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': this.options.csrfToken,
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            this.displayResult(result);
        } catch (error) {
            this.displayError(error.message);
        } finally {
            this.hideLoading();
        }
    }

    prepareData(formData) {
        return {
            ph: parseFloat(formData.get('ph')),
            vss: parseFloat(formData.get('vss')),
            ethanol: parseFloat(formData.get('ethanol')),
            acetate: parseFloat(formData.get('acetate')),
            propionate: parseFloat(formData.get('propionate')),
            butyrate: parseFloat(formData.get('butyrate')),
            sucrose_degradation: parseFloat(formData.get('sucrose_degradation')),
            orp_mid: parseFloat(formData.get('orp_mid')),
            orp_low: parseFloat(formData.get('orp_low')),
            vfa: parseFloat(formData.get('vfa')),
            cod_o: parseFloat(formData.get('cod_o')),
            ml_model_id: parseInt(formData.get('ml_model_id'), 10)
        };
    }

    validateData(data) {
        if (!data.ml_model_id || Number.isNaN(data.ml_model_id)) {
            throw new Error(this.getMessage('selectModelError', 'Please select an AI model'));
        }

        const inputs = this.form.querySelectorAll('input[type="number"]');

        for (const input of inputs) {
            const value = parseFloat(input.value);
            const min = input.min === '' ? Number.NEGATIVE_INFINITY : parseFloat(input.min);
            const max = input.max === '' ? Number.POSITIVE_INFINITY : parseFloat(input.max);
            const label = input.dataset.label || input.name;

            if (Number.isNaN(value)) {
                throw new Error(this.formatMessage(
                    this.getMessage('fieldRequired', ':field is required'),
                    { field: label }
                ));
            }

            if (value < min || value > max) {
                throw new Error(this.formatMessage(
                    this.getMessage('fieldBetween', ':field must be between :min and :max'),
                    { field: label, min: input.min, max: input.max }
                ));
            }
        }
    }

    displayResult(result) {
        if (result.success) {
            const accessType = this.options.userType === 'admin'
                ? this.getMessage('adminAccess', '(Admin Access)')
                : this.getMessage('userAccess', '(User Access)');
            const unit = result.unit || 'L/h/L';
            const formattedPrediction = Number(result.prediction).toFixed(4);
            const modelSource = result.model_source || 'file';
            const isMLflow = modelSource === 'mlflow';
            const modelName = result.model_used || this.getMessage('aiModelFallback', 'AI model');

            let modelInfoHtml = `
                <i class="bi bi-robot me-1"></i>
                ${this.getMessage('predictionCompletedUsing', 'Prediction completed using')}
                <strong>${modelName}</strong> ${accessType}
            `;

            if (isMLflow) {
                modelInfoHtml = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <i class="bi bi-robot me-1"></i>
                            ${this.getMessage('predictionUsing', 'Prediction using')}
                            <strong>${modelName}</strong> ${accessType}
                        </div>
                    </div>
                    ${result.mlflow_run_id ? `<small class="text-muted d-block mt-1"><i class="bi bi-tag me-1"></i>${this.getMessage('mlflowRun', 'MLflow Run')}: ${result.mlflow_run_id.substring(0, 8)}...</small>` : ''}
                `;
            }

            this.resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <h4><i class="bi bi-check-circle"></i> ${this.getMessage('predictionResultTitle', 'Prediction Result')}</h4>
                    <p class="mb-2"><strong>${this.getMessage('hydrogenProductionRate', 'Hydrogen Production Rate')}:</strong> <span class="result-value">${formattedPrediction}</span> ${unit}</p>
                    <small>${modelInfoHtml}</small>
                </div>
            `;
        } else {
            this.displayError(result.error || this.getMessage('unknownError', 'Unknown error occurred'));
        }
        this.showResult();
    }

    displayError(message) {
        this.resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <h4><i class="bi bi-exclamation-triangle"></i> ${this.getMessage('errorTitle', 'Error')}</h4>
                <p class="mb-0">${message}</p>
            </div>
        `;
        this.showResult();
    }

    showLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'flex';
        }

        const submitBtn = this.form.querySelector('.btn-predict');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="bi bi-hourglass-split me-2"></i>${this.options.processingLabel || 'Processing...'}`;
        }
    }

    hideLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }

        const submitBtn = this.form.querySelector('.btn-predict');
        if (submitBtn) {
            submitBtn.disabled = false;
            const defaultLabel = this.options.defaultSubmitLabel
                || (this.options.userType === 'admin' ? 'Predict HPR (Admin)' : 'Predict HPR');
            submitBtn.innerHTML = `<i class="bi bi-calculator me-2"></i>${defaultLabel}`;
        }
    }

    showResult() {
        if (this.resultDiv) {
            this.resultDiv.style.display = 'block';
        }
    }

    hideResult() {
        if (this.resultDiv) {
            this.resultDiv.style.display = 'none';
        }
    }

    setupInputValidation() {
        const inputs = this.form.querySelectorAll('input[type="number"]');

        inputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                const min = parseFloat(e.target.min);
                const max = parseFloat(e.target.max);

                if (!Number.isNaN(value) && !Number.isNaN(min) && !Number.isNaN(max)) {
                    if (value < min || value > max) {
                        e.target.classList.add('is-invalid');
                    } else {
                        e.target.classList.remove('is-invalid');
                    }
                }
            });
        });
    }

    setupModelSelection() {
        const modelSelect = document.getElementById('ml_model_id');
        const modelInfoCard = document.getElementById('selectedModelInfo');

        if (modelSelect && modelInfoCard) {
            if (modelSelect.options.length > 1 && !modelSelect.value) {
                modelSelect.selectedIndex = 1;
            }

            this.updateModelInfo();
            modelSelect.addEventListener('change', () => this.updateModelInfo());
        }
    }

    updateModelInfo() {
        const modelSelect = document.getElementById('ml_model_id');
        const modelInfoCard = document.getElementById('selectedModelInfo');
        const modelName = document.getElementById('selectedModelName');
        const modelBadge = document.getElementById('selectedModelBadge');
        const modelSize = document.getElementById('selectedModelSize');

        const mlflowBadge = document.getElementById('mlflowBadge');
        const mlflowRunInfo = document.getElementById('mlflowRunInfo');
        const mlflowRunId = document.getElementById('mlflowRunId');

        if (!modelSelect || !modelInfoCard) return;

        const selectedOption = modelSelect.options[modelSelect.selectedIndex];

        if (selectedOption && selectedOption.value) {
            const libType = selectedOption.dataset.libType || 'unknown';
            const fileSize = selectedOption.dataset.fileSize || 0;
            const modelNameText = selectedOption.text.split(' (')[0].replace('<span class="badge bg-info">MLflow</span>', '').trim();

            const hasMlflow = selectedOption.dataset.hasMlflow === 'true';
            const mlflowRunIdValue = selectedOption.dataset.mlflowRunId || '';

            if (modelName) modelName.textContent = modelNameText;
            if (modelBadge) {
                modelBadge.textContent = libType.toUpperCase();
                modelBadge.className = `model-badge ${libType.toLowerCase()}`;
            }
            if (modelSize) {
                modelSize.textContent = fileSize > 0 ? `${fileSize}MB` : this.getMessage('unknownSize', 'Unknown');
            }

            if (mlflowBadge) {
                mlflowBadge.style.display = hasMlflow ? 'inline-block' : 'none';
            }
            if (mlflowRunInfo && mlflowRunId) {
                if (hasMlflow && mlflowRunIdValue) {
                    mlflowRunInfo.style.display = 'block';
                    mlflowRunId.textContent = mlflowRunIdValue.substring(0, 12) + '...';
                } else {
                    mlflowRunInfo.style.display = 'none';
                }
            }

            modelInfoCard.classList.add('show');
        } else {
            modelInfoCard.classList.remove('show');
        }
    }

    clearForm() {
        if (this.form) {
            this.form.reset();
            this.hideResult();
            this.updateModelInfo();
        }
    }

    resetValidation() {
        const inputs = this.form.querySelectorAll('.is-invalid');
        inputs.forEach(input => input.classList.remove('is-invalid'));
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.initPredictionForm === 'function') {
        window.initPredictionForm();
    }
});
