@extends('layouts.app')

@section('title', __('permissions.roles_title'))
@section('page-title', __('permissions.roles_title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item active">{{ __('permissions.roles_breadcrumb') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('permissions.manage_roles') }}</h3>
            </div>
            <div class="card-body">
                <p class="text-muted">{{ __('permissions.roles_description') }}</p>
                
                <div class="row">
                    @foreach($roles as $role)
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header bg-primary">
                                <h5 class="mb-0">
                                    <i class="fas fa-shield-alt"></i> {{ $role->RoleName }}
                                    <small class="text-white-50">({{ $role->RoleCode }})</small>
                                </h5>
                            </div>
                            <div class="card-body">
                                <h6>{{ __('permissions.current_permissions') }}:</h6>
                                <div class="mb-3">
                                    @if($role->permissions->count() > 0)
                                        @foreach($role->permissions as $permission)
                                            <span class="badge badge-success mr-1 mb-1">
                                                <i class="fas fa-check"></i> {{ __('permissions.' . $permission->name) }}
                                            </span>
                                        @endforeach
                                    @else
                                        <span class="text-muted">{{ __('permissions.no_permissions') }}</span>
                                    @endif
                                </div>
                                
                                <a href="{{ route('admin.roles.show', $role) }}" class="btn btn-sm btn-primary">
                                    <i class="fas fa-edit"></i> {{ __('permissions.manage_permissions') }}
                                </a>
                                
                                <div class="mt-2">
                                    <small class="text-muted">
                                        {{ __('permissions.users_count') }}: <strong>{{ $role->users->count() }}</strong>
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                    @endforeach
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<script>
    $(function () {
        // Initialize tooltips
        $('[data-toggle="tooltip"]').tooltip();
    });
</script>
@endsection
