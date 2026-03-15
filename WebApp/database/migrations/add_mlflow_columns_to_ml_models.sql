-- Migration: Add MLflow tracking columns to ml_models table
-- Created: 2025-11-12
-- Purpose: Store MLflow run_id and experiment_id for model versioning and tracking

-- Add MLflow columns
ALTER TABLE `ml_models` 
ADD COLUMN `mlflow_run_id` VARCHAR(255) NULL AFTER `FilePath`,
ADD COLUMN `mlflow_experiment_id` VARCHAR(255) NULL AFTER `mlflow_run_id`;

-- Add index for faster queries
ALTER TABLE `ml_models`
ADD INDEX `idx_mlflow_run` (`mlflow_run_id`);

-- Add comment to columns
ALTER TABLE `ml_models`
MODIFY COLUMN `mlflow_run_id` VARCHAR(255) NULL COMMENT 'MLflow run ID for model versioning',
MODIFY COLUMN `mlflow_experiment_id` VARCHAR(255) NULL COMMENT 'MLflow experiment ID';

-- Verify structure
DESCRIBE `ml_models`;
