/* Admin Prediction Form JavaScript */

// Initialize admin prediction form
window.initAdminPredictionForm = function(config) {
    const defaultConfig = {
        submitUrl: '/admin/predict/make',
        csrfToken: '',
        userType: 'admin'
    };
    
    const finalConfig = { ...defaultConfig, ...config };
    
    window.predictionForm = new PredictionForm('predictionForm', finalConfig);
};
