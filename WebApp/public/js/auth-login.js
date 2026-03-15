/* Login Page JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Input filtering for username
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^a-zA-Z0-9@_.-]/g, '');
        });
    }

    // Input filtering for password
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^a-zA-Z0-9!@#$%^&*()_+=.,:;'"?\-]/g, '');
        });
    }

    // Show loading overlay on form submit
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function() {
            const loadingOverlay = document.getElementById('loadingOverlay');
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
            }
        });
    }

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 5000);
    });
});
