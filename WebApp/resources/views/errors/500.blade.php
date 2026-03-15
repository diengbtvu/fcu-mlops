@extends('layouts.error')

@section('title', '500 - Internal Server Error')
@section('error-code', '500')
@section('error-title', 'Oops! Something went wrong.')
@section('error-message', 'We will work on fixing that right away. Meanwhile, you may return to dashboard or contact support.')

@section('error-icon')
<i class="fas fa-tools text-danger"></i>
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
    
    <button onclick="window.location.reload()" class="btn btn-success btn-lg ms-2">
        <i class="fas fa-redo me-2"></i>
        Try Again
    </button>
</div>

<div class="error-details mt-4">
    <div class="alert alert-light" role="alert">
        <h6><i class="fas fa-info-circle me-1"></i> What can you do?</h6>
        <ul class="mb-0">
            <li>Try refreshing the page</li>
            <li>Go back to the previous page</li>
            <li>Contact support if the problem persists</li>
        </ul>
    </div>
</div>

@if(config('app.debug') && isset($exception))
<div class="error-debug mt-4">
    <div class="alert alert-danger" role="alert">
        <h6><i class="fas fa-bug me-1"></i> Debug Information (Development Mode)</h6>
        <strong>Error:</strong> {{ $exception->getMessage() }}<br>
        <strong>File:</strong> {{ $exception->getFile() }}:{{ $exception->getLine() }}
    </div>
</div>
@endif
@endsection
