@extends('layouts.app')

@section('title', __('email.title'))

@section('sidebar')
<x-navigation.admin-sidebar />
@endsection

@section('content')
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📧 {{ __('email.title') }}</h3>
                    <p class="text-muted mb-0">{{ __('email.description') }}</p>
                </div>
                <div class="card-body">
                    @if(session('success'))
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            <i class="bi bi-check-circle"></i> {{ session('success') }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    @endif

                    @if(session('error'))
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <i class="bi bi-exclamation-triangle"></i> {{ session('error') }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        </div>
                    @endif

                    <form action="{{ route('admin.settings.update-email') }}" method="POST">
                        @csrf
                        @method('PUT')

                        <!-- Notification Settings -->
                        <div class="mb-4">
                            <h5 class="border-bottom pb-2">
                                <i class="bi bi-bell"></i> {{ __('email.notification_settings') }}
                            </h5>
                            <p class="text-muted">{{ __('email.notification_email_help') }}</p>
                            
                            <div class="mb-3">
                                <label for="notification_email" class="form-label">
                                    {{ __('email.notification_email') }} <span class="text-danger">*</span>
                                </label>
                                <input type="email" 
                                       class="form-control @error('notification_email') is-invalid @enderror" 
                                       id="notification_email" 
                                       name="notification_email" 
                                       value="{{ old('notification_email', $notificationSettings->where('key', 'notification_email')->first()->value ?? '') }}"
                                       placeholder="admin@example.com"
                                       required>
                                @error('notification_email')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                                <div class="form-text">
                                    <i class="bi bi-info-circle"></i> This email will receive notifications when model training completes
                                </div>
                            </div>
                        </div>

                        <hr class="my-4">

                        <!-- SMTP Settings -->
                        <div class="mb-4">
                            <h5 class="border-bottom pb-2">
                                <i class="bi bi-envelope-at"></i> {{ __('email.smtp_configuration') }}
                            </h5>
                            <p class="text-muted">{{ __('email.smtp_configuration_help') }}</p>

                            <div class="row">
                                <div class="col-md-8 mb-3">
                                    <label for="smtp_host" class="form-label">
                                        {{ __('email.smtp_host') }} <span class="text-danger">*</span>
                                    </label>
                                    <input type="text" 
                                           class="form-control @error('smtp_host') is-invalid @enderror" 
                                           id="smtp_host" 
                                           name="smtp_host" 
                                           value="{{ old('smtp_host', $smtpSettings->where('key', 'smtp_host')->first()->value ?? '') }}"
                                           placeholder="smtp.gmail.com"
                                           required>
                                    @error('smtp_host')
                                        <div class="invalid-feedback">{{ $message }}</div>
                                    @enderror
                                    <div class="form-text">Example: smtp.gmail.com, smtp.office365.com</div>
                                </div>

                                <div class="col-md-4 mb-3">
                                    <label for="smtp_port" class="form-label">
                                        {{ __('email.smtp_port') }} <span class="text-danger">*</span>
                                    </label>
                                    <input type="number" 
                                           class="form-control @error('smtp_port') is-invalid @enderror" 
                                           id="smtp_port" 
                                           name="smtp_port" 
                                           value="{{ old('smtp_port', $smtpSettings->where('key', 'smtp_port')->first()->value ?? '587') }}"
                                           placeholder="587"
                                           required>
                                    @error('smtp_port')
                                        <div class="invalid-feedback">{{ $message }}</div>
                                    @enderror
                                    <div class="form-text">587 (TLS) or 465 (SSL)</div>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label for="smtp_username" class="form-label">
                                    {{ __('email.smtp_username') }} <span class="text-danger">*</span>
                                </label>
                                <input type="email" 
                                       class="form-control @error('smtp_username') is-invalid @enderror" 
                                       id="smtp_username" 
                                       name="smtp_username" 
                                       value="{{ old('smtp_username', $smtpSettings->where('key', 'smtp_username')->first()->value ?? '') }}"
                                       placeholder="your-email@gmail.com"
                                       required>
                                @error('smtp_username')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                                <div class="form-text">Usually your email address</div>
                            </div>

                            <div class="mb-3">
                                <label for="smtp_password" class="form-label">
                                    {{ __('email.smtp_password') }}
                                </label>
                                <div class="input-group">
                                    <input type="password" 
                                           class="form-control @error('smtp_password') is-invalid @enderror" 
                                           id="smtp_password" 
                                           name="smtp_password" 
                                           placeholder="Leave blank to keep current password">
                                    <button class="btn btn-outline-secondary" type="button" id="togglePassword">
                                        <i class="bi bi-eye"></i>
                                    </button>
                                </div>
                                @error('smtp_password')
                                    <div class="invalid-feedback d-block">{{ $message }}</div>
                                @enderror
                                <div class="form-text">
                                    <i class="bi bi-shield-lock"></i> For Gmail, use App Password. 
                                    <a href="https://myaccount.google.com/apppasswords" target="_blank">Create here</a>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label for="smtp_encryption" class="form-label">
                                    {{ __('email.smtp_encryption') }} <span class="text-danger">*</span>
                                </label>
                                <select class="form-select @error('smtp_encryption') is-invalid @enderror" 
                                        id="smtp_encryption" 
                                        name="smtp_encryption" 
                                        required>
                                    <option value="tls" {{ old('smtp_encryption', $smtpSettings->where('key', 'smtp_encryption')->first()->value ?? 'tls') == 'tls' ? 'selected' : '' }}>
                                        {{ __('email.encryption.tls') }}
                                    </option>
                                    <option value="ssl" {{ old('smtp_encryption', $smtpSettings->where('key', 'smtp_encryption')->first()->value ?? '') == 'ssl' ? 'selected' : '' }}>
                                        {{ __('email.encryption.ssl') }}
                                    </option>
                                </select>
                                @error('smtp_encryption')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                            </div>
                        </div>

                        <hr class="my-4">

                        <!-- Sender Information -->
                        <div class="mb-4">
                            <h5 class="border-bottom pb-2">
                                <i class="bi bi-person-badge"></i> {{ __('email.sender_information') }}
                            </h5>
                            <p class="text-muted">{{ __('email.sender_information_help') }}</p>

                            <div class="mb-3">
                                <label for="mail_from_address" class="form-label">
                                    {{ __('email.mail_from_address') }} <span class="text-danger">*</span>
                                </label>
                                <input type="email" 
                                       class="form-control @error('mail_from_address') is-invalid @enderror" 
                                       id="mail_from_address" 
                                       name="mail_from_address" 
                                       value="{{ old('mail_from_address', $smtpSettings->where('key', 'mail_from_address')->first()->value ?? '') }}"
                                       placeholder="noreply@example.com"
                                       required>
                                @error('mail_from_address')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                                <div class="form-text">Email address shown as sender</div>
                            </div>

                            <div class="mb-3">
                                <label for="mail_from_name" class="form-label">
                                    {{ __('email.mail_from_name') }} <span class="text-danger">*</span>
                                </label>
                                <input type="text" 
                                       class="form-control @error('mail_from_name') is-invalid @enderror" 
                                       id="mail_from_name" 
                                       name="mail_from_name" 
                                       value="{{ old('mail_from_name', $smtpSettings->where('key', 'mail_from_name')->first()->value ?? '') }}"
                                       placeholder="Hydrogen Production Rate Prediction System"
                                       required>
                                @error('mail_from_name')
                                    <div class="invalid-feedback">{{ $message }}</div>
                                @enderror
                                <div class="form-text">Name shown as sender</div>
                            </div>
                        </div>

                        <div class="d-flex gap-2">
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-save"></i> {{ __('email.save_settings') }}
                            </button>
                            <a href="{{ route('admin.settings.test-email') }}" class="btn btn-outline-secondary">
                                <i class="bi bi-send"></i> {{ __('email.test_email') }}
                            </a>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Help Card -->
            <div class="card mt-3">
                <div class="card-header bg-info text-white">
                    <h5 class="mb-0"><i class="bi bi-info-circle"></i> Gmail Setup Instructions</h5>
                </div>
                <div class="card-body">
                    <h6>For Gmail users:</h6>
                    <ol>
                        <li>Enable 2-Step Verification on your Google Account</li>
                        <li>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank">Google App Passwords</a></li>
                        <li>Generate a new App Password for "Mail"</li>
                        <li>Use the 16-character password in the SMTP Password field above</li>
                        <li>Settings: Host: <code>smtp.gmail.com</code>, Port: <code>587</code>, Encryption: <code>TLS</code></li>
                    </ol>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<script>
document.getElementById('togglePassword').addEventListener('click', function() {
    const passwordInput = document.getElementById('smtp_password');
    const icon = this.querySelector('i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
});
</script>
@endsection
