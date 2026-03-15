<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title') - {{ config('app.name') }}</title>
    <link rel="icon" type="image/png" href="{{ asset('images/logo-hidro-predict.png') }}">
    
    <!-- Bootstrap CSS -->
    <link href="{{ asset('vendor/bootstrap/css/bootstrap.min.css') }}" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="{{ asset('vendor/bootstrap-icons/bootstrap-icons.min.css') }}" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="{{ asset('vendor/fontawesome/css/all.min.css') }}" rel="stylesheet">
    
    <!-- Common Components CSS -->
        {{-- Custom CSS --}}
    <link rel="stylesheet" href="{{ asset('css/common-components.css') }}">
    <link rel="stylesheet" href="{{ asset('css/utilities.css') }}">

    {{-- Error Page specific styles --}}
    <!-- Error Pages CSS -->
    <link rel="stylesheet" href="{{ asset('css/error-pages.css') }}">
</head>
<body class="error-page">
    <div class="error-page-wrapper">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-lg-6 col-md-8 col-12">
                    <div class="error-card">
                        <div class="error-header text-center mb-4">
                            <div class="error-icon-wrapper mb-3">
                                @yield('error-icon')
                            </div>
                            <h1 class="error-code 
                                @if(View::getSection('error-code') == '404') bg-warning
                                @elseif(View::getSection('error-code') == '403') bg-danger
                                @elseif(View::getSection('error-code') == '500') bg-danger
                                @else bg-primary
                                @endif">@yield('error-code')</h1>
                            <h2 class="error-title">@yield('error-title')</h2>
                            <p class="error-message text-muted">@yield('error-message')</p>
                        </div>
                        
                        <div class="error-body text-center">
                            @yield('error-actions')
                        </div>
                        
                        <div class="error-footer mt-4 pt-3 border-top text-center">
                            <small class="text-muted">
                                <i class="fas fa-clock me-1"></i>
                                If you continue to experience problems, please contact 
                                <a href="mailto:support@hydrogen-mlops.local" class="text-decoration-none">support</a>.
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Background Pattern -->
        <div class="error-bg-pattern"></div>
    </div>

    <!-- Bootstrap JS -->
    <script src="{{ asset('vendor/bootstrap/js/bootstrap.bundle.min.js') }}"></script>
    
    <!-- Error Pages JS -->
    <script src="{{ asset('js/error-pages.js') }}"></script>
    
    @stack('scripts')
</body>
</html>
