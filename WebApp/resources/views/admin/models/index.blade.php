@extends('layouts.app')

@section('title', __('models.ml_models'))
@section('page-title', __('models.ml_models'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item active">{{ __('nav.models') }}</li>
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
                <h3 class="card-title">{{ __('models.machine_learning_models') }}</h3>
                <div class="card-tools">
                    <a href="{{ route('admin.models.create') }}" class="btn btn-primary btn-sm">
                        <i class="bi bi-plus"></i> {{ __('models.add_model') }}
                    </a>
                    <a href="{{ route('admin.models.compare') }}" class="btn btn-success btn-sm">
                        <i class="bi bi-bar-chart-line"></i> {{ __('models.compare_models') }}
                    </a>
                    <a href="http://127.0.0.1:5001" class="btn btn-secondary btn-sm" target="_blank">
                        <i class="bi bi-graph-up"></i> {{ __('models.mlflow_ui') }}
                    </a>
                </div>
            </div>
            <div class="card-body">
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    <strong>{{ __('note') }}:</strong> {{ __('models.default_model_note') }}
                </div>
                
                <div class="table-responsive">
                    <table id="models-table" class="table table-bordered table-striped">
                        <thead>
                            <tr>
                                <th>{{ __('models.name') }}</th>                            
                                <th>{{ __('models.library_type') }}</th>
                                <th>{{ __('models.dataset') }}</th>
                                <th>MSE</th>
                                <th>MAE</th>
                                <th>{{ __('models.status') }}</th>
                                <th>{{ __('models.predictions') }}</th>
                                <th>{{ __('models.actions') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            @foreach($models as $model)
                            <tr>
                                <td>
                                    {{ $model->MLMName }}
                                    @php
                                        $isDefault = $model->id === 1;
                                    @endphp
                                    @if($isDefault)
                                        <span class="badge badge-primary ms-1">
                                            <i class="bi bi-star"></i> {{ __('models.default_badge') }}
                                        </span>
                                    @endif
                                </td>
                                <td>
                                    <span class="badge badge-info">{{ $model->LibType }}</span>
                                </td>
                                <td>
                                    @if($model->dataset)
                                        <span class="badge badge-secondary">
                                            <i class="bi bi-database"></i> {{ $model->dataset->DatasetName }}
                                        </span>
                                    @else
                                        <span class="text-muted">{{ __('models.na') }}</span>
                                    @endif
                                </td>
                                <td>
                                    @if($model->MSEValue !== null)
                                        {{ number_format($model->MSEValue, 4) }}
                                    @else
                                        <span class="text-muted">{{ __('models.na') }}</span>
                                    @endif
                                </td>
                                <td>
                                    @if($model->MAEValue !== null)
                                        {{ number_format($model->MAEValue, 4) }}
                                    @else
                                        <span class="text-muted">{{ __('models.na') }}</span>
                                    @endif
                                </td>
                                <td>
                                    @if($model->IsActive)
                                        <span class="badge badge-success">{{ __('active') }}</span>
                                    @else
                                        <span class="badge badge-secondary">{{ __('inactive') }}</span>
                                    @endif
                                </td>
                                <td>
                                    @php
                                        $predictionCount = $model->predictions()->count();
                                    @endphp
                                    <span class="badge {{ $predictionCount > 0 ? 'badge-warning' : 'badge-light' }}">
                                        {{ $predictionCount }}
                                    </span>
                                </td>
                                <td>
                                    <div class="d-flex flex-wrap gap-1">
                                        <a href="{{ route('admin.models.report', $model) }}" class="btn btn-sm btn-primary">
                                            <i class="bi bi-bar-chart-line"></i> {{ __('view') }} Report
                                        </a>
                                        <a href="{{ route('admin.models.edit', $model) }}" class="btn btn-sm btn-info">
                                            <i class="bi bi-pencil"></i> {{ __('models.edit') }}
                                        </a>
                                        
                                        @php
                                            $predictionCount = $model->predictions()->count();
                                            $isDefault = $model->id === 1;
                                        @endphp
                                        
                                        @if($isDefault)
                                            <button type="button" class="btn btn-sm btn-secondary" disabled title="{{ __('models.cannot_delete_default') }}">
                                                <i class="bi bi-shield-lock"></i> {{ __('models.protected') }}
                                            </button>
                                        @else
                                            <button type="button" class="btn btn-sm {{ $predictionCount > 0 ? 'btn-warning' : 'btn-danger' }}" 
                                                    data-bs-toggle="modal" data-bs-target="#deleteModal{{ $model->id }}">
                                                <i class="bi bi-trash"></i> 
                                                {{ __('models.delete') }} {{ $predictionCount > 0 ? "({$predictionCount})" : '' }}
                                            </button>
                                        @endif
                                    </div>
                                </td>
                            </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
                
                <!-- Pagination -->
                <div class="d-flex justify-content-center">
                    {{ $models->links() }}
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Delete Modals -->
@foreach($models as $model)
    @php
        $predictionCount = $model->predictions()->count();
        $isDefault = $model->id === 1;
    @endphp
    
    @if(!$isDefault)
    <div class="modal fade" id="deleteModal{{ $model->id }}" tabindex="-1" 
         aria-labelledby="deleteModalLabel{{ $model->id }}" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header {{ $predictionCount > 0 ? 'bg-warning' : 'bg-danger' }} text-white">
                    <h5 class="modal-title" id="deleteModalLabel{{ $model->id }}">
                        <i class="bi bi-exclamation-triangle"></i>
                        {{ __('models.delete_model') }}: <span class="text-wrap">{{ $model->MLMName }}</span>
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    @if($predictionCount > 0)
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle"></i>
                            <strong>{{ __('models.warning') }}</strong> {{ __('models.associated_predictions', ['count' => $predictionCount]) }}
                        </div>
                        
                        <p>{{ __('models.choose_proceed') }}</p>
                        
                        <div class="row g-2">
                            <div class="col-12 col-md-4">
                                <div class="card border-secondary h-100">
                                    <div class="card-body text-center d-flex flex-column">
                                        <h6 class="card-title text-secondary">
                                            <i class="bi bi-shield-check"></i> {{ __('models.safe_option') }}
                                        </h6>
                                        <p class="card-text small flex-grow-1">{{ __('models.cancel_deletion') }}</p>
                                        <button type="button" class="btn btn-secondary btn-sm mt-auto" data-bs-dismiss="modal">
                                            <i class="bi bi-arrow-left"></i> {{ __('cancel') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="col-12 col-md-4">
                                <div class="card border-warning h-100">
                                    <div class="card-body text-center d-flex flex-column">
                                        <h6 class="card-title text-warning">
                                            <i class="bi bi-pause-circle"></i> {{ __('models.deactivate') }}
                                        </h6>
                                        <p class="card-text small flex-grow-1">{{ __('models.deactivate_desc') }}</p>
                                        <form method="POST" action="{{ route('admin.models.update', $model) }}" class="d-inline mt-auto">
                                            @csrf
                                            @method('PUT')
                                            <input type="hidden" name="MLMName" value="{{ $model->MLMName }}">
                                            <input type="hidden" name="LibType" value="{{ $model->LibType }}">
                                            <!-- Don't include IsActive checkbox to make it false -->
                                            <button type="submit" class="btn btn-warning btn-sm">
                                                <i class="bi bi-pause"></i> {{ __('models.deactivate') }}
                                            </button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                            <div class="col-12 col-md-4">
                                <div class="card border-danger h-100">
                                    <div class="card-body text-center d-flex flex-column">
                                        <h6 class="card-title text-danger">
                                            <i class="bi bi-exclamation-triangle"></i> {{ __('models.force_delete') }}
                                        </h6>
                                        <p class="card-text small flex-grow-1">{{ __('models.force_delete_desc', ['count' => $predictionCount]) }}</p>
                                        <form method="POST" action="{{ route('admin.models.force-delete', $model) }}" class="d-inline mt-auto">
                                            @csrf
                                            @method('DELETE')
                                            <button type="submit" class="btn btn-danger btn-sm" 
                                                    onclick="return confirm(@js(__('models.force_delete_warning', ['count' => $predictionCount])))">
                                                <i class="bi bi-trash"></i> {{ __('models.force_delete') }}
                                            </button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="bi bi-info-circle"></i>
                                <strong>{{ __('messages.alternative') }}:</strong> {{ __('models.alternative_tip') }}
                            </small>
                        </div>
                    @else
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i>
                            {{ __('models.no_predictions') }}
                        </div>
                        
                        <p>{{ __('models.confirm_delete') }} <strong>"{{ $model->MLMName }}"</strong>?</p>
                        <p class="text-muted small">{{ __('models.delete_permanent') }}</p>
                    @endif
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        <i class="bi bi-x"></i> {{ __('cancel') }}
                    </button>
                    @if($predictionCount == 0)
                        <form method="POST" action="{{ route('admin.models.delete', $model) }}" class="d-inline">
                            @csrf
                            @method('DELETE')
                            <button type="submit" class="btn btn-danger">
                                <i class="bi bi-trash"></i> {{ __('models.delete_model') }}
                            </button>
                        </form>
                    @endif
                </div>
            </div>
        </div>
    </div>
    @endif
@endforeach
@endsection

@section('styles')
<link rel="stylesheet" href="{{ asset('css/admin-tables.css') }}">
@endsection

@section('scripts')
<script src="{{ asset('js/admin-models-table.js') }}"></script>
<script src="{{ asset('js/admin-panel.js') }}"></script>
<script>
// Initialize admin panel after DataTable
$(document).ready(function() {
    // Wait for DataTable initialization
    setTimeout(function() {
        if (typeof AdminPanel !== 'undefined') {
            window.adminPanel = new AdminPanel('models');
        }
    }, 100);
});
</script>
@endsection
