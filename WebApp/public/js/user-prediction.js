/* User Prediction Form JavaScript */

// Initialize user prediction form
window.initUserPredictionForm = function(config) {
    const defaultConfig = {
        submitUrl: '/user/predict/make',
        csrfToken: '',
        userType: 'user'
    };
    
    const finalConfig = { ...defaultConfig, ...config };
    
    window.predictionForm = new PredictionForm('predictionForm', finalConfig);
};
