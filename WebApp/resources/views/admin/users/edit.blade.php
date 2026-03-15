@extends('layouts.app')

@section('title', 'Edit User')
@section('page-title', 'Edit User')

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">Dashboard</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.users') }}">Users</a></li>
    <li class="breadcrumb-item active">Edit</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Edit User: {{ $user->FullName }}</h3>
            </div>
            <form method="POST" action="{{ route('admin.users.update', $user) }}">
                @csrf
                @method('PUT')
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="UserCode">User Code</label>
                                <input type="text" class="form-control" 
                                       id="UserCode" name="UserCode" value="{{ $user->UserCode }}" readonly>
                                <small class="form-text text-muted">UserCode cannot be changed after creation</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="FullName">Full Name *</label>
                                <input type="text" class="form-control @error('FullName') is-invalid @enderror" 
                                       id="FullName" name="FullName" value="{{ old('FullName', $user->FullName) }}" required>
                                @error('FullName')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="Username">Username *</label>
                                <input type="text" class="form-control @error('Username') is-invalid @enderror" 
                                       id="Username" name="Username" value="{{ old('Username', $user->Username) }}" required>
                                @error('Username')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="Gender">Gender *</label>
                                <select class="form-control @error('Gender') is-invalid @enderror" id="Gender" name="Gender" required>
                                    <option value="">Select Gender</option>
                                    <option value="Male" {{ old('Gender', $user->Gender) == 'Male' ? 'selected' : '' }}>Male</option>
                                    <option value="Female" {{ old('Gender', $user->Gender) == 'Female' ? 'selected' : '' }}>Female</option>
                                </select>
                                @error('Gender')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="role_id">{{ __('users.role_required') }}</label>
                                <select class="form-control @error('role_id') is-invalid @enderror" id="role_id" name="role_id" required>
                                    <option value="">{{ __('users.select_role') }}</option>
                                    <option value="1" {{ old('role_id', $user->role_id) == 1 ? 'selected' : '' }}>{{ __('users.role_admin') }}</option>
                                    <option value="2" {{ old('role_id', $user->role_id) == 2 ? 'selected' : '' }}>{{ __('users.role_user') }}</option>
                                </select>
                                @error('role_id')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                                <small class="form-text text-muted">
                                    <i class="fas fa-info-circle"></i> {{ __('users.role_admin') }}: Full system access | {{ __('users.role_user') }}: Limited access
                                </small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="BirthDate">Birth Date *</label>
                                <input type="date" class="form-control @error('BirthDate') is-invalid @enderror" 
                                       id="BirthDate" name="BirthDate" value="{{ old('BirthDate', $user->BirthDate) }}" required>
                                @error('BirthDate')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-group">
                                <label for="Address">Address *</label>
                                <textarea class="form-control @error('Address') is-invalid @enderror" 
                                          id="Address" name="Address" rows="3" required>{{ old('Address', $user->Address) }}</textarea>
                                @error('Address')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">Update User</button>
                    <a href="{{ route('admin.users') }}" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
    </div>
</div>
@endsection
