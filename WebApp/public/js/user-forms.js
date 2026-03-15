/**
 * User Forms JavaScript
 * Handles form validation, password confirmation, and user interactions
 */

class UserForms {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupPasswordValidation();
        this.setupFormValidation();
        this.setupProfileForms();
    }
    
    setupPasswordValidation() {
        const passwordField = document.getElementById('new_password');
        const confirmField = document.getElementById('new_password_confirmation');
        
        if (passwordField && confirmField) {
            confirmField.addEventListener('input', () => {
                this.validatePasswordConfirmation(passwordField, confirmField);
            });
            
            passwordField.addEventListener('input', () => {
                if (confirmField.value) {
                    this.validatePasswordConfirmation(passwordField, confirmField);
                }
                this.validatePasswordStrength(passwordField);
            });
        }
        
        // Setup current password validation for change password forms
        const currentPasswordField = document.getElementById('current_password');
        if (currentPasswordField) {
            currentPasswordField.addEventListener('blur', () => {
                this.validateCurrentPassword(currentPasswordField);
            });
        }
    }
    
    validatePasswordConfirmation(passwordField, confirmField) {
        const password = passwordField.value;
        const confirmation = confirmField.value;
        
        if (password !== confirmation) {
            confirmField.setCustomValidity('Passwords do not match');
            confirmField.classList.add('is-invalid');
            this.showFieldError(confirmField, 'Passwords do not match');
        } else {
            confirmField.setCustomValidity('');
            confirmField.classList.remove('is-invalid');
            this.hideFieldError(confirmField);
        }
    }
    
    validatePasswordStrength(passwordField) {
        const password = passwordField.value;
        const strengthIndicator = document.getElementById('password-strength');
        
        if (!strengthIndicator) return;
        
        const strength = this.calculatePasswordStrength(password);
        this.updatePasswordStrengthIndicator(strengthIndicator, strength);
    }
    
    calculatePasswordStrength(password) {
        let score = 0;
        const checks = [
            { regex: /.{8,}/, message: 'At least 8 characters' },
            { regex: /[a-z]/, message: 'Lowercase letter' },
            { regex: /[A-Z]/, message: 'Uppercase letter' },
            { regex: /[0-9]/, message: 'Number' },
            { regex: /[^A-Za-z0-9]/, message: 'Special character' }
        ];
        
        checks.forEach(check => {
            if (check.regex.test(password)) {
                score++;
            }
        });
        
        return {
            score,
            total: checks.length,
            checks,
            strength: this.getStrengthLevel(score)
        };
    }
    
    getStrengthLevel(score) {
        if (score < 2) return { level: 'weak', color: 'danger', text: 'Weak' };
        if (score < 4) return { level: 'medium', color: 'warning', text: 'Medium' };
        return { level: 'strong', color: 'success', text: 'Strong' };
    }
    
    updatePasswordStrengthIndicator(indicator, strength) {
        const { score, total, checks, strength: strengthLevel } = strength;
        
        indicator.innerHTML = `
            <div class="password-strength-bar mb-2">
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar bg-${strengthLevel.color}" 
                         style="width: ${(score / total) * 100}%"></div>
                </div>
            </div>
            <div class="password-strength-text">
                <small class="text-${strengthLevel.color}">
                    Password strength: ${strengthLevel.text}
                </small>
            </div>
            <div class="password-requirements mt-2">
                ${checks.map(check => `
                    <small class="d-block ${check.regex.test(document.getElementById('new_password').value) ? 'text-success' : 'text-muted'}">
                        <i class="bi bi-${check.regex.test(document.getElementById('new_password').value) ? 'check' : 'x'}-circle me-1"></i>
                        ${check.message}
                    </small>
                `).join('')}
            </div>
        `;
    }
    
    async validateCurrentPassword(field) {
        const password = field.value;
        if (!password) return;
        
        try {
            const response = await fetch('/user/validate-current-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({ current_password: password })
            });
            
            const result = await response.json();
            
            if (result.valid) {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');
                this.hideFieldError(field);
            } else {
                field.classList.remove('is-valid');
                field.classList.add('is-invalid');
                this.showFieldError(field, 'Current password is incorrect');
            }
        } catch (error) {
            console.warn('Could not validate current password:', error);
        }
    }
    
    setupFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.focusFirstInvalidField(form);
                }
                form.classList.add('was-validated');
            });
            
            // Real-time validation for form fields
            const fields = form.querySelectorAll('input, select, textarea');
            fields.forEach(field => {
                field.addEventListener('blur', () => {
                    this.validateField(field);
                });
                
                field.addEventListener('input', () => {
                    if (field.classList.contains('is-invalid')) {
                        this.validateField(field);
                    }
                });
            });
        });
    }
    
    setupProfileForms() {
        // Handle profile image upload
        const imageInput = document.getElementById('profile_image');
        const imagePreview = document.getElementById('image-preview');
        
        if (imageInput && imagePreview) {
            imageInput.addEventListener('change', (e) => {
                this.handleImageUpload(e, imagePreview);
            });
        }
        
        // Handle form auto-save (optional)
        const autoSaveForms = document.querySelectorAll('[data-auto-save]');
        autoSaveForms.forEach(form => {
            this.setupAutoSave(form);
        });
    }
    
    handleImageUpload(event, previewElement) {
        const file = event.target.files[0];
        if (!file) return;
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showError('Please select a valid image file');
            event.target.value = '';
            return;
        }
        
        // Validate file size (e.g., 2MB limit)
        if (file.size > 2 * 1024 * 1024) {
            this.showError('Image size must be less than 2MB');
            event.target.value = '';
            return;
        }
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewElement.src = e.target.result;
            previewElement.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
    
    setupAutoSave(form) {
        let timeout;
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.autoSaveForm(form);
                }, 2000); // Save after 2 seconds of inactivity
            });
        });
    }
    
    async autoSaveForm(form) {
        const formData = new FormData(form);
        const indicator = document.getElementById('autosave-indicator');
        
        try {
            if (indicator) {
                indicator.textContent = 'Saving...';
                indicator.className = 'text-warning';
            }
            
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                if (indicator) {
                    indicator.textContent = 'Saved';
                    indicator.className = 'text-success';
                    setTimeout(() => {
                        indicator.textContent = '';
                    }, 2000);
                }
            }
        } catch (error) {
            if (indicator) {
                indicator.textContent = 'Save failed';
                indicator.className = 'text-danger';
            }
        }
    }
    
    validateField(field) {
        if (field.checkValidity()) {
            field.classList.remove('is-invalid');
            this.hideFieldError(field);
        } else {
            field.classList.add('is-invalid');
            this.showFieldError(field, field.validationMessage);
        }
    }
    
    showFieldError(field, message) {
        let errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            field.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = message;
    }
    
    hideFieldError(field) {
        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.textContent = '';
        }
    }
    
    focusFirstInvalidField(form) {
        const firstInvalid = form.querySelector('.is-invalid, :invalid');
        if (firstInvalid) {
            firstInvalid.focus();
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    showError(message) {
        // Simple error display - can be enhanced with toast notifications
        alert(message);
    }
    
    showSuccess(message) {
        // Simple success display - can be enhanced with toast notifications
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container-fluid') || document.body;
        container.insertBefore(alert, container.firstChild);
        
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    window.userForms = new UserForms();
});
