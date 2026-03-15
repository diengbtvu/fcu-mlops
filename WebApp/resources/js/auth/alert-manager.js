/**
 * Alert Manager
 * Handles alert display, auto-hide, and animations
 */

class AlertManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupAutoHide();
        this.setupDismissHandlers();
    }

    /**
     * Setup auto-hide for alerts
     */
    setupAutoHide() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        
        alerts.forEach(alert => {
            // Don't auto-hide if it has dismiss button
            if (alert.querySelector('.btn-close')) return;
            
            setTimeout(() => {
                this.hideAlert(alert);
            }, 5000);
        });
    }

    /**
     * Setup dismiss button handlers
     */
    setupDismissHandlers() {
        const dismissButtons = document.querySelectorAll('.alert .btn-close');
        
        dismissButtons.forEach(button => {
            button.addEventListener('click', () => {
                const alert = button.closest('.alert');
                this.hideAlert(alert);
            });
        });
    }

    /**
     * Hide alert with animation
     */
    hideAlert(alert) {
        if (!alert) return;

        alert.classList.add('fade-out');
        
        setTimeout(() => {
            alert.remove();
        }, 500);
    }

    /**
     * Show alert with animation
     */
    showAlert(message, type = 'info', options = {}) {
        const alertHtml = this.createAlertHtml(message, type, options);
        const alertContainer = this.getOrCreateAlertContainer();
        
        alertContainer.insertAdjacentHTML('beforeend', alertHtml);
        
        const newAlert = alertContainer.lastElementChild;
        
        // Setup auto-hide if specified
        if (options.autoHide !== false) {
            setTimeout(() => {
                this.hideAlert(newAlert);
            }, options.duration || 5000);
        }

        // Setup dismiss handler if dismissible
        if (options.dismissible) {
            const dismissButton = newAlert.querySelector('.btn-close');
            if (dismissButton) {
                dismissButton.addEventListener('click', () => {
                    this.hideAlert(newAlert);
                });
            }
        }

        return newAlert;
    }

    /**
     * Create alert HTML
     */
    createAlertHtml(message, type, options) {
        const iconMap = {
            success: 'bi-check-circle-fill',
            danger: 'bi-exclamation-triangle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill'
        };

        const icon = iconMap[type] || iconMap.info;
        const dismissButton = options.dismissible ? 
            '<button type="button" class="btn-close" aria-label="Close"></button>' : '';

        return `
            <div class="alert alert-${type} ${options.dismissible ? 'alert-dismissible' : ''}" role="alert">
                <i class="bi ${icon} flex-shrink-0 me-2"></i>
                <div>${message}</div>
                ${dismissButton}
            </div>
        `;
    }

    /**
     * Get or create alert container
     */
    getOrCreateAlertContainer() {
        let container = document.querySelector('.alert-container');
        
        if (!container) {
            container = document.createElement('div');
            container.className = 'alert-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
        
        return container;
    }

    /**
     * Clear all alerts
     */
    clearAll() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => this.hideAlert(alert));
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.alertManager = new AlertManager();
});
