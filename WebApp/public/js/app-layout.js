/**
 * App Layout JavaScript
 * Contains global functionality for the application layout
 */

$(document).ready(function() {
    // Initialize Bootstrap tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Ensure dropdown menus work properly
    $('.dropdown-toggle').dropdown();
    
    // Fix logout modal for sidebar
    $('.logout-link').on('click', function(e) {
        e.preventDefault();
        
        // Force close any existing modals first
        $('.modal').modal('hide');
        $('body').removeClass('modal-open');
        $('.modal-backdrop').remove();
        
        // Small delay then show the logout modal
        setTimeout(function() {
            // Try Bootstrap 5 first, then Bootstrap 4
            if (typeof bootstrap !== 'undefined') {
                // Bootstrap 5
                const modal = new bootstrap.Modal(document.getElementById('logoutModal'));
                modal.show();
            } else if (typeof $.fn.modal !== 'undefined') {
                // Bootstrap 4 (jQuery)
                $('#logoutModal').modal('show');
            } else {
                // Fallback - direct confirmation
                if (confirm('Are you sure you want to logout?')) {
                    // Find logout form and submit it
                    const logoutForm = document.querySelector('form[action*="logout"]');
                    if (logoutForm) {
                        logoutForm.submit();
                    }
                }
            }
        }, 150);
    });
    
    // Handle modal cleanup when closed
    $('#logoutModal').on('hidden.bs.modal hidden', function (e) {
        $('body').removeClass('modal-open');
        $('.modal-backdrop').remove();
        $('body').css('padding-right', '');
    });
    
    // Additional cleanup for backdrop clicks
    $(document).on('click', '.modal-backdrop', function() {
        $('.modal').modal('hide');
        $('body').removeClass('modal-open');
        $('.modal-backdrop').remove();
        $('body').css('padding-right', '');
    });
    
    // Force cleanup on escape key
    $(document).on('keyup', function(e) {
        if (e.key === 'Escape') {
            $('.modal').modal('hide');
            $('body').removeClass('modal-open');
            $('.modal-backdrop').remove();
            $('body').css('padding-right', '');
        }
    });
    
    // Global AJAX error handler for role mismatch
    $(document).ajaxError(function(event, xhr, settings, thrownError) {
        if (xhr.status === 403 && xhr.responseJSON && xhr.responseJSON.role_mismatch) {
            const response = xhr.responseJSON;
            showRoleMismatchModal(response.current_role, response.required_role);
        }
    });
});

/**
 * Show role mismatch modal for AJAX requests
 * @param {string} currentRole - User's current role
 * @param {string} requiredRole - Required role for the action
 */
function showRoleMismatchModal(currentRole, requiredRole) {
    const modalHtml = `
        <div class="modal fade" id="roleMismatchModal" tabindex="-1" aria-labelledby="roleMismatchModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title" id="roleMismatchModalLabel">
                            <i class="bi bi-shield-exclamation me-2"></i>
                            Access Denied - Role Mismatch
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center">
                            <i class="bi bi-exclamation-triangle text-warning" style="font-size: 3rem;"></i>
                            <h5 class="mt-3 mb-3">Permission Required</h5>
                            <p class="text-muted">
                                You are logged in as <strong>${currentRole.toUpperCase()}</strong> but this action requires 
                                <strong>${requiredRole.toUpperCase()}</strong> privileges.
                            </p>
                            <p class="text-muted">
                                Would you like to logout and login with the correct role?
                            </p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="bi bi-x-circle me-1"></i>
                            Cancel
                        </button>
                        <button type="button" class="btn btn-danger" onclick="logoutAndSwitch()">
                            <i class="bi bi-box-arrow-right me-1"></i>
                            Logout & Switch
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    $('#roleMismatchModal').remove();
    
    // Add new modal to body and show
    $('body').append(modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('roleMismatchModal'));
    modal.show();
}

/**
 * Logout and redirect to login page
 */
function logoutAndSwitch() {
    // Create and submit logout form
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.logoutRoute || '/logout';
    
    const csrfToken = document.createElement('input');
    csrfToken.type = 'hidden';
    csrfToken.name = '_token';
    csrfToken.value = window.csrfToken || document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    form.appendChild(csrfToken);
    document.body.appendChild(form);
    form.submit();
}
