<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>403 - Access Forbidden</title>
    <link href="{{ asset('vendor/bootstrap/css/bootstrap.min.css') }}" rel="stylesheet">
    <link href="{{ asset('vendor/fontawesome/css/all.min.css') }}" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-danger text-white text-center">
                        <h1 class="display-4">403</h1>
                        <h4>
                            @if(isset($role_mismatch) && $role_mismatch)
                                Role Permission Mismatch
                            @else
                                Access Forbidden
                            @endif
                        </h4>
                    </div>
                    <div class="card-body text-center">
                        @if(isset($role_mismatch) && $role_mismatch)
                            <!-- Role Mismatch Content -->
                            <div class="alert alert-warning" role="alert">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                <strong>Hello {{ $user_name ?? 'User' }}!</strong><br>
                                You need different role permissions to access this page.
                            </div>

                            @if(isset($current_role) && isset($required_role))
                            <div class="mb-4">
                                <p class="mb-3"><strong>Permission Details:</strong></p>
                                <div class="mb-3">
                                    <span class="badge bg-secondary fs-6 me-2">
                                        <i class="fas fa-user-circle me-1"></i>
                                        Your Role: {{ strtoupper($current_role) }}
                                    </span>
                                    <span class="badge bg-danger fs-6">
                                        <i class="fas fa-shield-alt me-1"></i>
                                        Required: {{ strtoupper($required_role) }}
                                    </span>
                                </div>
                            </div>
                            @endif

                            <div class="d-grid gap-2 d-md-flex justify-content-md-center">
                                <button type="button" class="btn btn-secondary" onclick="history.back()">
                                    <i class="fas fa-arrow-left me-2"></i>
                                    Go Back
                                </button>
                                
                                <button type="button" class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#logoutModal">
                                    <i class="fas fa-sign-out-alt me-2"></i>
                                    Logout & Switch
                                </button>
                            </div>

                            <!-- Logout Modal -->
                            <div class="modal fade" id="logoutModal" tabindex="-1" aria-hidden="true">
                                <div class="modal-dialog">
                                    <div class="modal-content">
                                        <div class="modal-header bg-danger text-white">
                                            <h5 class="modal-title">
                                                <i class="fas fa-sign-out-alt me-2"></i>
                                                Confirm Logout
                                            </h5>
                                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                        </div>
                                        <div class="modal-body">
                                            <p>Are you sure you want to logout and switch to a different account?</p>
                                            <p class="text-muted small">
                                                You'll need to login with an account that has 
                                                <strong>{{ strtoupper($required_role ?? 'appropriate') }}</strong> role permissions.
                                            </p>
                                        </div>
                                        <div class="modal-footer">
                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                            <form method="POST" action="{{ route('logout') }}" class="d-inline">
                                                @csrf
                                                <button type="submit" class="btn btn-danger">
                                                    <i class="fas fa-sign-out-alt me-1"></i>
                                                    Logout Now
                                                </button>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                            </div>

                        @else
                            <!-- Regular 403 Content -->
                            <p class="lead">You don't have permission to access this resource.</p>
                            <p>Please contact your administrator if you believe this is an error.</p>
                            
                            <div class="d-grid gap-2 d-md-flex justify-content-md-center">
                                <a href="{{ Auth::check() ? (Auth::user()->RoleID == 1 ? route('admin.dashboard') : route('user.dashboard')) : route('login') }}" 
                                   class="btn btn-primary">
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
                                
                                <button onclick="history.back()" class="btn btn-secondary">
                                    <i class="fas fa-arrow-left me-2"></i>
                                    Go Back
                                </button>
                            </div>

                            @if(Auth::check())
                            <div class="mt-4">
                                <div class="alert alert-info" role="alert">
                                    <h6><i class="fas fa-user me-1"></i> Your Current Access Level</h6>
                                    <strong>User:</strong> {{ Auth::user()->FullName }}<br>
                                    <strong>Role:</strong> {{ Auth::user()->RoleID == 1 ? 'Administrator' : 'User' }}<br>
                                    <strong>Logged in:</strong> {{ Auth::user()->created_at->diffForHumans() }}
                                </div>
                            </div>
                            @endif
                        @endif
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="{{ asset('vendor/bootstrap/js/bootstrap.bundle.min.js') }}"></script>
</body>
</html>
