<?php

namespace App\Services;

use App\Models\Dataset;
use App\Models\EmailSetting;
use App\Models\MLModel;
use App\Support\GroqKeyStatus;
use App\Support\PredictServiceUrl;
use App\Models\User;
use Illuminate\Http\Client\ConnectionException;
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

    private function configuredGroqApiKeys(): array
    {
        $keys = GroqKeyStatus::normalizeKeys((string) EmailSetting::get(GroqKeyStatus::KEYS_SETTING, ''));
        $statusMap = GroqKeyStatus::loadStatusMap();

        return GroqKeyStatus::filterUsableKeys($keys, $statusMap);
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
                'sheet_name' => $options['selected_sheet'] ?? $dataset->SelectedSheet ?? null,
                'model_type' => $options['model_type'] ?? 'random_forest',
                'training_scope' => $options['training_scope'] ?? 'all_models_compare',
                'model_name' => $options['model_name'] ?? 'Model_' . $dataset->DatasetName . '_' . date('YmdHis'),
                'test_size' => $options['test_size'] ?? 0.2,
                'random_state' => $options['random_state'] ?? 42,
                'trained_by' => $user->UserId,
                'dataset_id' => $dataset->DatasetId,
                'session_id' => $options['session_id'] ?? null,  // Pass session ID for progress tracking
                'llm_provider' => 'groq',
            ];
            if (!empty($options['llm_model'])) {
                $requestData['llm_model'] = $options['llm_model'];
            }
            $groqApiKeys = $this->configuredGroqApiKeys();
            if (empty($groqApiKeys)) {
                $storedKeys = GroqKeyStatus::normalizeKeys((string) EmailSetting::get(GroqKeyStatus::KEYS_SETTING, ''));

                return [
                    'success' => false,
                    'error' => empty($storedKeys)
                        ? 'No Groq API key is configured. Open Admin > Settings > AI and add at least one key.'
                        : 'All configured Groq API keys are marked blocked. Open Admin > Settings > AI to reactivate or replace a key.',
                ];
            }
            $requestData['groq_api_keys'] = $groqApiKeys;

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
            $safeRequestData = $requestData;
            if (isset($safeRequestData['groq_api_keys'])) {
                $safeRequestData['groq_api_key_count'] = count((array) $safeRequestData['groq_api_keys']);
                unset($safeRequestData['groq_api_keys']);
            }

            Log::info('Training via API started', [
                'dataset_id' => $dataset->DatasetId,
                'user_id' => $user->UserId,
                'session_id' => $options['session_id'] ?? null,
                'options' => $safeRequestData
            ]);

            // Call predict-service, with fallbacks for non-Docker/VPS deployments.
            $response = null;
            $lastConnectionException = null;
            $candidateUrls = PredictServiceUrl::urls('/train/model');

            foreach ($candidateUrls as $apiUrl) {
                try {
                    $response = Http::timeout(600) // 10 minutes timeout
                        ->withToken(config('app.prediction_api_token', ''))
                        ->post($apiUrl, $requestData);

                    if (in_array($response->status(), [404, 502, 503, 504], true)) {
                        Log::warning('Predict-service training endpoint returned fallback-eligible status.', [
                            'url' => $apiUrl,
                            'status' => $response->status(),
                        ]);
                        continue;
                    }

                    break;
                } catch (ConnectionException $exception) {
                    $lastConnectionException = $exception;

                    Log::warning('Predict-service training endpoint connection failed.', [
                        'url' => $apiUrl,
                        'error' => $exception->getMessage(),
                    ]);
                }
            }

            if ($response === null) {
                throw $lastConnectionException ?? new \RuntimeException('Predict-service is unavailable.');
            }

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

            // Guard against empty or non-JSON responses from predict-service.
            if (!is_array($result)) {
                $rawBody = trim((string) $response->body());
                if ($rawBody !== '') {
                    $decoded = json_decode($rawBody, true);
                    if (is_array($decoded)) {
                        $result = $decoded;
                    }
                }
            }

            if (!is_array($result)) {
                Log::error('Training API returned invalid response body', [
                    'status' => $response->status(),
                    'body_preview' => mb_substr((string) $response->body(), 0, 1000),
                ]);

                return [
                    'success' => false,
                    'error' => 'Training API returned an invalid or empty response.'
                ];
            }

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

        } catch (\Throwable $e) {
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

    public function resumeReportPostProcessing(MLModel $model, User $user, array $options = []): array
    {
        try {
            $reportInfo = is_array($model->training_report) ? $model->training_report : [];
            $reportId = trim((string) ($reportInfo['report_id'] ?? $model->MLMName ?? ''));
            if ($reportId === '') {
                return [
                    'success' => false,
                    'error' => 'This model does not have a saved training report bundle to resume.',
                ];
            }

            $groqApiKeys = $this->configuredGroqApiKeys();
            if (empty($groqApiKeys)) {
                $storedKeys = GroqKeyStatus::normalizeKeys((string) EmailSetting::get(GroqKeyStatus::KEYS_SETTING, ''));

                return [
                    'success' => false,
                    'error' => empty($storedKeys)
                        ? 'No Groq API key is configured. Open Admin > Settings > AI and add at least one key.'
                        : 'All configured Groq API keys are marked blocked. Open Admin > Settings > AI to reactivate or replace a key.',
                ];
            }

            $requestData = [
                'report_id' => $reportId,
                'llm_provider' => 'groq',
                'groq_api_keys' => $groqApiKeys,
            ];

            $llmModel = trim((string) ($options['llm_model'] ?? $reportInfo['llm_config']['model'] ?? ''));
            if ($llmModel !== '') {
                $requestData['llm_model'] = $llmModel;
            }

            Log::info('Report post-processing resume requested', [
                'model_id' => $model->id,
                'report_id' => $reportId,
                'user_id' => $user->UserId,
                'groq_api_key_count' => count($groqApiKeys),
            ]);

            $response = null;
            $lastConnectionException = null;
            foreach (PredictServiceUrl::urls('/train/report-post-processing/resume') as $apiUrl) {
                try {
                    $response = Http::timeout(120)
                        ->withToken(config('app.prediction_api_token', ''))
                        ->post($apiUrl, $requestData);

                    if (in_array($response->status(), [404, 502, 503, 504], true)) {
                        Log::warning('Predict-service resume endpoint returned fallback-eligible status.', [
                            'url' => $apiUrl,
                            'status' => $response->status(),
                        ]);
                        continue;
                    }

                    break;
                } catch (ConnectionException $exception) {
                    $lastConnectionException = $exception;

                    Log::warning('Predict-service resume endpoint connection failed.', [
                        'url' => $apiUrl,
                        'error' => $exception->getMessage(),
                    ]);
                }
            }

            if ($response === null) {
                throw $lastConnectionException ?? new \RuntimeException('Predict-service is unavailable.');
            }

            $result = $response->json();
            if (!is_array($result)) {
                $result = [
                    'success' => false,
                    'error' => trim((string) $response->body()) ?: 'Predict-service returned an invalid response.',
                ];
            }

            if (!$response->successful() || !($result['success'] ?? false)) {
                return [
                    'success' => false,
                    'error' => (string) ($result['error'] ?? $result['message'] ?? 'Resume request failed.'),
                ];
            }

            return [
                'success' => true,
                'message' => (string) ($result['message'] ?? 'Report post-processing resume started.'),
                'report_id' => $reportId,
            ];
        } catch (\Throwable $e) {
            Log::error('Report post-processing resume failed', [
                'model_id' => $model->id,
                'error' => $e->getMessage(),
            ]);

            return [
                'success' => false,
                'error' => 'Resume failed: ' . $e->getMessage(),
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
