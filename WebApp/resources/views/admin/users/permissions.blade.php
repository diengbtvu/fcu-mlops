@extends('layouts.app')

@section('title', __('permissions.manage_user_permissions'))
@section('page-title', __('permissions.manage_user_permissions') . ': ' . $user->FullName)

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.users') }}">{{ __('users.breadcrumb') }}</a></li>
    <li class="breadcrumb-item active">{{ __('permissions.manage_user_permissions') }}: {{ $user->FullName }}</li>
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
                    <i class="fas fa-shield-alt"></i> {{ __('permissions.user_specific_permissions_for') }} {{ $user->FullName }}
                </h3>
            </div>
            
            <form action="{{ route('admin.users.permissions.update', $user) }}" method="POST" id="permissionsForm">
                @csrf
                @method('PUT')
                
                <div class="card-body">
                    @if($user->role_id === 1)
                        <div class="alert alert-warning">
                            <i class="fas fa-crown"></i> 
                            <strong>{{ __('permissions.administrator_account') }}</strong><br>
                            {{ __('permissions.admin_all_access_desc') }}
                        </div>
                    @elseif($user->id === Auth::id())
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle"></i> 
                            <strong>{{ __('permissions.warning_edit_own_permissions') }}</strong><br>
                            {{ __('permissions.warning_edit_own_desc') }}
                        </div>
                    @else
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i> 
                            <strong>{{ __('permissions.how_it_works') }}</strong><br>
                            • <strong>{{ __('permissions.default_role') }}</strong> {{ __('permissions.default_role_desc') }} ({{ $user->role->RoleName }})<br>
                            • <strong>✅ {{ __('permissions.grant') }}</strong> {{ __('permissions.grant_desc') }}<br>
                            • <strong>❌ {{ __('permissions.revoke') }}</strong> {{ __('permissions.revoke_desc') }}<br>
                            • {{ __('profile.user_code') }}: <code>{{ $user->UserCode }}</code>
                        </div>
                    @endif

                    {{-- Permission Table with Inline Edit --}}
                    <div class="card mb-4">
                        <div class="card-header bg-light d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">
                                <i class="fas fa-shield-alt"></i> {{ __('permissions.permission_management') }}
                            </h5>
                            <!-- @if($user->role_id !== 1)
                                <button type="button" class="btn btn-sm btn-outline-secondary" id="resetAllBtn">
                                    <i class="fas fa-undo"></i> {{ __('permissions.reset_all_to_defaults') }}
                                </button>
                            @endif -->
                        </div>
                        <div class="card-body p-0">
                            <table class="table table-hover mb-0">
                                <thead class="thead-light">
                                    <tr>
                                        <th style="width: 30%">{{ __('permissions.permission') }}</th>
                                        <th style="width: 15%" class="text-center">{{ __('permissions.role_default') }}<br><small class="text-muted">({{ $user->role->RoleName }})</small></th>
                                        <th style="width: 20%" class="text-center">{{ __('permissions.action') }}</th>
                                        <th style="width: 18%" class="text-center">{{ __('permissions.final_status') }}</th>
                                        <th style="width: 17%">{{ __('permissions.result_source') }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    @php
                                        $allPerms = ['training_model', 'manage_dataset', 'manage_users', 'manage_models', 
                                                     'view_predictions', 'make_predictions', 'view_history', 'manage_roles'];
                                    @endphp
                                    @foreach($allPerms as $permName)
                                        @php
                                            $permission = $allPermissions->firstWhere('name', $permName);
                                            if (!$permission) continue;
                                            
                                            $hasRolePermission = in_array($permission->id, $rolePermissions);
                                            $userOverride = $userPermissions[$permission->id] ?? null;
                                            
                                            // Calculate final status first
                                            if ($userOverride !== null) {
                                                $finalStatus = $userOverride;
                                                $source = __('permissions.user_override');
                                                $sourceClass = 'warning';
                                            } else {
                                                $finalStatus = $hasRolePermission;
                                                $source = __('permissions.role') . ': ' . $user->role->RoleName;
                                                $sourceClass = 'info';
                                            }
                                            
                                            // Determine current state for dropdown based on user override
                                            if ($userOverride !== null) {
                                                // User has explicit override
                                                $currentState = $userOverride ? 'granted' : 'revoked';
                                            } else {
                                                // No override, using role default
                                                $currentState = 'default';
                                            }
                                        @endphp
                                        <tr class="permission-row {{ $userOverride !== null ? 'table-warning-custom' : '' }}" data-permission-id="{{ $permission->id }}">
                                            <td>
                                                <strong>{{ __('permissions.' . $permission->name) }}</strong>
                                                <br>
                                                <small class="text-muted">{{ __('permissions.' . $permission->name . '_desc') }}</small>
                                            </td>
                                            <td class="text-center align-middle">
                                                @if($hasRolePermission)
                                                    <span class="badge badge-success badge-pill">
                                                        <i class="fas fa-check"></i> {{ __('permissions.has') }}
                                                    </span>
                                                @else
                                                    <span class="badge badge-secondary badge-pill">
                                                        <i class="fas fa-times"></i> {{ __('permissions.no') }}
                                                    </span>
                                                @endif
                                            </td>
                                            <td class="text-center align-middle">
                                                @if($user->role_id === 1)
                                                    <span class="badge badge-primary">
                                                        <i class="fas fa-lock"></i> {{ __('permissions.admin_all_access') }}
                                                    </span>
                                                @else
                                                    <select class="form-control form-control-sm permission-select" 
                                                            name="permission_{{ $permission->id }}"
                                                            data-permission-id="{{ $permission->id }}"
                                                            data-role-default="{{ $hasRolePermission ? '1' : '0' }}">
                                                        <option value="default" {{ $currentState === 'default' ? 'selected' : '' }}>
                                                            🔄 {{ __('permissions.use_role_default') }} ({{ $hasRolePermission ? __('permissions.has') : __('permissions.no') }})
                                                        </option>
                                                        <option value="granted" {{ $currentState === 'granted' ? 'selected' : '' }}>
                                                            ✅ {{ __('permissions.grant_access') }}
                                                        </option>
                                                        <option value="revoked" {{ $currentState === 'revoked' ? 'selected' : '' }}>
                                                            ❌ {{ __('permissions.revoke_access') }}
                                                        </option>
                                                    </select>
                                                @endif
                                            </td>
                                            <td class="text-center align-middle final-status">
                                                @if($finalStatus)
                                                    <span class="badge badge-lg badge-success">
                                                        <i class="fas fa-check-circle"></i> {{ __('permissions.has_access') }}
                                                    </span>
                                                @else
                                                    <span class="badge badge-lg badge-danger">
                                                        <i class="fas fa-times-circle"></i> {{ __('permissions.no_access') }}
                                                    </span>
                                                @endif
                                            </td>
                                            <td class="align-middle source-info">
                                                <span class="badge badge-{{ $sourceClass }}">
                                                    <i class="fas fa-{{ $sourceClass === 'warning' ? 'user-edit' : 'users-cog' }}"></i>
                                                    {{ $source }}
                                                </span>
                                            </td>
                                        </tr>
                                    @endforeach
                                </tbody>
                            </table>
                        </div>
                        <div class="card-footer bg-light">
                            <small class="text-muted">
                                <i class="fas fa-info-circle"></i> <strong>{{ __('permissions.legend') }}</strong>
                                🔄 {{ __('permissions.legend_default') }} | 
                                ✅ {{ __('permissions.legend_grant') }} | 
                                ❌ {{ __('permissions.legend_revoke') }}
                            </small>
                        </div>
                    </div>
                </div>

                <div class="card-footer">
                    @if($user->role_id !== 1)
                        <button type="submit" class="btn btn-primary" id="saveBtn">
                            <i class="fas fa-save"></i> {{ __('permissions.save_user_permissions') }}
                        </button>
                    @endif
                    <a href="{{ route('admin.users') }}" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i> {{ __('Back') }}
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<style>
    .badge-lg {
        font-size: 0.85rem;
        padding: 0.4rem 0.6rem;
        font-weight: 600;
    }
    
    .table-hover tbody tr:hover {
        background-color: #f8f9fa;
    }
    
    .permission-select {
        min-width: 200px;
        cursor: pointer;
        font-size: 0.9rem;
    }
    
    .permission-select:focus {
        border-color: #007bff;
        box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
    }
    
    .permission-row {
        transition: background-color 0.2s;
    }
    
    .permission-row:hover {
        background-color: #f8f9fa;
    }
    
    .badge-pill {
        padding: 0.35rem 0.65rem;
    }
    
    .final-status .badge-lg {
        min-width: 120px;
        display: inline-block;
    }
    
    .source-info .badge {
        font-size: 0.75rem;
    }
    
    .thead th {
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
    }
    
    .table-warning-custom {
        background-color: #fff3cd;
        border-left: 3px solid #ffc107;
    }
    
    .table-warning-custom:hover {
        background-color: #ffe69c !important;
    }
</style>

<script>
const isAdmin = {{ $user->role_id === 1 ? 'true' : 'false' }};
const isSelf = {{ $user->id === Auth::id() ? 'true' : 'false' }};

// Translation strings
const translations = {
    hasAccess: {!! json_encode(__('permissions.has_access')) !!},
    noAccess: {!! json_encode(__('permissions.no_access')) !!},
    role: {!! json_encode(__('permissions.role')) !!},
    userOverride: {!! json_encode(__('permissions.user_override')) !!}
};

$(function () {
    console.log('Permission page loaded, found ' + $('.permission-select').length + ' dropdowns');
    
    // Reset All button
    $('#resetAllBtn').click(function() {
        if (confirm({!! json_encode(__('permissions.reset_confirm')) !!})) {
            $('.permission-select').each(function() {
                $(this).val('default').trigger('change');
            });
        }
    });
    
    // Real-time update when dropdown changes
    $('.permission-select').change(function() {
        console.log('Dropdown changed!');
        const $row = $(this).closest('.permission-row');
        const permissionId = $(this).data('permission-id');
        const selectedValue = $(this).val();
        const roleDefault = $(this).data('role-default') === '1';
        
        console.log('Permission ID:', permissionId, 'Selected:', selectedValue, 'Role Default:', roleDefault);
        
        let finalStatus, source, sourceClass;
        
        if (selectedValue === 'default') {
            finalStatus = roleDefault;
            source = translations.role + ': {{ $user->role->RoleName }}';
            sourceClass = 'info';
        } else if (selectedValue === 'granted') {
            finalStatus = true;
            source = translations.userOverride;
            sourceClass = 'warning';
        } else { // revoked
            finalStatus = false;
            source = translations.userOverride;
            sourceClass = 'warning';
        }
        
        // Update Final Status badge
        const $finalStatusCell = $row.find('.final-status');
        if (finalStatus) {
            $finalStatusCell.html(`
                <span class="badge badge-lg badge-success">
                    <i class="fas fa-check-circle"></i> ${translations.hasAccess}
                </span>
            `);
        } else {
            $finalStatusCell.html(`
                <span class="badge badge-lg badge-danger">
                    <i class="fas fa-times-circle"></i> ${translations.noAccess}
                </span>
            `);
        }
        
        // Update Source badge
        const $sourceCell = $row.find('.source-info');
        const icon = sourceClass === 'warning' ? 'user-edit' : 'users-cog';
        $sourceCell.html(`
            <span class="badge badge-${sourceClass}">
                <i class="fas fa-${icon}"></i> ${source}
            </span>
        `);
        
        // Add highlight animation
        if (selectedValue !== 'default') {
            $row.addClass('table-warning-custom');
        } else {
            $row.removeClass('table-warning-custom');
        }
        
        // Temporary flash effect
        $row.addClass('table-info');
        setTimeout(() => $row.removeClass('table-info'), 500);
    });
    
    // Handle form submission
    $('#permissionsForm').submit(function(e) {
        const formData = [];
        
        $('.permission-select').each(function() {
            const permissionId = $(this).data('permission-id');
            const selectedValue = $(this).val();
            
            // Only include overrides (granted/revoked), not default
            if (selectedValue !== 'default') {
                formData.push({
                    permission_id: permissionId,
                    granted: selectedValue === 'granted'
                });
            }
        });
        
        // Clear existing hidden inputs
        $('input[name="permissions"]').remove();
        
        // Add permissions data as hidden input
        if (formData.length > 0) {
            $(this).append(`<input type="hidden" name="permissions" value='${JSON.stringify(formData)}'>`);
        }
    });
});
</script>
@endsection
