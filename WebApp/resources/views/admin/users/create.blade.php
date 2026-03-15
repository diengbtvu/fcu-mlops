@extends('layouts.app')

@section('title', __('users.create_user'))
@section('page-title', __('users.create_user'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('admin.dashboard') }}">{{ __('dashboard.title') }}</a></li>
    <li class="breadcrumb-item"><a href="{{ route('admin.users') }}">{{ __('users.breadcrumb') }}</a></li>
    <li class="breadcrumb-item active">{{ __('users.create_user') }}</li>
@endsection

@section('sidebar')
    <x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('users.create_new_user') }}</h3>
            </div>
            <form method="POST" action="{{ route('admin.users.store') }}">
                @csrf
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        <strong>{{ __('users.note') }}</strong> {{ __('users.usercode_note') }}
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="FullName">{{ __('users.full_name_required') }}</label>
                                <input type="text" class="form-control @error('FullName') is-invalid @enderror" 
                                       id="FullName" name="FullName" value="{{ old('FullName') }}" required>
                                @error('FullName')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="Username">{{ __('users.username_required') }}</label>
                                <input type="text" class="form-control @error('Username') is-invalid @enderror" 
                                       id="Username" name="Username" value="{{ old('Username') }}" required>
                                @error('Username')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="Password">{{ __('users.password_required') }}</label>
                                <input type="password" class="form-control @error('Password') is-invalid @enderror" 
                                       id="Password" name="Password" required>
                                @error('Password')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="Gender">{{ __('users.gender_required') }}</label>
                                <select class="form-control @error('Gender') is-invalid @enderror" id="Gender" name="Gender" required>
                                    <option value="">{{ __('users.select_gender') }}</option>
                                    <option value="Male" {{ old('Gender') == 'Male' ? 'selected' : '' }}>{{ __('users.male') }}</option>
                                    <option value="Female" {{ old('Gender') == 'Female' ? 'selected' : '' }}>{{ __('users.female') }}</option>
                                </select>
                                @error('Gender')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="BirthDate">{{ __('users.birth_date_required') }}</label>
                                <input type="date" class="form-control @error('BirthDate') is-invalid @enderror" 
                                       id="BirthDate" name="BirthDate" value="{{ old('BirthDate') }}" required>
                                @error('BirthDate')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="Address">{{ __('users.address_required') }}</label>
                        <textarea class="form-control @error('Address') is-invalid @enderror" 
                                  id="Address" name="Address" rows="3" required>{{ old('Address') }}</textarea>
                        @error('Address')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                </div>
                
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">{{ __('users.create_user') }}</button>
                    <a href="{{ route('admin.users') }}" class="btn btn-secondary">{{ __('users.cancel') }}</a>
                </div>
            </form>
        </div>
    </div>
</div>
@endsection
