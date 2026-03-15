{{-- Component: Logout Confirmation Modal --}}
@props(['modalId' => 'logoutModal'])

<div class="modal fade" id="{{ $modalId }}" tabindex="-1" aria-labelledby="{{ $modalId }}Label" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header bg-danger text-white">
                <h5 class="modal-title" id="{{ $modalId }}Label">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Confirm Logout
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" data-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <div class="text-center">
                    <i class="bi bi-box-arrow-right text-danger icon-48"></i>
                    <h5 class="mt-3 mb-3">Are you sure you want to logout?</h5>
                    <p class="text-muted">You will be redirected to the login page and need to sign in again to access your account.</p>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" data-dismiss="modal">
                    <i class="bi bi-x-circle me-1"></i>
                    Cancel
                </button>
                <form method="POST" action="{{ route('logout') }}" class="d-inline">
                    @csrf
                    <button type="submit" class="btn btn-danger">
                        <i class="bi bi-box-arrow-right me-1"></i>
                        Yes, Logout
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
