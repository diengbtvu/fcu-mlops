<?php

namespace App\Services;

use App\Models\Dataset;
use App\Models\MLModel;
use App\Models\User;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Http;
use Symfony\Component\Process\Process;
use Symfony\Component\Process\Exception\ProcessFailedException;

class TrainingService
{
    /**
     * Đường dẫn tới predict-service directory
     */
    private string $predictServicePath;

    /**
     * Đường dẫn tới Python executable
     */
    private string $pythonPath;

    /**
     * Đường dẫn tới training script
     */
    private string $scriptPath;

    public function __construct()
    {
        $this->predictServicePath = realpath(base_path('../predict-service'));
        $this->pythonPath = $this->predictServicePath . '\venv\Scripts\python.exe';
        $this->scriptPath = $this->predictServicePath . '\run_pipeline.py';
    }

    /**
     * Validate training environment
     * 
     * @return array ['valid' => bool, 'errors' => array]
     */
    public function validateEnvironment(): array
    {
        $errors = [];

        if (!$this->predictServicePath || !is_dir($this->predictServicePath)) {
            $errors[] = 'Predict service directory not found';
        }

        if (!file_exists($this->pythonPath)) {
            $errors[] = 'Python environment not found at: ' . $this->pythonPath;
        }

        if (!file_exists($this->scriptPath)) {
            $errors[] = 'Training script not found at: ' . $this->scriptPath;
        }

        return [
            'valid' => empty($errors),
            'errors' => $errors
        ];
    }

    /**
     * Train model với dataset
     * 
     * @param Dataset $dataset
     * @param User $user
     * @param array $options Training options (hyperparameters, etc.)
     * @return array
     */
    public function trainModel(Dataset $dataset, User $user, array $options = []): array
    {
        try {
            // 1. Validate environment
            $validation = $this->validateEnvironment();
            if (!$validation['valid']) {
                return [
                    'success' => false,
                    'error' => 'Environment validation failed',
                    'details' => $validation['errors']
                ];
            }

            // 2. Validate dataset file
            $datasetPath = storage_path('app/public/' . $dataset->FilePath);
            if (!file_exists($datasetPath)) {
                return [
                    'success' => false,
                    'error' => 'Dataset file not found: ' . $datasetPath
                ];
            }

            // 3. Log training start
            Log::info('Training started', [
                'dataset_id' => $dataset->DatasetId,
                'dataset_name' => $dataset->DatasetName,
                'user_id' => $user->UserId,
                'user_name' => $user->FullName
            ]);

            // 4. Execute training process
            $result = $this->executeTrainingProcess($datasetPath, $options);

            // 5. Handle training result
            if ($result['success']) {
                // Save model info to database (optional)
                $this->saveModelMetadata($dataset, $user, $result);

                Log::info('Training completed successfully', [
                    'dataset_id' => $dataset->DatasetId,
                    'output' => $result['output']
                ]);
            } else {
                Log::error('Training failed', [
                    'dataset_id' => $dataset->DatasetId,
                    'error' => $result['error']
                ]);
            }

            return $result;

        } catch (\Exception $e) {
            Log::error('Training exception', [
                'dataset_id' => $dataset->DatasetId,
                'exception' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);

            return [
                'success' => false,
                'error' => 'Training failed with exception: ' . $e->getMessage()
            ];
        }
    }

    /**
     * Execute Python training process
     * 
     * @param string $datasetPath
     * @param array $options
     * @return array
     */
    private function executeTrainingProcess(string $datasetPath, array $options = []): array
    {
        try {
            // Build command
            $command = [
                $this->pythonPath,
                $this->scriptPath,
                '--data', $datasetPath
            ];

            // Add optional parameters
            if (isset($options['n_estimators'])) {
                $command[] = '--n_estimators';
                $command[] = $options['n_estimators'];
            }

            if (isset($options['max_depth'])) {
                $command[] = '--max_depth';
                $command[] = $options['max_depth'];
            }

            // Create process
            $process = new Process($command, $this->predictServicePath);
            $process->setTimeout(600); // 10 minutes timeout

            // Run process
            $process->run();

            // Check if successful
            if (!$process->isSuccessful()) {
                return [
                    'success' => false,
                    'error' => $process->getErrorOutput(),
                    'exit_code' => $process->getExitCode()
                ];
            }

            return [
                'success' => true,
                'output' => $process->getOutput(),
                'exit_code' => $process->getExitCode()
            ];

        } catch (ProcessFailedException $exception) {
            return [
                'success' => false,
                'error' => $exception->getMessage()
            ];
        }
    }

    /**
     * Save trained model metadata to database
     * 
     * @param Dataset $dataset
     * @param User $user
     * @param array $trainingResult
     * @return MLModel|null
     */
    private function saveModelMetadata(Dataset $dataset, User $user, array $trainingResult): ?MLModel
    {
        try {
            // Extract metrics from training output (if available)
            $output = $trainingResult['output'] ?? '';
            
            // Parse metrics from output (adjust based on your script output format)
            $metrics = $this->parseTrainingMetrics($output);

            // Generate model name
            $modelName = 'RF_Model_' . $dataset->DatasetName . '_' . date('YmdHis');
            
            // Model file path (adjust based on your actual model save location)
            $modelPath = 'ml_model/latest_model.pkl';

            // Create model record
            $model = MLModel::create([
                'ModelName' => $modelName,
                'ModelPath' => $modelPath,
                'Version' => '1.0',
                'Description' => 'Trained with dataset: ' . $dataset->DatasetName,
                'Accuracy' => $metrics['accuracy'] ?? null,
                'TrainedBy' => $user->UserId,
                'TrainDate' => now(),
            ]);

            return $model;

        } catch (\Exception $e) {
            Log::error('Failed to save model metadata', [
                'error' => $e->getMessage()
            ]);
            return null;
        }
    }

    /**
     * Parse training metrics from output
     * 
     * @param string $output
     * @return array
     */
    private function parseTrainingMetrics(string $output): array
    {
        $metrics = [
            'accuracy' => null,
            'r2_score' => null,
            'rmse' => null,
            'mae' => null
        ];

        // Parse R² Score
        if (preg_match('/R²\s*Score[:\s]+([\d.]+)/i', $output, $matches)) {
            $metrics['r2_score'] = floatval($matches[1]);
            $metrics['accuracy'] = floatval($matches[1]) * 100; // Convert to percentage
        }

        // Parse RMSE
        if (preg_match('/RMSE[:\s]+([\d.]+)/i', $output, $matches)) {
            $metrics['rmse'] = floatval($matches[1]);
        }

        // Parse MAE
        if (preg_match('/MAE[:\s]+([\d.]+)/i', $output, $matches)) {
            $metrics['mae'] = floatval($matches[1]);
        }

        return $metrics;
    }

    /**
     * Get training history for a user
     * 
     * @param User $user
     * @param int $perPage
     * @return \Illuminate\Pagination\LengthAwarePaginator
     */
    public function getUserTrainingHistory(User $user, int $perPage = 10)
    {
        return MLModel::with(['trainer', 'dataset'])
            ->where('TrainedBy', $user->UserId)
            ->orderBy('TrainDate', 'desc')
            ->paginate($perPage);
    }

    /**
     * Get training statistics
     * 
     * @param User|null $user
     * @return array
     */
    public function getTrainingStats(?User $user = null): array
    {
        $query = MLModel::query();

        if ($user) {
            $query->where('TrainedBy', $user->UserId);
        }

        return [
            'total_models' => $query->count(),
            'recent_trainings' => $query->where('TrainDate', '>=', now()->subDays(30))->count(),
            'avg_accuracy' => round($query->avg('Accuracy') ?? 0, 2),
            'best_accuracy' => round($query->max('Accuracy') ?? 0, 2),
            'last_training' => $query->latest('TrainDate')->first()?->TrainDate,
        ];
    }

    /**
     * Check if training is currently running (placeholder for future implementation)
     * 
     * @return bool
     */
    public function isTrainingRunning(): bool
    {
        // TODO: Implement with Queue/Job status check
        // For now, return false
        return false;
    }

    /**
     * Cancel running training (placeholder for future implementation)
     * 
     * @param int $trainingJobId
     * @return bool
     */
    public function cancelTraining(int $trainingJobId): bool
    {
        // TODO: Implement with Queue/Job cancellation
        return false;
    }

    /**
     * Train model using Flask API (Alternative to executeTrainingProcess)
     * 
     * @param Dataset $dataset
     * @param User $user
     * @param array $options
     * @return array
     */
    public function trainModelViaAPI(Dataset $dataset, User $user, array $options = []): array
    {
        try {
            // Validate dataset file
            $datasetPath = storage_path('app/public/' . $dataset->FilePath);
            if (!file_exists($datasetPath)) {
                return [
                    'success' => false,
                    'error' => 'Dataset file not found'
                ];
            }

            // Prepare request data
            $requestData = [
                'dataset_path' => $datasetPath,
                'model_type' => $options['model_type'] ?? 'random_forest',
                'training_scope' => $options['training_scope'] ?? 'all_models_compare',
                'model_name' => $options['model_name'] ?? 'Model_' . $dataset->DatasetName . '_' . date('YmdHis'),
                'test_size' => $options['test_size'] ?? 0.2,
                'random_state' => $options['random_state'] ?? 42,
                'trained_by' => $user->UserId,
                'dataset_id' => $dataset->DatasetId,
                'session_id' => $options['session_id'] ?? null  // Pass session ID for progress tracking
            ];

            // Add model-specific parameters
            $modelType = $options['model_type'] ?? 'random_forest';
            
            if ($modelType === 'random_forest' || $modelType === 'xgboost') {
                $requestData['n_estimators'] = $options['n_estimators'] ?? 100;
                $requestData['max_depth'] = $options['max_depth'] ?? null;
                
                if ($modelType === 'xgboost') {
                    $requestData['learning_rate'] = $options['learning_rate'] ?? 0.1;
                }
            } elseif ($modelType === 'decision_tree' || $modelType === 'dt') {
                $requestData['max_depth'] = $options['max_depth'] ?? null;
            } elseif ($modelType === 'svm') {
                $requestData['C'] = $options['C'] ?? 1.0;
                $requestData['gamma'] = $options['gamma'] ?? 'scale';
                $requestData['kernel'] = $options['kernel'] ?? 'rbf';
            } elseif ($modelType === 'knn') {
                $requestData['n_neighbors'] = $options['n_neighbors'] ?? 5;
            }

            // Log training start
            Log::info('Training via API started', [
                'dataset_id' => $dataset->DatasetId,
                'user_id' => $user->UserId,
                'session_id' => $options['session_id'] ?? null,
                'options' => $requestData
            ]);

            // Call Flask API
            $apiUrl = config('services.predict_service.url', 'http://predict-service:5000') . '/train/model';
            
            $response = Http::timeout(600) // 10 minutes timeout
                ->withToken(config('app.prediction_api_token', ''))
                ->post($apiUrl, $requestData);

            if (!$response->successful()) {
                Log::error('Training API failed', [
                    'status' => $response->status(),
                    'body' => $response->body()
                ]);

                return [
                    'success' => false,
                    'error' => 'Training API failed: ' . $response->body()
                ];
            }

            $result = $response->json();

            // REMOVED: Don't save model metadata here, Python service will save via API
            // if ($result['success'] ?? false) {
            //     $this->saveModelMetadataFromAPI($dataset, $user, $result);
            // }

            Log::info('Training via API completed', [
                'dataset_id' => $dataset->DatasetId,
                'database_id' => $result['database_id'] ?? null,  // Log database_id from Python
                'mlflow_run_id' => $result['mlflow_run_id'] ?? null,
                'metrics' => $result['metrics'] ?? []
            ]);

            return $result;

        } catch (\Exception $e) {
            Log::error('Training via API exception', [
                'dataset_id' => $dataset->DatasetId,
                'error' => $e->getMessage()
            ]);

            return [
                'success' => false,
                'error' => 'Training failed: ' . $e->getMessage()
            ];
        }
    }

    /**
     * Save model metadata from API response
     * 
     * @param Dataset $dataset
     * @param User $user
     * @param array $apiResult
     * @return MLModel|null
     */
    private function saveModelMetadataFromAPI(Dataset $dataset, User $user, array $apiResult): ?MLModel
    {
        try {
            $metrics = $apiResult['metrics'] ?? [];
            $trainingInfo = $apiResult['training_info'] ?? [];

            $model = MLModel::create([
                'ModelName' => $apiResult['model_name'] ?? 'Unknown Model',
                'ModelPath' => $apiResult['model_path'] ?? '',
                'Version' => '1.0',
                'Description' => 'Trained with dataset: ' . $dataset->DatasetName . 
                               ' | R²: ' . ($metrics['r2_score'] ?? 'N/A') .
                               ' | RMSE: ' . ($metrics['rmse'] ?? 'N/A'),
                'Accuracy' => isset($metrics['r2_score']) ? $metrics['r2_score'] * 100 : null,
                'TrainedBy' => $user->UserId,
                'TrainDate' => now(),
            ]);

            return $model;

        } catch (\Exception $e) {
            Log::error('Failed to save model metadata from API', [
                'error' => $e->getMessage()
            ]);
            return null;
        }
    }
}
