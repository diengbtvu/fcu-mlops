@extends('layouts.app')

@section('title', __('user_profile.title'))
@section('page-title', __('user_profile.title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('user.dashboard') }}">{{ __('user_profile.breadcrumb_dashboard') }}</a></li>
    <li class="breadcrumb-item active">{{ __('user_profile.breadcrumb_profile') }}</li>
@endsection

@section('sidebar')
    <x-navigation.user-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('user_profile.profile_information') }}</h3>
            </div>
            <form method="POST" action="{{ route('user.profile.update') }}">
                @csrf
                @method('PUT')
                <div class="card-body">
                    <div class="form-group">
                        <label for="UserCode">{{ __('user_profile.user_code') }}</label>
                        <input type="text" class="form-control" id="UserCode" value="{{ $user->UserCode }}" readonly>
                        <small class="form-text text-muted">{{ __('user_profile.user_code_note') }}</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="FullName">{{ __('user_profile.full_name') }}</label>
                        <input type="text" class="form-control @error('FullName') is-invalid @enderror" 
                               id="FullName" name="FullName" value="{{ old('FullName', $user->FullName) }}" required>
                        @error('FullName')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <label for="Username">{{ __('user_profile.username') }}</label>
                        <input type="text" class="form-control @error('Username') is-invalid @enderror" 
                               id="Username" name="Username" value="{{ old('Username', $user->Username) }}" required>
                        @error('Username')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <label for="Gender">{{ __('user_profile.gender') }}</label>
                        <select class="form-control @error('Gender') is-invalid @enderror" id="Gender" name="Gender" required>
                            <option value="">{{ __('user_profile.select_gender') }}</option>
                            <option value="Male" {{ old('Gender', $user->Gender) == 'Male' ? 'selected' : '' }}>{{ __('user_profile.male') }}</option>
                            <option value="Female" {{ old('Gender', $user->Gender) == 'Female' ? 'selected' : '' }}>{{ __('user_profile.female') }}</option>
                        </select>
                        @error('Gender')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <label for="BirthDate">{{ __('user_profile.birth_date') }}</label>
                        <input type="date" class="form-control @error('BirthDate') is-invalid @enderror" 
                               id="BirthDate" name="BirthDate" value="{{ old('BirthDate', $user->BirthDate) }}" required>
                        @error('BirthDate')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <label for="Address">{{ __('user_profile.address') }}</label>
                        <textarea class="form-control @error('Address') is-invalid @enderror" 
                                  id="Address" name="Address" rows="3" required>{{ old('Address', $user->Address) }}</textarea>
                        @error('Address')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                </div>
                
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">{{ __('user_profile.update_profile') }}</button>
                </div>
            </form>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('user_profile.account_information') }}</h3>
            </div>
            <div class="card-body">
                <table class="table table-borderless">
                    <tr>
                        <td><strong>{{ __('user_profile.user_code') }}</strong></td>
                        <td>{{ $user->UserCode }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ __('user_profile.role') }}</strong></td>
                        <td><span class="badge badge-info">{{ $user->role->RoleName }}</span></td>
                    </tr>
                    <tr>
                        <td><strong>{{ __('user_profile.member_since') }}</strong></td>
                        <td>{{ $user->created_at->format('F d, Y') }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ __('user_profile.last_updated') }}</strong></td>
                        <td>{{ $user->updated_at->format('F d, Y H:i') }}</td>
                    </tr>
                </table>
                
                <hr>
                
                <h5>{{ __('user_profile.account_actions') }}</h5>
                <div class="btn-group-vertical w-100">
                    <a href="{{ route('user.security') }}" class="btn btn-outline-primary">
                        <i class="bi bi-shield-lock"></i> {{ __('user_profile.change_password') }}
                    </a>
                    <a href="{{ route('user.history') }}" class="btn btn-outline-info">
                        <i class="bi bi-clock-history"></i> {{ __('user_profile.view_prediction_history') }}
                    </a>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('user_profile.need_help') }}</h3>
            </div>
            <div class="card-body">
                <p>{{ __('user_profile.need_help_desc') }}</p>
                <p class="text-muted">{{ __('user_profile.tech_support') }}</p>
            </div>
        </div>
    </div>
</div>
@endsection
