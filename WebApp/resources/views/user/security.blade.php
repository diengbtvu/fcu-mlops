@extends('layouts.app')

@section('title', __('security.title'))
@section('page-title', __('security.page_title'))

@section('breadcrumb')
    <li class="breadcrumb-item"><a href="{{ route('user.dashboard') }}">{{ __('security.breadcrumb_dashboard') }}</a></li>
    <li class="breadcrumb-item active">{{ __('security.title') }}</li>
@endsection

@section('sidebar')
    <x-navigation.user-sidebar />
@endsection

@section('content')
<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('security.change_password') }}</h3>
            </div>
            <form method="POST" action="{{ route('user.security.change-password') }}">
                @csrf
                <div class="card-body">
                    <div class="form-group">
                        <label for="current_password">{{ __('security.current_password') }}</label>
                        <input type="password" class="form-control @error('current_password') is-invalid @enderror" 
                               id="current_password" name="current_password" required>
                        @error('current_password')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <label for="new_password">{{ __('security.new_password') }}</label>
                        <input type="password" class="form-control @error('new_password') is-invalid @enderror" 
                               id="new_password" name="new_password" minlength="6" required>
                        <small class="form-text text-muted">{{ __('security.password_length_hint') }}</small>
                        @error('new_password')
                            <div class="invalid-feedback">{{ $message }}</div>
                        @enderror
                    </div>
                    
                    <div class="form-group">
                        <label for="new_password_confirmation">{{ __('security.confirm_new_password') }}</label>
                        <input type="password" class="form-control" 
                               id="new_password_confirmation" name="new_password_confirmation" required>
                    </div>
                </div>
                
                <div class="card-footer">
                    <button type="submit" class="btn btn-primary">{{ __('security.change_password_btn') }}</button>
                    <a href="{{ route('user.profile') }}" class="btn btn-secondary">{{ __('security.cancel') }}</a>
                </div>
            </form>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('security.security_tips') }}</h3>
            </div>
            <div class="card-body">
                <h5><i class="bi bi-shield-check text-success"></i> {{ __('security.password_security') }}</h5>
                <ul class="list-unstyled">
                    <li><i class="bi bi-check text-success"></i> {{ __('security.tip_length') }}</li>
                    <li><i class="bi bi-check text-success"></i> {{ __('security.tip_numbers') }}</li>
                    <li><i class="bi bi-check text-success"></i> {{ __('security.tip_personal') }}</li>
                    <li><i class="bi bi-check text-success"></i> {{ __('security.tip_reuse') }}</li>
                </ul>
                
                <hr>
                
                <h5><i class="bi bi-info-circle text-info"></i> {{ __('security.account_recovery') }}</h5>
                <p class="text-muted">{{ __('security.recovery_desc') }}</p>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">{{ __('security.account_activity') }}</h3>
            </div>
            <div class="card-body">
                <p><strong>{{ __('security.last_login') }}</strong><br>
                <small class="text-muted">{{ Auth::user()->updated_at->format('F d, Y H:i:s') }}</small></p>
                
                <p><strong>{{ __('security.account_created') }}</strong><br>
                <small class="text-muted">{{ Auth::user()->created_at->format('F d, Y') }}</small></p>
                
                <hr>
                
                <div class="text-center">
                    <form method="POST" action="{{ route('logout') }}">
                        @csrf
                        <button type="submit" class="btn btn-outline-danger btn-sm" onclick="return confirm('{{ __('security.logout_confirm') }}')">
                            <i class="bi bi-box-arrow-right"></i> {{ __('security.logout_all') }}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<script src="{{ asset('js/user-forms.js') }}"></script>
@endsection
