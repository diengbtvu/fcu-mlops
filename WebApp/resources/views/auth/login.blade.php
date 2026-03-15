<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Login - Hydrogen Production Rate Prediction System</title>
    <link rel="icon" type="image/png" href="{{ asset('images/logo-hidro-predict.png') }}">
    
    <!-- Bootstrap CSS -->
    <link href="{{ asset('vendor/bootstrap/css/bootstrap.min.css') }}" rel="stylesheet">
    
    <!-- FontAwesome - Toggle between CDN and Static -->
    <!-- CDN Version -->
    <!-- <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"> -->
    <!-- Static Version -->
    <link rel="stylesheet" href="{{ asset('vendor/fontawesome/css/all.min.css') }}">
    
    <!-- AdminLTE - Toggle between CDN and Static -->
    <!-- CDN Version -->
    <!-- <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css"> -->
    <!-- Static Version -->
    <link rel="stylesheet" href="{{ asset('vendor/adminlte/css/adminlte.min.css') }}">
    
    <!-- Login Page CSS -->
    <link rel="stylesheet" href="{{ asset('css/auth-login.css') }}">
</head>
<body class="hold-transition">
    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="spinner"></div>
    </div>

    <section>
        <div class="container-fluid">
            <div class="row login-row">
                <!-- Form Column -->
                <div class="col-lg-4 col-md-6 col-sm-8 d-flex align-items-center justify-content-center login-form-column">
                    <div class="w-100 login-form-container">
                        <div class="card login-card">
                            <div class="card-header login-card-header text-center">
                                <h4 class="mb-3">
                                    Hydrogen Production Rate<br>Prediction System
                                </h4>
                            </div>
                            <div class="card-body login-card-body">
                                <h5 class="text-center mb-4 text-muted">
                                    <i class="fas fa-sign-in-alt me-2"></i>
                                    Sign In to Continue
                                </h5>

                                <form method="POST" action="{{ route('login') }}" id="loginForm">
                                    @csrf
                                    
                                    <div class="form-group mb-3">
                                        <label for="username" class="form-label">
                                            <i class="fas fa-user me-1"></i>
                                            Username
                                        </label>
                                        <input
                                            value="{{ old('username') }}"
                                            type="text"
                                            id="username"
                                            name="username"
                                            class="form-control @error('username') is-invalid @enderror"
                                            placeholder="Enter your username"
                                            required
                                            autofocus
                                            inputmode="latin"
                                            lang="en"
                                            autocomplete="off"
                                            autocorrect="off"
                                            autocapitalize="off"
                                            spellcheck="false"
                                        />
                                        @error('username')
                                            <div class="invalid-feedback">
                                                <i class="fas fa-exclamation-circle me-1"></i>
                                                {{ $message }}
                                            </div>
                                        @enderror
                                    </div>

                                    <div class="form-group mb-4">
                                        <label for="password" class="form-label">
                                            <i class="fas fa-lock me-1"></i>
                                            Password
                                        </label>
                                        <input
                                            type="password"
                                            id="password"
                                            name="password"
                                            class="form-control @error('password') is-invalid @enderror"
                                            placeholder="Enter your password"
                                            required
                                            inputmode="latin"
                                            lang="en"
                                            autocomplete="off"
                                            autocorrect="off"
                                            autocapitalize="off"
                                            spellcheck="false"
                                        />
                                        @error('password')
                                            <div class="invalid-feedback">
                                                <i class="fas fa-exclamation-circle me-1"></i>
                                                {{ $message }}
                                            </div>
                                        @enderror
                                        <div class="text-end mt-2">
                                            <a href="{{ route('password.request') }}" class="text-muted small">
                                                <i class="fas fa-key me-1"></i>
                                                Forgot Password?
                                            </a>
                                        </div>
                                    </div>

                                    <div class="d-grid mb-3">
                                        <button class="btn btn-info btn-login" type="submit">
                                            <i class="fas fa-sign-in-alt me-2"></i>
                                            Sign In
                                        </button>
                                    </div>

                                    @if (session('success'))
                                        <div class="alert alert-success d-flex align-items-center">
                                            <i class="fas fa-check-circle flex-shrink-0 me-2"></i>
                                            <div>{{ session('success') }}</div>
                                        </div>
                                    @endif

                                    @if ($errors->any())
                                        <div class="alert alert-danger d-flex align-items-center">
                                            <i class="fas fa-exclamation-triangle flex-shrink-0 me-2"></i>
                                            <div>
                                                @foreach ($errors->all() as $error)
                                                    {{ $error }}<br>
                                                @endforeach
                                            </div>
                                        </div>
                                    @endif
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Image Column -->
                <div class="col-lg-8 col-md-6 col-sm-4 px-0 d-none d-sm-block image-section full-height">
                    <img src="{{ asset('images/Login-img.jpg') }}"
                        alt="Login image" class="w-100 vh-100 login-image object-cover-left">
                </div>
            </div>
        </div>
    </section>

    <!-- Bootstrap JS -->
    <script src="{{ asset('vendor/bootstrap/js/bootstrap.bundle.min.js') }}"></script>
    
    <!-- AdminLTE JS - Toggle between CDN and Static -->
    <!-- CDN Version -->
    <script src="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/js/adminlte.min.js"></script>
    <!-- Static Version (uncomment to use) -->
    <!-- <script src="{{ asset('vendor/adminlte/js/adminlte.min.js') }}"></script> -->
    
    <!-- Login Page JavaScript -->
    <script src="{{ asset('js/auth-login.js') }}"></script>
</body>
</html>
