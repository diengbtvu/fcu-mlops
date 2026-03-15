/* Admin Model Create Form JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    const libTypeSelect = document.getElementById('LibType');
    const fileInput = document.getElementById('model_file');
    
    // File extensions mapping
    const extensionMapping = {
        'keras': '.keras,.h5,.hdf5',
        'pytorch': '.pt,.pth',
        'sklearn': '.pkl,.joblib',
        'xgboost': '.json,.model,.xgb',
        'pickle': '.pkl,.pickle',
        'joblib': '.joblib'
    };
    
    if (libTypeSelect && fileInput) {
        libTypeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            if (selectedType && extensionMapping[selectedType]) {
                fileInput.setAttribute('accept', extensionMapping[selectedType]);
            } else {
                // Default to all supported extensions
                fileInput.setAttribute('accept', '.h5,.pkl,.keras,.json,.pt,.pth,.joblib,.xgb');
            }
        });
    }
    
    // Initialize admin panel for model creation
    if (typeof AdminPanel !== 'undefined') {
        window.adminPanel = new AdminPanel('model-create');
    }
});
