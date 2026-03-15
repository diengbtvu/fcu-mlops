@extends('layouts.app')

@section('title', __('profile.title'))
@section('page-title', __('profile.title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item active">{{ __('profile.breadcrumb') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <!-- Profile Information -->
    <div class="col-md-8">
        <div class="card">
            <div class="card-header bg-primary">
                <h3 class="card-title">
                    <i class="fas fa-user-circle"></i> {{ __('profile.profile_information') }}
                </h3>
            </div>
            
            <form action="{{ route('admin.profile.update') }}" method="POST">
                @csrf
                @method('PUT')
                
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="UserCode">{{ __('profile.user_code') }}</label>
                                <input type="text" class="form-control" value="{{ $admin->UserCode }}" disabled>
                                <small class="text-muted">{{ __('profile.user_code_note') }}</small>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="role">{{ __('profile.role') }}</label>
                                <input type="text" class="form-control" value="{{ $admin->role->RoleName }}" disabled>
                                <small class="text-muted">{{ __('profile.role_note') }}</small>
                            </div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="FullName">{{ __('profile.full_name') }} <span class="text-danger">*</span></label>
                        <input type="text" 
                               class="form-control @error('FullName') is-invalid @enderror" 
                               id="FullName" 
                               name="FullName" 
                               value="{{ old('FullName', $admin->FullName) }}" 
                               required>
                        @error('FullName')
                            <span class="invalid-feedback">{{ $message }}</span>
                        @enderror
                    </div>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="Gender">{{ __('profile.gender') }} <span class="text-danger">*</span></label>
                                <select class="form-control @error('Gender') is-invalid @enderror" 
                                        id="Gender" 
                                        name="Gender" 
                                        required>
                                    <option value="Male" {{ old('Gender', $admin->Gender) == 'Male' ? 'selected' : '' }}>{{ __('profile.male') }}</option>
                                    <option value="Female" {{ old('Gender', $admin->Gender) == 'Female' ? 'selected' : '' }}>{{ __('profile.female') }}</option>
                                </select>
                                @error('Gender')
                                    <span class="invalid-feedback">{{ $message }}</span>
                                @enderror
                            </div>
                        </div>

                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="BirthDate">{{ __('profile.birth_date') }} <span class="text-danger">*</span></label>
                                <input type="date" 
                                       class="form-control @error('BirthDate') is-invalid @enderror" 
                                       id="BirthDate" 
                                       name="BirthDate" 
                                       value="{{ old('BirthDate', $admin->BirthDate) }}" 
                                       required>
                                @error('BirthDate')
                                    <span class="invalid-feedback">{{ $message }}</span>
                                @enderror
                            </div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="Address">{{ __('profile.address') }} <span class="text-danger">*</span></label>
                        <textarea class="form-control @error('Address') is-invalid @enderror" 
                                  id="Address" 
                                  name="Address" 
                                  rows="2" 
                                  required>{{ old('Address', $admin->Address) }}</textarea>
                        @error('Address')
                            <span class="invalid-feedback">{{ $message }}</span>
                        @enderror
                    </div>

                    <div class="form-group">
                        <label for="Username">{{ __('profile.username') }} <span class="text-danger">*</span></label>
                        <input type="text" 
                               class="form-control @error('Username') is-invalid @enderror" 
                               id="Username" 
                               name="Username" 
                               value="{{ old('Username', $admin->Username) }}" 
                               required>
                        @error('Username')
                            <span class="invalid-feedback">{{ $message }}</span>
                        @enderror
                    </div>

                    <div class="form-group">
                        <label for="email">{{ __('profile.email') }}</label>
                        <input type="email" 
                               class="form-control @error('email') is-invalid @enderror" 
                               id="email" 
                               name="email" 
                               value="{{ old('email', $admin->email) }}" 
                               placeholder="{{ __('profile.email_placeholder') }}">
                        <small class="text-muted">
                            <i class="fas fa-info-circle"></i> {{ __('profile.email_note') }}
                        </small>
                        @error('email')
                            <span class="invalid-feedback">{{ $message }}</span>
                        @enderror
                    </div>
                </div>

                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> {{ __('profile.update_profile') }}
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Change Password -->
    <div class="col-md-4">
        <div class="card">
            <div class="card-header bg-warning">
                <h3 class="card-title">
                    <i class="fas fa-key"></i> {{ __('profile.change_password') }}
                </h3>
            </div>
            
            <form action="{{ route('admin.profile.password') }}" method="POST">
                @csrf
                @method('PUT')
                
                <div class="card-body">
                    <div class="form-group">
                        <label for="current_password">{{ __('profile.current_password') }} <span class="text-danger">*</span></label>
                        <input type="password" 
                               class="form-control @error('current_password') is-invalid @enderror" 
                               id="current_password" 
                               name="current_password" 
                               required>
                        @error('current_password')
                            <span class="invalid-feedback">{{ $message }}</span>
                        @enderror
                    </div>

                    <div class="form-group">
                        <label for="new_password">{{ __('profile.new_password') }} <span class="text-danger">*</span></label>
                        <input type="password" 
                               class="form-control @error('new_password') is-invalid @enderror" 
                               id="new_password" 
                               name="new_password" 
                               required
                               minlength="6">
                        <small class="text-muted">{{ __('profile.new_password_note') }}</small>
                        @error('new_password')
                            <span class="invalid-feedback">{{ $message }}</span>
                        @enderror
                    </div>

                    <div class="form-group">
                        <label for="new_password_confirmation">{{ __('profile.confirm_password') }} <span class="text-danger">*</span></label>
                        <input type="password" 
                               class="form-control" 
                               id="new_password_confirmation" 
                               name="new_password_confirmation" 
                               required>
                    </div>
                </div>

                <div class="card-footer">
                    <button type="submit" class="btn btn-warning">
                        <i class="fas fa-lock"></i> {{ __('profile.change_password') }}
                    </button>
                </div>
            </form>
        </div>

        <!-- Account Info -->
        <div class="card">
            <div class="card-header bg-info">
                <h3 class="card-title">
                    <i class="fas fa-info-circle"></i> {{ __('profile.account_info') }}
                </h3>
            </div>
            <div class="card-body">
                <dl class="row mb-0">
                    <dt class="col-sm-6">{{ __('profile.account_created') }}:</dt>
                    <dd class="col-sm-6">{{ $admin->created_at->format('M d, Y') }}</dd>
                    
                    <dt class="col-sm-6">{{ __('profile.last_updated') }}:</dt>
                    <dd class="col-sm-6">{{ $admin->updated_at->format('M d, Y') }}</dd>
                    
                    <dt class="col-sm-6">{{ __('profile.total_predictions') }}:</dt>
                    <dd class="col-sm-6">
                        <span class="badge badge-primary">
                            {{ $admin->predictions()->count() }}
                        </span>
                    </dd>
                </dl>
            </div>
        </div>
    </div>
</div>
@endsection
