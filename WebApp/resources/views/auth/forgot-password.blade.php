<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Forgot Password - Hydrogen MLOps System</title>
    <link rel="icon" type="image/png" href="{{ asset('images/logo-hidro-predict.png') }}">
    
    <link href="{{ asset('vendor/bootstrap/css/bootstrap.min.css') }}" rel="stylesheet">
    <link rel="stylesheet" href="{{ asset('vendor/fontawesome/css/all.min.css') }}">
    <link rel="stylesheet" href="{{ asset('vendor/adminlte/css/adminlte.min.css') }}">
    <link rel="stylesheet" href="{{ asset('css/auth-login.css') }}">
</head>
<body class="hold-transition">
    <section>
        <div class="container-fluid">
            <div class="row login-row">
                <div class="col-lg-4 col-md-6 col-sm-8 d-flex align-items-center justify-content-center login-form-column">
                    <div class="w-100 login-form-container">
                        <div class="card login-card">
                            <div class="card-header login-card-header text-center">
                                <h4 class="mb-3">
                                    Hydrogen Production Rate<br>Prediction System
                                </h4>
                            </div>
                            <div class="card-body login-card-body">
                                <h5 class="text-center mb-2 text-muted">
                                    <i class="fas fa-key me-2"></i>
                                    {{ __('auth.forgot_password_title') }}
                                </h5>
                                <p class="text-center text-muted small mb-4">
                                    {{ __('auth.forgot_password_message') }}
                                </p>

                                @if (session('status'))
                                    <div class="alert alert-success d-flex align-items-center">
                                        <i class="fas fa-check-circle flex-shrink-0 me-2"></i>
                                        <div>{{ session('status') }}</div>
                                    </div>
                                @endif

                                @if (session('error'))
                                    <div class="alert alert-danger d-flex align-items-center">
                                        <i class="fas fa-exclamation-triangle flex-shrink-0 me-2"></i>
                                        <div>{{ session('error') }}</div>
                                    </div>
                                @endif

                                <form method="POST" action="{{ route('password.email') }}">
                                    @csrf
                                    
                                    <div class="form-group mb-4">
                                        <label for="email" class="form-label">
                                            <i class="fas fa-envelope me-1"></i>
                                            {{ __('auth.email_address') }}
                                        </label>
                                        <input
                                            value="{{ old('email') }}"
                                            type="email"
                                            id="email"
                                            name="email"
                                            class="form-control @error('email') is-invalid @enderror"
                                            placeholder="{{ __('auth.enter_email') }}"
                                            required
                                            autofocus
                                        />
                                        @error('email')
                                            <div class="invalid-feedback">
                                                <i class="fas fa-exclamation-circle me-1"></i>
                                                {{ $message }}
                                            </div>
                                        @enderror
                                    </div>

                                    <div class="d-grid mb-3">
                                        <button class="btn btn-info btn-login" type="submit">
                                            <i class="fas fa-paper-plane me-2"></i>
                                            {{ __('auth.send_reset_link') }}
                                        </button>
                                    </div>

                                    <div class="text-center">
                                        <a href="{{ route('login') }}" class="text-muted">
                                            <i class="fas fa-arrow-left me-1"></i>
                                            {{ __('auth.back_to_login') }}
                                        </a>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-8 col-md-6 col-sm-4 px-0 d-none d-sm-block image-section full-height">
                    <img src="{{ asset('images/Login-img.jpg') }}"
                        alt="Login image" class="w-100 vh-100 login-image object-cover-left">
                </div>
            </div>
        </div>
    </section>

    <script src="{{ asset('vendor/bootstrap/js/bootstrap.bundle.min.js') }}"></script>
    <script src="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/js/adminlte.min.js"></script>
</body>
</html>
