@extends('layouts.app')

@section('title', __('models.compare_models'))
@section('page-title', __('models.compare_models'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.models') }}">{{ __('nav.models') }}</a></li>
    <li class="breadcrumb-item active">{{ __('models.comparison') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">
                    <i class="bi bi-bar-chart-line"></i> {{ __('models.select_models_to_compare') }}
                </h3>
            </div>
            <div class="card-body">
                @if($models->count() < 2)
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle"></i>
                        <strong>{{ __('notice') }}:</strong> {{ __('models.need_2_models_notice') }}
                    </div>
                    <a href="{{ route('admin.datasets.index') }}" class="btn btn-primary">
                        <i class="bi bi-plus"></i> {{ __('models.train_new_model') }}
                    </a>
                @else
                    <form action="{{ route('admin.models.compare.result') }}" method="GET" id="compareForm">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card bg-light">
                                    <div class="card-header">
                                        <h5 class="mb-0">
                                            <i class="bi bi-1-circle-fill text-primary"></i> {{ __('models.model') }} 1
                                        </h5>
                                    </div>
                                    <div class="card-body">
                                        <div class="form-group">
                                            <label for="model1_id">{{ __('models.select_first_model') }} <span class="text-danger">*</span></label>
                                            <select name="model1_id" id="model1_id" class="form-control @error('model1_id') is-invalid @enderror" required>
                                                <option value="">-- {{ __('models.choose_model') }} --</option>
                                                @foreach($models as $model)
                                                    <option value="{{ $model->id }}" 
                                                            data-type="{{ $model->LibraryType }}"
                                                            data-mse="{{ $model->MSE }}"
                                                            data-mae="{{ $model->MAE }}"
                                                            data-rmse="{{ $model->RMSE }}"
                                                            data-r2="{{ $model->R2 }}"
                                                            data-dataset="{{ $model->dataset->DatasetName ?? 'N/A' }}"
                                                            data-date="{{ $model->TrainedDate ? $model->TrainedDate->format('Y-m-d H:i') : 'N/A' }}"
                                                            {{ old('model1_id') == $model->id ? 'selected' : '' }}>
                                                        {{ $model->ModelName }} 
                                                        ({{ strtoupper($model->LibraryType) }})
                                                        - R²: {{ number_format($model->R2, 4) }}
                                                    </option>
                                                @endforeach
                                            </select>
                                            @error('model1_id')
                                                <div class="invalid-feedback">{{ $message }}</div>
                                            @enderror
                                        </div>

                                        <div id="model1-preview" class="mt-3" style="display: none;">
                                            <h6>{{ __('models.model_preview') }}:</h6>
                                            <table class="table table-sm table-bordered">
                                                <tr>
                                                    <th>{{ __('models.type') }}:</th>
                                                    <td id="model1-type"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.dataset') }}:</th>
                                                    <td id="model1-dataset"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.r2') }}:</th>
                                                    <td id="model1-r2"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.rmse') }}:</th>
                                                    <td id="model1-rmse"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.trained') }}:</th>
                                                    <td id="model1-date"></td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="card bg-light">
                                    <div class="card-header">
                                        <h5 class="mb-0">
                                            <i class="bi bi-2-circle-fill text-success"></i> {{ __('models.model') }} 2
                                        </h5>
                                    </div>
                                    <div class="card-body">
                                        <div class="form-group">
                                            <label for="model2_id">{{ __('models.select_second_model') }} <span class="text-danger">*</span></label>
                                            <select name="model2_id" id="model2_id" class="form-control @error('model2_id') is-invalid @enderror" required>
                                                <option value="">-- {{ __('models.choose_model') }} --</option>
                                                @foreach($models as $model)
                                                    <option value="{{ $model->id }}"
                                                            data-type="{{ $model->LibraryType }}"
                                                            data-mse="{{ $model->MSE }}"
                                                            data-mae="{{ $model->MAE }}"
                                                            data-rmse="{{ $model->RMSE }}"
                                                            data-r2="{{ $model->R2 }}"
                                                            data-dataset="{{ $model->dataset->DatasetName ?? 'N/A' }}"
                                                            data-date="{{ $model->TrainedDate ? $model->TrainedDate->format('Y-m-d H:i') : 'N/A' }}"
                                                            {{ old('model2_id') == $model->id ? 'selected' : '' }}>
                                                        {{ $model->ModelName }} 
                                                        ({{ strtoupper($model->LibraryType) }})
                                                        - R²: {{ number_format($model->R2, 4) }}
                                                    </option>
                                                @endforeach
                                            </select>
                                            @error('model2_id')
                                                <div class="invalid-feedback">{{ $message }}</div>
                                            @enderror
                                        </div>

                                        <div id="model2-preview" class="mt-3" style="display: none;">
                                            <h6>{{ __('models.model_preview') }}:</h6>
                                            <table class="table table-sm table-bordered">
                                                <tr>
                                                    <th>{{ __('models.type') }}:</th>
                                                    <td id="model2-type"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.dataset') }}:</th>
                                                    <td id="model2-dataset"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.r2') }}:</th>
                                                    <td id="model2-r2"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.rmse') }}:</th>
                                                    <td id="model2-rmse"></td>
                                                </tr>
                                                <tr>
                                                    <th>{{ __('models.trained') }}:</th>
                                                    <td id="model2-date"></td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="text-center mt-4">
                            <button type="submit" class="btn btn-primary btn-lg" id="compareBtn" disabled>
                                <i class="bi bi-bar-chart-line"></i> {{ __('models.compare_models') }}
                            </button>
                            <a href="{{ route('admin.models') }}" class="btn btn-secondary btn-lg">
                                <i class="bi bi-arrow-left"></i> {{ __('back') }} {{ __('nav.models') }}
                            </a>
                        </div>
                    </form>
                @endif
            </div>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<script>
document.addEventListener('DOMContentLoaded', function() {
    const model1Select = document.getElementById('model1_id');
    const model2Select = document.getElementById('model2_id');
    const compareBtn = document.getElementById('compareBtn');

    function updatePreview(selectEl, previewId) {
        const selectedOption = selectEl.options[selectEl.selectedIndex];
        const preview = document.getElementById(previewId + '-preview');
        
        if (selectedOption.value) {
            document.getElementById(previewId + '-type').textContent = selectedOption.dataset.type.toUpperCase();
            document.getElementById(previewId + '-dataset').textContent = selectedOption.dataset.dataset;
            document.getElementById(previewId + '-r2').textContent = parseFloat(selectedOption.dataset.r2).toFixed(4);
            document.getElementById(previewId + '-rmse').textContent = parseFloat(selectedOption.dataset.rmse).toFixed(4);
            document.getElementById(previewId + '-date').textContent = selectedOption.dataset.date;
            preview.style.display = 'block';
        } else {
            preview.style.display = 'none';
        }
    }

    function checkCanCompare() {
        const model1 = model1Select.value;
        const model2 = model2Select.value;
        
        if (model1 && model2 && model1 !== model2) {
            compareBtn.disabled = false;
        } else {
            compareBtn.disabled = true;
        }

        // Warning if same model selected
        if (model1 && model2 && model1 === model2) {
            alert(@js(__('models.select_different_models')));
            model2Select.value = '';
            updatePreview(model2Select, 'model2');
        }
    }

    model1Select.addEventListener('change', function() {
        updatePreview(this, 'model1');
        checkCanCompare();
    });

    model2Select.addEventListener('change', function() {
        updatePreview(this, 'model2');
        checkCanCompare();
    });

    // Initialize if values already selected
    if (model1Select.value) {
        updatePreview(model1Select, 'model1');
    }
    if (model2Select.value) {
        updatePreview(model2Select, 'model2');
    }
    checkCanCompare();
});
</script>
@endsection
