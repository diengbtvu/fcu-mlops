<?php

return [
    'title' => 'Models Management',
    'list' => 'Model List',
    'create' => 'Create Model',
    'edit' => 'Edit Model',
    'delete' => 'Delete Model',
    'details' => 'Model Details',
    'comparison' => 'Model Comparison',
    
    // Fields
    'name' => 'Model Name',
    'library_type' => 'Library Type',
    'mse' => 'MSE',
    'mae' => 'MAE',
    'r2' => 'R² Score',
    'rmse' => 'RMSE',
    'created_date' => 'Created Date',
    'algorithm' => 'Algorithm',
    'parameters' => 'Parameters',
    'training_time' => 'Training Time',
    'dataset_used' => 'Dataset Used',
    
    // Library Types
    'libraries' => [
        'ann' => 'Artificial Neural Network',
        'xgboost' => 'XGBoost',
        'random_forest' => 'Random Forest',
        'linear_regression' => 'Linear Regression',
    ],
    
    // Comparison
    'compare_models' => 'Compare Models',
    'select_models' => 'Select models to compare',
    'comparison_chart' => 'Comparison Chart',
    'winner' => 'Winner',
    'best_model' => 'Best Model',
    'metrics_comparison' => 'Metrics Comparison',
    'performance_summary' => 'Performance Summary',
    
    // Warnings
    'incomplete_metrics' => 'Some models have incomplete metrics data. Please retrain these models to get complete evaluation metrics.',
    'no_r2_value' => 'R² value not available',
    'no_rmse_value' => 'RMSE value not available',
    
    // Actions
    'train_model' => 'Train Model',
    'retrain' => 'Retrain',
    'evaluate' => 'Evaluate',
    'deploy' => 'Deploy',
    'download_model' => 'Download Model',
    'view_logs' => 'View Logs',
    
    // Messages
    'training_started' => 'Model training started successfully!',
    'training_completed' => 'Model training completed!',
    'training_failed' => 'Model training failed. Please check the logs.',
    'model_deleted' => 'Model deleted successfully!',
    'no_models' => 'No models found. Please train a model first.',
];
