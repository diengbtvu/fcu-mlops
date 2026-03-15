@extends('layouts.app')

@section('title', 'Manage Permission Groups')
@section('page-title', 'Manage Permission Groups: ' . $user->FullName)

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.users') }}">{{ __('users.breadcrumb') }}</a></li>
    <li class="breadcrumb-item active">Permission Groups: {{ $user->FullName }}</li>
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
                    <i class="fas fa-users-cog"></i> Permission Groups for {{ $user->FullName }}
                </h3>
            </div>
            
            <form action="{{ route('admin.users.roles.update', $user) }}" method="POST" id="rolesForm">
                @csrf
                @method('PUT')
                
                <div class="card-body">
                    @if($user->role_id === 1)
                        <div class="alert alert-warning">
                            <i class="fas fa-crown"></i> 
                            <strong>Administrator Account</strong><br>
                            This is an administrator account. Administrators automatically have all permissions and do not need permission groups.
                        </div>
                    @else
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i> 
                            <strong>How Permission Groups Work</strong><br>
                            • A user can be assigned to <strong>multiple permission groups</strong><br>
                            • Each group grants specific permissions to the user<br>
                            • Users will have access to <strong>all permissions</strong> from their assigned groups<br>
                            • User Code: <code>{{ $user->UserCode }}</code>
                        </div>

                        <div class="mb-4">
                            <h5 class="mb-3">
                                <i class="fas fa-info-circle"></i> Current Role: 
                                <span class="badge badge-info">{{ $user->role->RoleName }}</span>
                            </h5>
                            <p class="text-muted">
                                The user's base role provides default permissions. You can assign additional permission groups below.
                            </p>
                        </div>

                        <hr>

                        <h5 class="mb-3"><i class="fas fa-layer-group"></i> Available Permission Groups</h5>
                        <p class="text-muted mb-4">Select one or more permission groups to assign to this user:</p>

                        <div class="row">
                            @foreach($permissionGroups as $group)
                            <div class="col-md-6 mb-3">
                                <div class="card h-100 {{ in_array($group->id, $assignedRoleIds) ? 'border-success' : 'border-secondary' }}">
                                    <div class="card-header {{ in_array($group->id, $assignedRoleIds) ? 'bg-success' : 'bg-secondary' }}">
                                        <div class="custom-control custom-checkbox">
                                            <input 
                                                type="checkbox" 
                                                class="custom-control-input role-checkbox" 
                                                id="role_{{ $group->id }}" 
                                                name="roles[]" 
                                                value="{{ $group->id }}"
                                                {{ in_array($group->id, $assignedRoleIds) ? 'checked' : '' }}
                                            >
                                            <label class="custom-control-label" for="role_{{ $group->id }}">
                                                <strong>{{ $group->RoleName }}</strong>
                                                <small class="d-block text-white-50">{{ $group->RoleCode }}</small>
                                            </label>
                                        </div>
                                    </div>
                                    <div class="card-body">
                                        <h6 class="mb-2">Permissions in this group:</h6>
                                        <ul class="list-unstyled mb-0">
                                            @forelse($group->permissions as $permission)
                                                <li class="mb-1">
                                                    <i class="fas fa-check text-success"></i> 
                                                    {{ __('permissions.' . $permission->name) }}
                                                </li>
                                            @empty
                                                <li class="text-muted">No permissions assigned</li>
                                            @endforelse
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            @endforeach
                        </div>

                        @if($permissionGroups->isEmpty())
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle"></i> 
                                No permission groups available. Please create permission groups first.
                            </div>
                        @endif
                    @endif
                </div>
                
                @if($user->role_id !== 1)
                <div class="card-footer">
                    <button type="submit" class="btn btn-success" id="saveButton">
                        <i class="fas fa-save"></i> Save Permission Groups
                    </button>
                    <a href="{{ route('admin.users') }}" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i> Back to Users
                    </a>
                    <a href="{{ route('admin.users.permissions', $user) }}" class="btn btn-info">
                        <i class="fas fa-shield-alt"></i> Manage Individual Permissions
                    </a>
                </div>
                @endif
            </form>
        </div>

        @if($user->role_id !== 1)
        <!-- Current Assignments Summary -->
        <div class="card mt-4">
            <div class="card-header bg-info">
                <h4 class="card-title mb-0">
                    <i class="fas fa-list-check"></i> Current Permission Summary
                </h4>
            </div>
            <div class="card-body">
                <h5>Assigned Permission Groups:</h5>
                @if($user->roles->isEmpty())
                    <p class="text-muted">No permission groups assigned yet.</p>
                @else
                    <div class="row">
                        @foreach($user->roles as $role)
                        <div class="col-md-4 mb-2">
                            <span class="badge badge-success badge-lg p-2">
                                <i class="fas fa-layer-group"></i> {{ $role->RoleName }}
                            </span>
                        </div>
                        @endforeach
                    </div>
                @endif

                <hr>

                <h5 class="mt-3">All Available Permissions from Assigned Groups:</h5>
                @php
                    $allPermissions = collect();
                    foreach($user->roles as $role) {
                        $allPermissions = $allPermissions->merge($role->permissions);
                    }
                    $allPermissions = $allPermissions->unique('id');
                @endphp

                @if($allPermissions->isEmpty())
                    <p class="text-muted">No permissions from groups. The user only has permissions from their base role: <strong>{{ $user->role->RoleName }}</strong></p>
                @else
                    <div class="row">
                        @foreach($allPermissions as $permission)
                        <div class="col-md-4 mb-2">
                            <span class="badge badge-primary p-2">
                                <i class="fas fa-check"></i> {{ __('permissions.' . $permission->name) }}
                            </span>
                        </div>
                        @endforeach
                    </div>
                @endif
            </div>
        </div>
        @endif
    </div>
</div>
@endsection

@section('scripts')
<script>
$(document).ready(function() {
    // Add visual feedback when checkboxes are toggled
    $('.role-checkbox').on('change', function() {
        const card = $(this).closest('.card');
        const cardHeader = card.find('.card-header');
        
        if ($(this).is(':checked')) {
            card.removeClass('border-secondary').addClass('border-success');
            cardHeader.removeClass('bg-secondary').addClass('bg-success');
        } else {
            card.removeClass('border-success').addClass('border-secondary');
            cardHeader.removeClass('bg-success').addClass('bg-secondary');
        }
    });

    // Form submission confirmation
    $('#rolesForm').on('submit', function(e) {
        const checkedCount = $('.role-checkbox:checked').length;
        const message = checkedCount === 0 
            ? 'Are you sure you want to remove all permission groups from this user?' 
            : `Are you sure you want to assign ${checkedCount} permission group(s) to this user?`;
        
        if (!confirm(message)) {
            e.preventDefault();
        }
    });
});
</script>
@endsection

@section('styles')
<style>
.badge-lg {
    font-size: 1rem;
    font-weight: normal;
}

.card.border-success,
.card.border-secondary {
    border-width: 2px !important;
}

.custom-control-label {
    cursor: pointer;
    width: 100%;
}

.card-header .custom-control {
    margin: 0;
}

.card-header .custom-control-label {
    padding-top: 0.125rem;
}
</style>
@endsection
