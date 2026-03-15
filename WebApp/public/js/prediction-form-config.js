/**
 * Prediction Form Configuration Manager
 * Handles initialization of prediction forms with dynamic config
 */
class PredictionFormConfig {
    constructor() {
        this.configs = new Map();
    }

    /**
     * Register a prediction form configuration
     * @param {string} formId - Unique identifier for the form
     * @param {Object} config - Configuration object
     */
    register(formId, config) {
        this.configs.set(formId, config);
    }

    /**
     * Initialize prediction form based on registered config
     * @param {string} formId - Form identifier
     */
    initialize(formId) {
        const config = this.configs.get(formId);
        if (!config) {
            console.error(`No configuration found for form: ${formId}`);
            return;
        }

        switch (config.userType) {
            case 'user':
                if (typeof window.initUserPredictionForm === 'function') {
                    window.initUserPredictionForm(config);
                }
                break;
            case 'admin':
                if (typeof window.initAdminPredictionForm === 'function') {
                    window.initAdminPredictionForm(config);
                }
                break;
            default:
                console.error(`Unknown user type: ${config.userType}`);
        }
    }

    /**
     * Auto-initialize all registered forms
     */
    initializeAll() {
        this.configs.forEach((config, formId) => {
            this.initialize(formId);
        });
    }
}

// Global instance
window.PredictionFormConfig = new PredictionFormConfig();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure other scripts are loaded
    setTimeout(() => {
        window.PredictionFormConfig.initializeAll();
    }, 100);
});
