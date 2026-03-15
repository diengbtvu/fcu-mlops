@extends('layouts.error')

@section('title', '404 - Page Not Found')
@section('error-code', '404')
@section('error-title', 'Oops! Page not found.')
@section('error-message', 'We could not find the page you were looking for. Meanwhile, you may return to dashboard or try using the search form.')

@section('error-icon')
<i class="fas fa-exclamation-triangle text-warning"></i>
@endsection

@section('error-actions')
<div class="error-actions">
    <a href="{{ Auth::check() ? (Auth::user()->RoleID == 1 ? route('admin.dashboard') : route('user.dashboard')) : route('login') }}" 
       class="btn btn-primary btn-lg">
        <i class="fas fa-home me-2"></i>
        @if(Auth::check())
            @if(Auth::user()->RoleID == 1)
                Admin Dashboard
            @else
                User Dashboard
            @endif
        @else
            Go to Login
        @endif
    </a>
    
    <button onclick="history.back()" class="btn btn-secondary btn-lg ms-2">
        <i class="fas fa-arrow-left me-2"></i>
        Go Back
    </button>
</div>

<div class="error-search mt-4">
    <form action="{{ route('search') }}" method="GET" class="d-flex" role="search">
        <input type="search" name="q" class="form-control form-control-lg me-2" 
               placeholder="Search for something..." value="{{ request('q') }}">
        <button type="submit" class="btn btn-outline-primary btn-lg">
            <i class="fas fa-search"></i>
        </button>
    </form>
</div>
@endsection
