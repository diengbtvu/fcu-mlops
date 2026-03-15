@extends('layouts.app')

@section('title', __('permissions.edit_role_permissions'))
@section('page-title', __('permissions.edit_role_permissions'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.roles') }}">{{ __('permissions.roles_breadcrumb') }}</a></li>
    <li class="breadcrumb-item active">{{ $role->RoleName }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header bg-primary">
                <h3 class="card-title">
                    <i class="fas fa-shield-alt"></i> {{ __('permissions.edit_permissions_for') }}: {{ $role->RoleName }}
                </h3>
            </div>
            
            <form action="{{ route('admin.roles.permissions.update', $role) }}" method="POST">
                @csrf
                @method('PUT')
                
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> {{ __('permissions.permissions_help') }}
                    </div>

                    <div class="row">
                        @php
                            $permissionGroups = [
                                'user_management' => ['manage_users', 'manage_roles'],
                                'model_management' => ['training_model', 'manage_models'],
                                'dataset_management' => ['manage_dataset'],
                                'prediction' => ['make_predictions', 'view_predictions', 'view_history'],
                            ];
                        @endphp

                        @foreach($permissionGroups as $group => $permNames)
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5 class="mb-0">{{ __('permissions.group_' . $group) }}</h5>
                                    </div>
                                    <div class="card-body">
                                        @foreach($permNames as $permName)
                                            @php
                                                $permission = $allPermissions->firstWhere('name', $permName);
                                            @endphp
                                            @if($permission)
                                                <div class="custom-control custom-switch mb-3">
                                                    <input type="checkbox" 
                                                           class="custom-control-input" 
                                                           id="permission_{{ $permission->id }}" 
                                                           name="permissions[]" 
                                                           value="{{ $permission->id }}"
                                                           {{ $role->permissions->contains($permission->id) ? 'checked' : '' }}>
                                                    <label class="custom-control-label" for="permission_{{ $permission->id }}">
                                                        <strong>{{ __('permissions.' . $permission->name) }}</strong>
                                                        <br>
                                                        <small class="text-muted">{{ __('permissions.' . $permission->name . '_desc') }}</small>
                                                    </label>
                                                </div>
                                            @endif
                                        @endforeach
                                    </div>
                                </div>
                            </div>
                        @endforeach
                    </div>
                </div>

                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> {{ __('permissions.save_permissions') }}
                    </button>
                    <a href="{{ route('admin.roles') }}" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i> {{ __('common.back') }}
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<script>
    $(function () {
        // Select all/none functionality per group
        $('.card').each(function() {
            const card = $(this);
            const checkboxes = card.find('input[type="checkbox"]');
            
            // Add select all button to card header
            if (checkboxes.length > 0) {
                const header = card.find('.card-header');
                const selectAllBtn = $('<button type="button" class="btn btn-sm btn-outline-primary float-right">{{ __('permissions.select_all') }}</button>');
                
                selectAllBtn.click(function() {
                    const allChecked = checkboxes.filter(':checked').length === checkboxes.length;
                    checkboxes.prop('checked', !allChecked);
                    selectAllBtn.text(allChecked ? '{{ __('permissions.select_all') }}' : '{{ __('permissions.deselect_all') }}');
                });
                
                header.append(selectAllBtn);
            }
        });
    });
</script>
@endsection
