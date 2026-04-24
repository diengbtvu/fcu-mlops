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
    $predictBrowserBase = rtrim((string) config('services.predict_service.browser_url', ''), '/');
    $inspectUrl = ($predictBrowserBase !== '' ? $predictBrowserBase : '') . '/train/inspect';
    $sheetUiTexts = [
        'chooseSheet' => __('datasets.choose_sheet'),
        'sourceLabel' => __('datasets.preview_source'),
        'previewSheetLabel' => __('datasets.preview_sheet'),
        'datasetFallback' => __('datasets.preview_dataset'),
        'rowsAfterPreprocessing' => __('datasets.rows_after_preprocessing'),
        'minimumRequiredRows' => __('datasets.minimum_required_rows'),
        'chooseSheetToContinue' => __('datasets.choose_sheet_to_continue'),
        'multiSheetWarning' => __('datasets.multi_sheet_select_warning'),
        'validDatasetBadge' => __('datasets.valid_dataset'),
        'validDatasetMessage' => __('datasets.valid_dataset_message'),
        'invalidDatasetBadge' => __('datasets.invalid_dataset'),
        'invalidDatasetMessage' => __('datasets.invalid_dataset_message'),
        'inspectInProgress' => __('datasets.inspect_in_progress'),
        'inspectFailed' => __('datasets.inspect_failed'),
        'noPreviewRows' => __('datasets.no_preview_rows'),
    ];
@endphp
<div class="container">
    <h2>{{ __('datasets.upload_dataset') }}</h2>

    @if ($errors->any())
        <div class="alert alert-danger">
            <strong>{{ __('error') }}!</strong> {{ __('datasets.error_check_input') }}<br><br>
            <ul>
                @foreach ($errors->all() as $error)
                    <li>{{ $error }}</li>
                @endforeach
            </ul>
        </div>
    @endif

    <form action="{{ route($routePrefix . '.datasets.store') }}" method="POST" enctype="multipart/form-data" id="datasetUploadForm">
        @csrf
        <div class="mb-3">
            <label for="DatasetName" class="form-label">{{ __('datasets.name') }}</label>
            <input type="text" name="DatasetName" class="form-control" required>
        </div>

        <div class="mb-3">
            <label for="Description" class="form-label">{{ __('datasets.description_optional') }}</label>
            <textarea name="Description" class="form-control"></textarea>
        </div>

        <div class="mb-3">
            <label for="dataset_file" class="form-label">{{ __('datasets.choose_file') }}</label>
            <input type="file" name="dataset_file" id="dataset_file" class="form-control" accept=".csv,.xls,.xlsx" required>
            <input type="hidden" name="selected_sheet" id="selected_sheet" value="">
            <div class="mt-2">
                <span class="small text-muted d-block mb-2">{{ __('datasets.download_templates') }}</span>
                <div class="d-flex flex-wrap gap-2">
                    <a href="{{ asset('templates/template_train.csv') }}" class="btn btn-outline-primary btn-sm" download>
                        {{ __('datasets.download_template_csv') }}
                    </a>
                    <a href="{{ asset('templates/template_train.xlsx') }}" class="btn btn-outline-primary btn-sm" download>
                        {{ __('datasets.download_template_xlsx') }}
                    </a>
                </div>
                <small class="text-muted d-block mt-2">{{ __('datasets.template_note') }}</small>
                <small class="text-muted d-block mt-1">{{ __('datasets.template_source_note') }}</small>
            </div>
        </div>

        <div id="inspectStatus" class="alert d-none" role="alert"></div>

        <div id="sheetSelectionCard" class="card mb-3 d-none">
            <div class="card-header">
                <strong>{{ __('datasets.sheet_selection') }}</strong>
            </div>
            <div class="card-body">
                <label for="sheet_select" class="form-label">{{ __('datasets.choose_sheet_to_train') }}</label>
                <select id="sheet_select" class="form-select">
                    <option value="">{{ __('datasets.choose_sheet') }}</option>
                </select>
                <small class="text-muted d-block mt-2">{{ __('datasets.multi_sheet_instruction') }}</small>
            </div>
        </div>

        <div id="validationCard" class="card mb-3 d-none">
            <div class="card-header">
                <strong>{{ __('datasets.validation_result') }}</strong>
            </div>
            <div class="card-body">
                <div id="validationSummary" class="mb-2"></div>
                <div id="validationMeta" class="small text-muted"></div>
                <div id="missingColumnsWrapper" class="mt-2 d-none">
                    <strong>{{ __('datasets.missing_required_columns') }}</strong>
                    <div id="missingColumns" class="mt-1"></div>
                </div>
            </div>
        </div>

        <div id="previewCard" class="card mb-4 d-none">
            <div class="card-header">
                <strong>{{ __('datasets.preview_after_normalization') }}</strong>
            </div>
            <div class="card-body">
                <div id="previewMeta" class="small text-muted mb-3"></div>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered align-middle" id="previewTable">
                        <thead></thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>

        <button type="submit" class="btn btn-success" id="uploadBtn" disabled>{{ __('upload') }}</button>
        <a href="{{ route($routePrefix . '.datasets.index') }}" class="btn btn-secondary">{{ __('back') }}</a>
    </form>
</div>
@endsection

@section('scripts')
<script>
document.addEventListener('DOMContentLoaded', function () {
    const inspectUrl = @json($inspectUrl);
    const texts = @json($sheetUiTexts);
    const fileInput = document.getElementById('dataset_file');
    const selectedSheetInput = document.getElementById('selected_sheet');
    const uploadBtn = document.getElementById('uploadBtn');
    const inspectStatus = document.getElementById('inspectStatus');
    const sheetSelectionCard = document.getElementById('sheetSelectionCard');
    const sheetSelect = document.getElementById('sheet_select');
    const validationCard = document.getElementById('validationCard');
    const validationSummary = document.getElementById('validationSummary');
    const validationMeta = document.getElementById('validationMeta');
    const missingColumnsWrapper = document.getElementById('missingColumnsWrapper');
    const missingColumns = document.getElementById('missingColumns');
    const previewCard = document.getElementById('previewCard');
    const previewMeta = document.getElementById('previewMeta');
    const previewTable = document.getElementById('previewTable');
    const previewHead = previewTable.querySelector('thead');
    const previewBody = previewTable.querySelector('tbody');

    function setStatus(message, type) {
        inspectStatus.className = `alert alert-${type}`;
        inspectStatus.textContent = message;
        inspectStatus.classList.remove('d-none');
    }

    function clearStatus() {
        inspectStatus.className = 'alert d-none';
        inspectStatus.textContent = '';
    }

    function resetInspectionState() {
        clearStatus();
        selectedSheetInput.value = '';
        uploadBtn.disabled = true;
        sheetSelectionCard.classList.add('d-none');
        validationCard.classList.add('d-none');
        previewCard.classList.add('d-none');
        missingColumnsWrapper.classList.add('d-none');
        missingColumns.innerHTML = '';
        validationSummary.innerHTML = '';
        validationMeta.textContent = '';
        previewMeta.textContent = '';
        previewHead.innerHTML = '';
        previewBody.innerHTML = '';
        sheetSelect.innerHTML = `<option value="">${texts.chooseSheet}</option>`;
    }

    function renderPreview(columns, rows) {
        previewHead.innerHTML = '';
        previewBody.innerHTML = '';

        if (!Array.isArray(columns) || columns.length === 0) {
            previewCard.classList.add('d-none');
            return;
        }

        const headerRow = document.createElement('tr');
        columns.forEach((column) => {
            const th = document.createElement('th');
            th.textContent = column;
            headerRow.appendChild(th);
        });
        previewHead.appendChild(headerRow);

        if (Array.isArray(rows) && rows.length > 0) {
            rows.forEach((row) => {
                const tr = document.createElement('tr');
                columns.forEach((column) => {
                    const td = document.createElement('td');
                    const value = row[column];
                    td.textContent = value === null || value === undefined ? '' : value;
                    tr.appendChild(td);
                });
                previewBody.appendChild(tr);
            });
        } else {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = columns.length;
            td.className = 'text-muted text-center';
            td.textContent = texts.noPreviewRows;
            tr.appendChild(td);
            previewBody.appendChild(tr);
        }

        previewCard.classList.remove('d-none');
    }

    function renderInspection(result, chosenSheet) {
        const requiresSheetSelection = Boolean(result.requires_sheet_selection);
        const selectedSheet = chosenSheet || result.selected_sheet || '';
        const detectedFormat = String(result.detected_format || '').toUpperCase();
        const previewSheet = result.preview_sheet || selectedSheet || detectedFormat || texts.datasetFallback;

        renderPreview(result.preview_columns || [], result.preview_rows || []);
        previewMeta.textContent = `${texts.sourceLabel}: ${detectedFormat}${previewSheet ? ` | ${texts.previewSheetLabel}: ${previewSheet}` : ''}`;

        if (Array.isArray(result.sheet_names) && result.sheet_names.length > 1) {
            sheetSelectionCard.classList.remove('d-none');
            sheetSelect.innerHTML = `<option value="">${texts.chooseSheet}</option>`;
            result.sheet_names.forEach((sheetName) => {
                const option = document.createElement('option');
                option.value = sheetName;
                option.textContent = sheetName;
                if (selectedSheet && sheetName === selectedSheet) {
                    option.selected = true;
                }
                sheetSelect.appendChild(option);
            });
        } else {
            sheetSelectionCard.classList.add('d-none');
        }

        validationCard.classList.remove('d-none');
        const rowsAfter = Number(result.rows_after_preprocessing || 0);
        validationMeta.textContent = `${texts.rowsAfterPreprocessing}: ${rowsAfter} | ${texts.minimumRequiredRows}: ${result.minimum_required_rows || 6}`;

        if (Array.isArray(result.missing_columns) && result.missing_columns.length > 0) {
            missingColumnsWrapper.classList.remove('d-none');
            missingColumns.innerHTML = result.missing_columns
                .map((column) => `<span class="badge bg-danger me-1 mb-1">${column}</span>`)
                .join('');
        } else {
            missingColumnsWrapper.classList.add('d-none');
            missingColumns.innerHTML = '';
        }

        if (requiresSheetSelection && !selectedSheet) {
            selectedSheetInput.value = '';
            uploadBtn.disabled = true;
            validationSummary.innerHTML = `<span class="badge bg-warning text-dark">${texts.chooseSheetToContinue}</span>`;
            setStatus(texts.multiSheetWarning, 'warning');
            return;
        }

        if (result.is_valid) {
            selectedSheetInput.value = selectedSheet;
            uploadBtn.disabled = false;
            validationSummary.innerHTML = `<span class="badge bg-success">${texts.validDatasetBadge}</span>`;
            setStatus(texts.validDatasetMessage, 'success');
            return;
        }

        selectedSheetInput.value = selectedSheet;
        uploadBtn.disabled = true;
        const errorMessage = result.validation_error || texts.invalidDatasetMessage;
        validationSummary.innerHTML = `<span class="badge bg-danger">${texts.invalidDatasetBadge}</span>`;
        setStatus(errorMessage, 'danger');
    }

    async function inspectFile(sheetName = '') {
        const file = fileInput.files[0];
        if (!file) {
            resetInspectionState();
            return;
        }

        uploadBtn.disabled = true;
        setStatus(texts.inspectInProgress, 'info');

        const formData = new FormData();
        formData.append('dataset_file', file);
        if (sheetName) {
            formData.append('sheet_name', sheetName);
        }
        formData.append('preview_rows', '10');

        try {
            const response = await fetch(inspectUrl, {
                method: 'POST',
                body: formData,
            });
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || texts.inspectFailed);
            }

            renderInspection(result, sheetName);
        } catch (error) {
            resetInspectionState();
            setStatus(error.message || texts.inspectFailed, 'danger');
        }
    }

    fileInput.addEventListener('change', function () {
        resetInspectionState();
        if (fileInput.files.length > 0) {
            inspectFile('');
        }
    });

    sheetSelect.addEventListener('change', function () {
        const chosenSheet = sheetSelect.value;
        selectedSheetInput.value = chosenSheet;
        if (chosenSheet) {
            inspectFile(chosenSheet);
        } else {
            uploadBtn.disabled = true;
            setStatus(texts.chooseSheetToContinue, 'warning');
        }
    });
});
</script>
@endsection
