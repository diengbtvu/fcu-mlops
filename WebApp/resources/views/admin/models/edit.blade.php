@extends('layouts.app')

@section('title', __('model_edit.title'))
@section('page-title', __('model_edit.title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('model_edit.breadcrumb_dashboard') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.models') }}">{{ __('model_edit.breadcrumb_models') }}</a></li>
    <li class="breadcrumb-item active">{{ __('model_edit.breadcrumb_edit') }}</li>
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
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('model_edit.edit_model') }} {{ $model->MLMName }}</h3>
            </div>
            <form method="POST" action="{{ route('admin.models.update', $model) }}" enctype="multipart/form-data">
                @csrf
                @method('PUT')
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="MLMName">{{ __('model_edit.model_name') }}</label>
                                <input type="text" class="form-control @error('MLMName') is-invalid @enderror" 
                                       id="MLMName" name="MLMName" value="{{ old('MLMName', $model->MLMName) }}" required>
                                @error('MLMName')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="LibType">{{ __('model_edit.library_type') }}</label>
                                <select class="form-control @error('LibType') is-invalid @enderror" id="LibType" name="LibType" required>
                                    <option value="">{{ __('model_edit.select_library') }}</option>
                                    <option value="keras" {{ old('LibType', $model->LibType) == 'keras' ? 'selected' : '' }}>Keras/TensorFlow</option>
                                    <option value="pytorch" {{ old('LibType', $model->LibType) == 'pytorch' ? 'selected' : '' }}>PyTorch</option>
                                    <option value="sklearn" {{ old('LibType', $model->LibType) == 'sklearn' ? 'selected' : '' }}>Scikit-learn</option>
                                    <option value="xgboost" {{ old('LibType', $model->LibType) == 'xgboost' ? 'selected' : '' }}>XGBoost</option>
                                    <option value="pickle" {{ old('LibType', $model->LibType) == 'pickle' ? 'selected' : '' }}>Pickle</option>
                                    <option value="joblib" {{ old('LibType', $model->LibType) == 'joblib' ? 'selected' : '' }}>Joblib</option>
                                </select>
                                @error('LibType')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="MSEValue">{{ __('model_edit.mse_value') }}</label>
                                <input type="number" step="0.0001" class="form-control @error('MSEValue') is-invalid @enderror" 
                                       id="MSEValue" name="MSEValue" value="{{ old('MSEValue', $model->MSEValue) }}">
                                @error('MSEValue')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="MAEValue">{{ __('model_edit.mae_value') }}</label>
                                <input type="number" step="0.0001" class="form-control @error('MAEValue') is-invalid @enderror" 
                                       id="MAEValue" name="MAEValue" value="{{ old('MAEValue', $model->MAEValue) }}">
                                @error('MAEValue')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>{{ __('model_edit.current_file') }}</label>
                        <p><code>{{ $model->FilePath }}</code></p>
                    </div>
                    
                    <div class="form-group">
                        <label for="model_file">{{ __('model_edit.replace_file') }}</label>
                        <input type="file" class="form-control-file @error('model_file') is-invalid @enderror" 
                               id="model_file" name="model_file" accept=".h5,.pkl,.keras,.json,.pt,.pth,.joblib,.xgb">
                        <small class="form-text text-muted">
                            <strong>{{ __('model_edit.supported_formats') }}</strong> 
                            <br><strong>{{ __('model_edit.keras_formats') }}</strong> .keras, .h5, .hdf5
                            <br><strong>{{ __('model_edit.pytorch_formats') }}</strong> .pt, .pth
                            <br><strong>{{ __('model_edit.sklearn_formats') }}</strong> .pkl, .joblib
                            <br><strong>{{ __('model_edit.xgboost_formats') }}</strong> .json, .model, .xgb
                            <br><strong>{{ __('model_edit.max_size') }}</strong> <?php echo ini_get('upload_max_filesize'); ?> ({{ __('model_edit.php_limit') }}) / 100MB ({{ __('model_edit.laravel_limit') }})
                            <br><small class="text-warning">{{ __('model_edit.upload_warning') }} <?php echo ini_get('upload_max_filesize'); ?> ({{ __('model_edit.current_php_limit') }})</small>
                        </small>
                        @error('model_file')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <div class="form-check">
                            <input type="checkbox" class="form-check-input" id="IsActive" name="IsActive" value="1" 
                                   {{ old('IsActive', $model->IsActive) ? 'checked' : '' }}>
                            <label class="form-check-label" for="IsActive">
                                {{ __('model_edit.set_active') }}
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">{{ __('model_edit.update_btn') }}</button>
                    <a href="{{ route('admin.models') }}" class="btn btn-secondary">{{ __('model_edit.cancel') }}</a>
                </div>
            </form>
        </div>
        
        @include('admin.models.php-upload-help')
    </div>
</div>
@endsection

@section('scripts')
<script src="{{ asset('js/admin-panel.js') }}"></script>
<script src="{{ asset('js/admin-model-edit.js') }}"></script>
@endsection
