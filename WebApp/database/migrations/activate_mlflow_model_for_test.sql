-- Quick setup: Activate a model with MLflow tracking for testing
-- Run this in MySQL/phpMyAdmin

-- Option 1: Update existing model with MLflow data
UPDATE ml_models 
SET 
    IsActive = true,
    mlflow_run_id = 'd2b915073d074ae2bfaf934b86e55566',
    mlflow_experiment_id = '460928566585211178'
WHERE id = 8;

-- Option 2: Or insert a new test model
INSERT INTO ml_models (
    MLMName,
    FilePath,
    LibType,
    IsActive,
    MSEValue,
    MAEValue,
    mlflow_run_id,
    mlflow_experiment_id,
    TrainedBy,
    CreatedDate,
    UpdatedDate
) VALUES (
    'Test_MLflow_Cache_Model',
    'models/Test_MLflow_Cache_Model.pkl',
    'sklearn',
    1,  -- IsActive = true
    276.58,
    11.06,
    'd2b915073d074ae2bfaf934b86e55566',
    '460928566585211178',
    1,  -- Admin user ID
    NOW(),
    NOW()
);

-- Verify
SELECT 
    id,
    MLMName,
    IsActive,
    mlflow_run_id,
    mlflow_experiment_id,
    LibType
FROM ml_models 
WHERE IsActive = 1
ORDER BY id DESC
LIMIT 5;
