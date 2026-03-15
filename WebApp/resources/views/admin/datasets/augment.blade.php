@extends('layouts.app')

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('content')
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-10">
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">
                        <i class="bi bi-database-add"></i> {{ __('datasets.data_augmentation') }}
                    </h4>
                </div>
                <div class="card-body">
                    <!-- Dataset Info -->
                    <div class="alert alert-info">
                        <h5><i class="bi bi-info-circle"></i> {{ __('datasets.dataset_information') }}</h5>
                        <p class="mb-1"><strong>{{ __('datasets.name') }}:</strong> {{ $dataset->DatasetName }}</p>
                        <p class="mb-1"><strong>{{ __('datasets.description') }}:</strong> {{ $dataset->Description ?? __('models.na') }}</p>
                        <p class="mb-1"><strong>{{ __('datasets.uploaded_by') }}:</strong> {{ $dataset->user->FullName ?? __('datasets.unknown_user') }}</p>
                        <p class="mb-0"><strong>{{ __('datasets.upload_date') }}:</strong> {{ $dataset->UploadDate }}</p>
                    </div>

                    <!-- Augmentation Form -->
                    <form action="{{ route('admin.datasets.augment', $dataset->DatasetId) }}" method="POST" id="augmentForm">
                        @csrf

                        <!-- Augmentation Method -->
                        <div class="mb-4">
                            <label for="method" class="form-label fw-bold">
                                <i class="bi bi-gear"></i> {{ __('datasets.augmentation_method_required') }}
                            </label>
                            <select name="method" id="method" class="form-select @error('method') is-invalid @enderror" required>
                                <option value="">-- {{ __('datasets.select_method') }} --</option>
                                @foreach($availableMethods as $key => $method)
                                    <option value="{{ $key }}" {{ old('method') == $key ? 'selected' : '' }}>
                                        {{ $method['name'] }}
                                    </option>
                                @endforeach
                            </select>
                            @error('method')
                                <div class="invalid-feedback">{{ $message }}</div>
                            @enderror
                            <div id="methodDescription" class="form-text mt-2"></div>
                        </div>

                        <!-- Output Name (Optional) -->
                        <div class="mb-4">
                            <label for="output_name" class="form-label">
                                <i class="bi bi-tag"></i> {{ __('datasets.custom_output_name') }}
                            </label>
                            <input type="text" 
                                   name="output_name" 
                                   id="output_name" 
                                   class="form-control @error('output_name') is-invalid @enderror"
                                   value="{{ old('output_name') }}"
                                   placeholder="{{ __('datasets.leave_empty_auto') }}">
                            @error('output_name')
                                <div class="invalid-feedback">{{ $message }}</div>
                            @enderror
                            <div class="form-text">{{ __('datasets.auto_name_note') }}</div>
                        </div>

                        <!-- Method-specific Parameters -->
                        <div id="parametersContainer">
                            <!-- SMOTE & Sampling Parameters -->
                            <div class="parameter-group" data-methods="smote,random_oversample,random_undersample" style="display:none;">
                                <div class="card mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">{{ __('datasets.sampling_parameters') }}</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label for="sampling_strategy" class="form-label">{{ __('datasets.sampling_strategy') }}</label>
                                            <select name="sampling_strategy" id="sampling_strategy" class="form-select">
                                                <option value="auto" selected>{{ __('datasets.auto_default') }}</option>
                                                <option value="minority">{{ __('datasets.minority') }}</option>
                                                <option value="not majority">{{ __('datasets.not_majority') }}</option>
                                                <option value="not minority">{{ __('datasets.not_minority') }}</option>
                                                <option value="all">{{ __('all') }}</option>
                                            </select>
                                            <div class="form-text">{{ __('datasets.sampling_strategy_desc') }}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- SMOTE K-Neighbors -->
                            <div class="parameter-group" data-methods="smote" style="display:none;">
                                <div class="card mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">{{ __('datasets.smote_parameters') }}</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label for="k_neighbors" class="form-label">{{ __('datasets.k_neighbors') }}</label>
                                            <input type="number" 
                                                   name="k_neighbors" 
                                                   id="k_neighbors" 
                                                   class="form-control" 
                                                   value="5" 
                                                   min="1" 
                                                   max="20">
                                            <div class="form-text">{{ __('datasets.k_neighbors_desc') }}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Noise Parameters -->
                            <div class="parameter-group" data-methods="noise_injection,duplication" style="display:none;">
                                <div class="card mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">{{ __('datasets.noise_parameters') }}</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label for="noise_level" class="form-label">{{ __('datasets.noise_level') }}</label>
                                            <input type="number" 
                                                   name="noise_level" 
                                                   id="noise_level" 
                                                   class="form-control" 
                                                   value="0.05" 
                                                   step="0.01" 
                                                   min="0" 
                                                   max="1">
                                            <div class="form-text">{{ __('datasets.noise_level_desc') }}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Duplication Parameters -->
                            <div class="parameter-group" data-methods="noise_injection,interpolation,duplication" style="display:none;">
                                <div class="card mb-3">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">{{ __('datasets.duplication_parameters') }}</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label for="duplicate_factor" class="form-label">{{ __('datasets.duplicate_factor') }}</label>
                                            <input type="number" 
                                                   name="duplicate_factor" 
                                                   id="duplicate_factor" 
                                                   class="form-control" 
                                                   value="2" 
                                                   min="2" 
                                                   max="10">
                                            <div class="form-text">{{ __('datasets.duplicate_factor_desc') }}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Action Buttons -->
                        <div class="d-flex justify-content-between mt-4">
                            <a href="{{ route('admin.datasets.index') }}" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> {{ __('cancel') }}
                            </a>
                            <button type="submit" class="btn btn-primary" id="submitBtn">
                                <i class="bi bi-play-circle"></i> {{ __('datasets.start_augmentation') }}
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Information Card -->
            <!-- <div class="card mt-4">
                <div class="card-header bg-info text-white">
                    <h5 class="mb-0"><i class="bi bi-lightbulb"></i> {{ __('datasets.about_augmentation') }}</h5>
                </div>
                <div class="card-body">
                    <p>{{ __('datasets.about_augmentation_desc') }}</p>
                    
                    <h6 class="mt-3">{{ __('datasets.available_methods') }}</h6>
                    <ul class="list-group">
                        @foreach($availableMethods as $key => $method)
                            <li class="list-group-item">
                                <strong>{{ $method['name'] }}:</strong> {{ $method['description'] }}
                            </li>
                        @endforeach
                    </ul>
                </div>
            </div> -->
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const methodSelect = document.getElementById('method');
    const methodDescription = document.getElementById('methodDescription');
    const parameterGroups = document.querySelectorAll('.parameter-group');
    
    const methods = @json($availableMethods);
    
    methodSelect.addEventListener('change', function() {
        const selectedMethod = this.value;
        
        // Update description
        if (selectedMethod && methods[selectedMethod]) {
            methodDescription.innerHTML = `<div class="alert alert-secondary"><strong>{{ __('datasets.description') }}:</strong> ${methods[selectedMethod].description}</div>`;
        } else {
            methodDescription.innerHTML = '';
        }
        
        // Show/hide parameter groups
        parameterGroups.forEach(group => {
            const supportedMethods = group.dataset.methods.split(',');
            if (supportedMethods.includes(selectedMethod)) {
                group.style.display = 'block';
            } else {
                group.style.display = 'none';
            }
        });
    });
    
    // Form submission handling
    const form = document.getElementById('augmentForm');
    const submitBtn = document.getElementById('submitBtn');
    
    form.addEventListener('submit', function() {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> {{ __('datasets.processing') }}';
    });
});
</script>
@endsection
