/**
 * Form Validation and Input Filtering
 * Handles client-side validation and input sanitization
 */

class FormValidator {
    constructor() {
        this.init();
    }

    init() {
        this.setupInputFiltering();
        this.setupFormValidation();
        this.setupSubmitHandler();
    }

    /**
     * Setup input filtering for security
     */
    setupInputFiltering() {
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');

        if (usernameInput) {
            usernameInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z0-9@_.-]/g, '');
            });
        }

        if (passwordInput) {
            passwordInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z0-9!@#$%^&*()_+=.,:;'"?\-]/g, '');
            });
        }
    }

    /**
     * Setup real-time form validation
     */
    setupFormValidation() {
        const form = document.getElementById('loginForm');
        if (!form) return;

        const inputs = form.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }

    /**
     * Setup form submit handler
     */
    setupSubmitHandler() {
        const form = document.getElementById('loginForm');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                return false;
            }
            this.showLoading();
        });
    }

    /**
     * Validate individual field
     */
    validateField(field) {
        const value = field.value.trim();
        const fieldName = field.getAttribute('name');
        let isValid = true;
        let message = '';

        // Required field validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} is required`;
        }

        // Specific field validations
        if (value && fieldName === 'username') {
            if (value.length < 3) {
                isValid = false;
                message = 'Username must be at least 3 characters';
            }
        }

        if (value && fieldName === 'password') {
            if (value.length < 6) {
                isValid = false;
                message = 'Password must be at least 6 characters';
            }
        }

        this.setFieldValidation(field, isValid, message);
        return isValid;
    }

    /**
     * Validate entire form
     */
    validateForm() {
        const form = document.getElementById('loginForm');
        if (!form) return true;

        const inputs = form.querySelectorAll('input[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    /**
     * Set field validation state
     */
    setFieldValidation(field, isValid, message) {
        const fieldGroup = field.closest('.form-group');
        const feedback = fieldGroup?.querySelector('.invalid-feedback');

        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            if (feedback) feedback.textContent = '';
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            if (feedback) {
                feedback.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
            }
        }
    }

    /**
     * Clear field error state
     */
    clearFieldError(field) {
        field.classList.remove('is-invalid', 'is-valid');
        const fieldGroup = field.closest('.form-group');
        const feedback = fieldGroup?.querySelector('.invalid-feedback');
        if (feedback) feedback.textContent = '';
    }

    /**
     * Show loading state
     */
    showLoading() {
        const overlay = document.getElementById('loadingOverlay');
        const submitButton = document.querySelector('.btn-login');
        
        if (overlay) {
            overlay.style.display = 'flex';
        }
        
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Signing In...';
        }
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        const submitButton = document.querySelector('.btn-login');
        
        if (overlay) {
            overlay.style.display = 'none';
        }
        
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="bi bi-box-arrow-in-right me-2"></i>Sign In';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FormValidator();
});
