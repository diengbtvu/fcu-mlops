@extends('layouts.app')

@section('title', __('users.title'))
@section('page-title', __('users.title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item active">{{ __('users.breadcrumb') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('users.users') }}</h3>
                <div class="card-tools">
                    <a href="{{ route('admin.users.create') }}" class="btn btn-primary btn-sm">
                        <i class="fas fa-plus"></i> {{ __('users.add_user') }}
                    </a>
                </div>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table id="users" class="table table-bordered table-striped">
                        <thead>
                            <tr>
                                <th>{{ __('users.user_code') }}</th>
                                <th>{{ __('users.full_name') }}</th>
                                <th>{{ __('users.username') }}</th>
                                <th>{{ __('users.role') }}</th>
                                <th>{{ __('users.gender') }}</th>
                                <th>{{ __('users.address') }}</th>
                                <th>{{ __('users.predictions') }}</th>
                                <th>{{ __('users.actions') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                        @foreach($users as $user)
                        @php
                            $predictionCount = $user->predictions_count ?? 0;
                            $isCurrentUser = $user->id === Auth::id();
                            $isAdmin = $user->role_id == 1;
                        @endphp
                        <tr class="{{ $isAdmin ? 'table-warning' : '' }} {{ $isCurrentUser ? 'table-info' : '' }}">
                            <td>
                                {{ $user->UserCode }}
                                @if($isCurrentUser)
                                    <span class="badge badge-info badge-sm ms-1">
                                        <i class="fas fa-user"></i> You
                                    </span>
                                @endif
                            </td>
                            <td>{{ $user->FullName }}</td>
                            <td>{{ $user->Username }}</td>
                            <td>
                                <span class="badge {{ $isAdmin ? 'bg-danger' : 'bg-primary' }}">
                                    @if($isAdmin)
                                        <i class="fas fa-crown"></i> {{ __('users.role_admin') }}
                                    @else
                                        <i class="fas fa-user"></i> {{ __('users.role_user') }}
                                    @endif
                                </span>
                            </td>
                            <td>{{ $user->Gender }}</td>
                            <td>{{ $user->Address }}</td>
                            <td>
                                <span class="badge {{ $predictionCount > 0 ? 'bg-warning' : 'bg-light' }}">
                                    {{ $predictionCount }}
                                </span>
                            </td>
                            <td>
                                <div class="btn-group" role="group">
                                    <a href="{{ route('admin.users.edit', $user) }}" 
                                       class="btn btn-sm btn-info"
                                       title="Edit user details">
                                        <i class="fas fa-edit"></i> {{ __('users.edit') }}
                                    </a>
                                    
                                    <button type="button" 
                                            class="btn btn-sm btn-secondary dropdown-toggle dropdown-toggle-split" 
                                            data-bs-toggle="dropdown" 
                                            aria-expanded="false"
                                            title="More actions">
                                        <span class="visually-hidden">Toggle Dropdown</span>
                                    </button>
                                    <ul class="dropdown-menu dropdown-menu-end">
                                        <li>
                                            <h6 class="dropdown-header">
                                                <i class="fas fa-user-cog"></i> {{ $user->FullName }}
                                            </h6>
                                        </li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li>
                                            <a href="{{ route('admin.users.roles', $user) }}" 
                                               class="dropdown-item">
                                                <i class="fas fa-users-cog text-primary"></i> Manage Permission Groups
                                            </a>
                                        </li>
                                        <li>
                                            <a href="{{ route('admin.users.permissions', $user) }}" 
                                               class="dropdown-item">
                                                <i class="fas fa-shield-alt text-success"></i> {{ __('users.manage_permissions') }}
                                            </a>
                                        </li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li>
                                            <form method="POST" action="{{ route('admin.users.reset-password', $user) }}" class="d-inline w-100">
                                                @csrf
                                                <button type="submit" 
                                                        class="dropdown-item {{ $isCurrentUser ? 'disabled' : '' }}" 
                                                        onclick="return {{ $isCurrentUser ? 'false' : 'confirm(\'' . __('users.reset_password_confirm') . '\')' }}"
                                                        {{ $isCurrentUser ? 'disabled' : '' }}>
                                                    <i class="fas fa-key text-warning"></i> {{ __('users.reset') }} Password
                                                    @if($isCurrentUser)
                                                        <span class="badge badge-secondary badge-sm ms-1">You</span>
                                                    @endif
                                                </button>
                                            </form>
                                        </li>
                                        <li><hr class="dropdown-divider"></li>
                                        <li>
                                            <button type="button" 
                                                    class="dropdown-item {{ $isCurrentUser ? 'disabled' : ($predictionCount > 0 ? 'text-warning' : 'text-danger') }}" 
                                                    data-bs-toggle="modal" 
                                                    data-bs-target="#deleteModal{{ $user->id }}"
                                                    {{ $isCurrentUser ? 'disabled' : '' }}>
                                                <i class="fas fa-trash"></i> {{ __('users.delete') }}
                                                @if($predictionCount > 0)
                                                    <span class="badge badge-warning badge-sm ms-1">{{ $predictionCount }}</span>
                                                @endif
                                                @if($isCurrentUser)
                                                    <span class="badge badge-secondary badge-sm ms-1">You</span>
                                                @endif
                                            </button>
                                        </li>
                                    </ul>
                                </div>
                            </td>
                        </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
            <div class="card-footer">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <small class="text-muted">
                            Showing {{ $users->firstItem() ?? 0 }} to {{ $users->lastItem() ?? 0 }} of {{ $users->total() }} users
                        </small>
                    </div>
                    <div class="col-md-6">
                        <div class="d-flex justify-content-end">
                            {{ $users->links() }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Delete Modals -->
@foreach($users as $user)
    @php
        $predictionCount = $user->predictions()->count();
    @endphp
    
    <div class="modal fade" id="deleteModal{{ $user->id }}" tabindex="-1" 
         aria-labelledby="deleteModalLabel{{ $user->id }}" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header {{ $predictionCount > 0 ? 'bg-warning' : 'bg-danger' }} text-white">
                    <h5 class="modal-title" id="deleteModalLabel{{ $user->id }}">
                        <i class="fas fa-exclamation-triangle"></i>
                        {{ __('users.delete_user_title', ['name' => $user->FullName]) }}
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    @if($predictionCount > 0)
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle"></i>
                            <strong>{{ __('users.warning') }}</strong> {{ __('users.user_has_predictions', ['count' => $predictionCount]) }}
                        </div>
                        
                        <p>{{ __('users.choose_proceed') }}</p>
                        
                        <div class="row g-2">
                            <div class="col-12 col-md-4">
                                <div class="card border-secondary h-100">
                                    <div class="card-body text-center d-flex flex-column">
                                        <h6 class="card-title text-secondary">
                                            <i class="fas fa-shield-alt"></i> {{ __('users.safe_option') }}
                                        </h6>
                                        <p class="card-text small flex-grow-1">{{ __('users.safe_option_desc') }}</p>
                                        <button type="button" class="btn btn-secondary btn-sm mt-auto" data-bs-dismiss="modal">
                                            <i class="fas fa-arrow-left"></i> {{ __('users.cancel') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="col-12 col-md-4">
                                <div class="card border-warning h-100">
                                    <div class="card-body text-center d-flex flex-column">
                                        <h6 class="card-title text-warning">
                                            <i class="fas fa-eye-slash"></i> {{ __('users.anonymize') }}
                                        </h6>
                                        <p class="card-text small flex-grow-1">{{ __('users.anonymize_desc') }}</p>
                                        <form method="POST" action="{{ route('admin.users.anonymize', $user) }}" class="d-inline mt-auto">
                                            @csrf
                                            <button type="submit" class="btn btn-warning btn-sm" 
                                                    onclick="return confirm('{{ __('users.anonymize_confirm', ['count' => $predictionCount]) }}')">
                                                <i class="fas fa-eye-slash"></i> {{ __('users.anonymize') }}
                                            </button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                            <div class="col-12 col-md-4">
                                <div class="card border-danger h-100">
                                    <div class="card-body text-center d-flex flex-column">
                                        <h6 class="card-title text-danger">
                                            <i class="fas fa-exclamation-triangle"></i> {{ __('users.force_delete') }}
                                        </h6>
                                        <p class="card-text small flex-grow-1">{{ __('users.force_delete_desc', ['count' => $predictionCount]) }}</p>
                                        <form method="POST" action="{{ route('admin.users.force-delete', $user) }}" class="d-inline mt-auto">
                                            @csrf
                                            @method('DELETE')
                                            <button type="submit" class="btn btn-danger btn-sm" 
                                                    onclick="return confirm('{{ __('users.force_delete_confirm', ['count' => $predictionCount]) }}')">
                                                <i class="fas fa-trash"></i> {{ __('users.force_delete') }}
                                            </button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="fas fa-info-circle"></i>
                                <strong>{{ __('users.recommendation') }}</strong> {{ __('users.recommendation_text') }}
                            </small>
                        </div>
                    @else
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i>
                            {{ __('users.no_predictions') }}
                        </div>
                        
                        <p>{{ __('users.confirm_delete', ['name' => $user->FullName]) }}</p>
                        <p class="text-muted small">{{ __('users.delete_warning') }}</p>
                    @endif
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        <i class="fas fa-times"></i> {{ __('users.cancel') }}
                    </button>
                    @if($predictionCount == 0)
                        <form method="POST" action="{{ route('admin.users.delete', $user) }}" class="d-inline">
                            @csrf
                            @method('DELETE')
                            <button type="submit" class="btn btn-danger">
                                <i class="fas fa-trash"></i> {{ __('users.delete_user') }}
                            </button>
                        </form>
                    @endif
                </div>
            </div>
        </div>
    </div>
@endforeach
@endsection

@section('styles')
<link rel="stylesheet" href="{{ asset('css/admin-user-management.css') }}">
<link rel="stylesheet" href="{{ asset('css/admin-tables.css') }}">
<style>
    .table-warning {
        background-color: #fff3cd !important;
        border-left: 3px solid #ffc107;
    }
    
    .table-info {
        background-color: #d1ecf1 !important;
        border-left: 3px solid #17a2b8;
    }
    
    .badge-sm {
        font-size: 0.7rem;
        padding: 0.2rem 0.4rem;
    }
    
    .dropdown-item.disabled {
        opacity: 0.5;
        cursor: not-allowed;
        pointer-events: none;
    }
    
    .btn-group .btn {
        border-radius: 0;
    }
    
    .btn-group .btn:first-child {
        border-top-left-radius: 0.25rem;
        border-bottom-left-radius: 0.25rem;
    }
    
    .btn-group .dropdown-toggle {
        border-top-right-radius: 0.25rem;
        border-bottom-right-radius: 0.25rem;
    }
    
    .dropdown-menu {
        min-width: 220px;
    }
</style>
@endsection

@section('scripts')
<script src="{{ asset('js/admin-users-table.js') }}"></script>
<script src="{{ asset('js/admin-panel.js') }}"></script>
<script>
$(document).ready(function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
</script>
@endsection
