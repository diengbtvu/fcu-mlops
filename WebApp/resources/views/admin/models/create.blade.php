@extends('layouts.app')

@section('title', __('models.upload_model'))
@section('page-title', __('models.upload_model'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.models') }}">{{ __('nav.models') }}</a></li>
    <li class="breadcrumb-item active">{{ __('models.upload') }}</li>
@endsection

@section('sidebar')
@if(auth()->user()->role_id == 1)
    <x-navigation.admin-sidebar />
@else
    <x-navigation.user-sidebar />
@endif
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        @if ($errors->any())
            <div class="alert alert-danger">
                <h5><i class="icon fas fa-ban"></i> {{ __('models.validation_errors') }}</h5>
                <ul class="mb-0">
                    @foreach ($errors->all() as $error)
                        <li>{{ $error }}</li>
                    @endforeach
                </ul>
            </div>
        @endif
        
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('models.upload_new_model') }}</h3>
            </div>
            <form method="POST" action="{{ route('admin.models.store') }}" enctype="multipart/form-data">
                @csrf
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="MLMName">{{ __('models.model_name_required') }}</label>
                                <input type="text" class="form-control @error('MLMName') is-invalid @enderror" 
                                       id="MLMName" name="MLMName" value="{{ old('MLMName') }}" required>
                                @error('MLMName')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="LibType">{{ __('models.library_type_required') }}</label>
                                <select class="form-control @error('LibType') is-invalid @enderror" id="LibType" name="LibType" required>
                                    <option value="">{{ __('models.select_library_type') }}</option>
                                    <option value="keras" {{ old('LibType') == 'keras' ? 'selected' : '' }}>Keras/TensorFlow</option>
                                    <option value="pytorch" {{ old('LibType') == 'pytorch' ? 'selected' : '' }}>PyTorch</option>
                                    <option value="sklearn" {{ old('LibType') == 'sklearn' ? 'selected' : '' }}>Scikit-learn</option>
                                    <option value="xgboost" {{ old('LibType') == 'xgboost' ? 'selected' : '' }}>XGBoost</option>
                                    <option value="pickle" {{ old('LibType') == 'pickle' ? 'selected' : '' }}>Pickle</option>
                                    <option value="joblib" {{ old('LibType') == 'joblib' ? 'selected' : '' }}>Joblib</option>
                                </select>
                                @error('LibType')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    <div class=row>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="MSEValue">{{ __('models.mse_value') }}</label>
                                <input type="number" step="0.0001" class="form-control @error('MSEValue') is-invalid @enderror" 
                                       id="MSEValue" name="MSEValue" value="{{ old('MSEValue') }}">
                                @error('MSEValue')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="MAEValue">{{ __('models.mae_value') }}</label>
                                <input type="number" step="0.0001" class="form-control @error('MAEValue') is-invalid @enderror" 
                                       id="MAEValue" name="MAEValue" value="{{ old('MAEValue') }}">
                                @error('MAEValue')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="model_file">{{ __('models.model_file_required') }}</label>
                        <input type="file" class="form-control-file @error('model_file') is-invalid @enderror" 
                               id="model_file" name="model_file" accept=".h5,.pkl,.keras,.json,.pt,.pth,.joblib,.xgb" required>
                        <small class="form-text text-muted">
                            <strong>{{ __('models.supported_formats') }}</strong> 
                            <br><strong>Keras:</strong> .keras, .h5, .hdf5
                            <br><strong>PyTorch:</strong> .pt, .pth
                            <br><strong>Sklearn:</strong> .pkl, .joblib
                            <br><strong>XGBoost:</strong> .json, .model, .xgb
                            <br><strong>{{ __('models.max_size') }}</strong> <?php echo ini_get('upload_max_filesize'); ?> ({{ __('models.php_limit') }}) / 100MB ({{ __('models.laravel_limit') }})
                            <br><small class="text-warning">{{ __('models.upload_warning', ['size' => ini_get('upload_max_filesize')]) }}</small>
                        </small>
                        @error('model_file')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <div class="form-check">
                            <input type="checkbox" class="form-check-input" id="IsActive" name="IsActive" value="1" {{ old('IsActive') ? 'checked' : '' }}>
                            <label class="form-check-label" for="IsActive">
                                {{ __('models.set_as_active') }}
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">{{ __('models.upload_model_button') }}</button>
                    <a href="{{ route('admin.models') }}" class="btn btn-secondary">{{ __('cancel') }}</a>
                </div>
            </form>
        </div>
        
        @include('admin.models.php-upload-help')
    </div>
@endsection

@section('scripts')
<script src="{{ asset('js/admin-panel.js') }}"></script>
<script src="{{ asset('js/admin-model-create.js') }}"></script>
@endsection
