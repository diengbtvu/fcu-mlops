<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Services\UserService;
use Illuminate\Http\Client\Pool;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Http;
use Firebase\JWT\JWT;
use App\Models\User;
use App\Models\Role;
use App\Models\MLModel;
use App\Models\Prediction;
use App\Models\Permission;

class AdminController extends Controller
{
    private const BENCHMARK_SELECTABLE_ARMS = ['A', 'B', 'C'];
    private const BENCHMARK_CORE_ARTIFACT_ASSET_KEYS = [
        'model_comparison/main' => ['metrics_overview', 'model_comparison_table'],
        'incremental_feature_analysis/main' => ['table1_incremental_results'],
        'feature_ranking/gra' => ['gra_ranking'],
    ];
    private const BENCHMARK_OVERVIEW_PRIORITY_KEYS = [
        'metrics_overview',
        'fig5_model_comparison',
        'model_comparison_bars',
        'fig3_feature_analysis',
        'fig3a_gra_ranking',
        'feature_importance',
        'fig6ab_mse_r2_features',
        'table1_incremental_results',
        'correlation_heatmap',
        'predicted_vs_actual',
    ];

    protected $userService;

    public function __construct(UserService $userService)
    {
        $this->middleware('auth');
        $this->middleware('admin');
        $this->userService = $userService;
    }

    public function dashboard()
    {
        $totalUsers = User::where('role_id', 2)->count();
        $totalModels = MLModel::count();
        $activeModels = MLModel::where('IsActive', true)->count();
        $adminPredictions = Prediction::where('user_id', Auth::id())->count();
        
        return view('admin.dashboard', compact('totalUsers', 'totalModels', 'activeModels', 'adminPredictions'));
    }

    // User Management
    public function users()
    {
        // Only show regular users (non-admin), exclude admin accounts from management
        $users = User::with('role')
            ->withCount('predictions')
            ->where('role_id', '!=', 1) // Exclude admins
            ->orderBy('created_at', 'desc')
            ->paginate(10);
        return view('admin.users.index', compact('users'));
    }

    public function createUser()
    {
        return view('admin.users.create');
    }

    public function storeUser(Request $request)
    {
        $request->validate([
            'FullName' => 'required|string|max:255',
            'Gender' => 'required|in:Male,Female',
            'BirthDate' => 'required|date',
            'Address' => 'required|string|max:255',
            'Username' => 'required|string|max:255|unique:users',
            'Password' => 'required|string|min:6',
        ]);

        try {
            $this->userService->createUser([
                'FullName' => $request->FullName,
                'Gender' => $request->Gender,
                'BirthDate' => $request->BirthDate,
                'Address' => $request->Address,
                'Username' => $request->Username,
                'Password' => $request->Password,
            ]);

            return redirect()->route('admin.users')->with('success', 'User created successfully with auto-generated UserCode.');
        } catch (\Exception $e) {
            return redirect()->back()
                ->withInput()
                ->with('error', 'Failed to create user: ' . $e->getMessage());
        }
    }

    public function editUser(User $user)
    {
        // Allow editing all users including admins to manage roles
        return view('admin.users.edit', compact('user'));
    }

    public function updateUser(Request $request, User $user)
    {
        $request->validate([
            'FullName' => 'required|string|max:255',
            'Gender' => 'required|in:Male,Female',
            'BirthDate' => 'required|date',
            'Address' => 'required|string|max:255',
            'Username' => 'required|string|max:255|unique:users,Username,' . $user->id,
            'role_id' => 'required|integer|in:1,2',
        ]);

        try {
            $updated = $this->userService->updateUser($user, [
                'FullName' => $request->FullName,
                'Gender' => $request->Gender,
                'BirthDate' => $request->BirthDate,
                'Address' => $request->Address,
                'Username' => $request->Username,
                'role_id' => $request->role_id,
            ]);

            if (!$updated) {
                return redirect()->route('admin.users')->with('error', __('users.role_cannot_change_admin'));
            }

            return redirect()->route('admin.users')->with('success', __('users.role_updated'));
        } catch (\Exception $e) {
            return redirect()->back()
                ->withInput()
                ->with('error', 'Failed to update user: ' . $e->getMessage());
        }
    }

    public function resetPassword(User $user)
    {
        try {
            $success = $this->userService->resetPassword($user, 'TempPass@123');
            
            if (!$success) {
                return redirect()->route('admin.users')->with('error', 'Cannot reset admin password.');
            }

            return redirect()->route('admin.users')->with('success', 'Password has been reset to \'TempPass@123\'.');
        } catch (\Exception $e) {
            return redirect()->route('admin.users')->with('error', 'Failed to reset password: ' . $e->getMessage());
        }
    }

    public function deleteUser(User $user)
    {
        try {
            $success = $this->userService->deleteUser($user);
            
            if (!$success) {
                $predictionCount = $user->predictions()->count();
                if ($predictionCount > 0) {
                    return redirect()->route('admin.users')
                        ->with('error', "Cannot delete user '{$user->FullName}' because they have {$predictionCount} associated prediction(s). Use anonymize or force delete instead.");
                } else {
                    return redirect()->route('admin.users')->with('error', 'Cannot delete admin user.');
                }
            }

            return redirect()->route('admin.users')->with('success', "User '{$user->FullName}' deleted successfully.");
        } catch (\Exception $e) {
            return redirect()->route('admin.users')->with('error', 'Failed to delete user: ' . $e->getMessage());
        }
    }

    public function forceDeleteUser(User $user)
    {
        try {
            $predictionCount = $user->predictions()->count();
            $userName = $user->FullName;
            
            $success = $this->userService->deleteUser($user, true);
            
            if (!$success) {
                return redirect()->route('admin.users')->with('error', 'Cannot delete admin user.');
            }
            
            return redirect()->route('admin.users')
                ->with('success', "User '{$userName}' and {$predictionCount} associated prediction(s) deleted successfully.");
        } catch (\Exception $e) {
            return redirect()->route('admin.users')->with('error', 'Failed to force delete user: ' . $e->getMessage());
        }
    }

    public function anonymizeUser(User $user)
    {
        try {
            $originalName = $user->FullName;
            $predictionCount = $user->predictions()->count();
            
            $success = $this->userService->anonymizeUser($user);
            
            if (!$success) {
                return redirect()->route('admin.users')->with('error', 'Cannot anonymize admin user.');
            }
            
            return redirect()->route('admin.users')
                ->with('success', "User '{$originalName}' has been anonymized. {$predictionCount} prediction(s) have been preserved for data integrity.");
        } catch (\Exception $e) {
            return redirect()->route('admin.users')->with('error', 'Failed to anonymize user: ' . $e->getMessage());
        }
    }

    // ML Model Management
    public function models()
    {
        $models = MLModel::with('dataset')->paginate(10);
        return view('admin.models.index', compact('models'));
    }

    public function showModelReport(MLModel $model)
    {
        return view('admin.models.report', $this->buildModelReportViewData($model));
    }

    public function showModelBenchmark(MLModel $model)
    {
        $viewData = $this->buildModelReportViewData($model);
        $summary = is_array($viewData['summary'] ?? null) ? $viewData['summary'] : [];
        $reportAssets = is_array($viewData['reportAssets'] ?? null) ? $viewData['reportAssets'] : [];
        $reportInfo = is_array($viewData['reportInfo'] ?? null) ? $viewData['reportInfo'] : [];
        $routePrefix = '/' . ltrim((string) ($reportInfo['route_prefix'] ?? ''), '/');
        $predictServiceInternalBase = rtrim(
            config('services.predict_service.url', 'http://predict-service:5000'),
            '/'
        );

        $assetJson = function (string $key) use ($reportAssets): ?array {
            $asset = is_array($reportAssets[$key] ?? null) ? $reportAssets[$key] : [];
            $url = (string) ($asset['internal_url'] ?? $asset['public_url'] ?? '');

            return $this->fetchReportJsonAsset($url);
        };

        $leaderboardPayload = $assetJson('benchmark_leaderboard_json') ?? [];
        $runMetadataPayload = $assetJson('benchmark_run_metadata') ?? [];
        $selectedBenchmarkPayload = $assetJson('benchmark_selected_explanations')
            ?? (
                is_array($summary['selected_benchmark_explanations'] ?? null)
                    ? $summary['selected_benchmark_explanations']
                    : []
            );
        $manifestAsset = is_array($reportAssets['benchmark_manifest'] ?? null) ? $reportAssets['benchmark_manifest'] : [];
        $manifestUrl = (string) ($manifestAsset['internal_url'] ?? $manifestAsset['public_url'] ?? '');
        $manifestRows = $this->parseJsonLines($this->fetchReportTextAsset($manifestUrl) ?? '');
        $benchmarkClaimComparisonRows = $this->buildBenchmarkClaimComparisonRows(
            $predictServiceInternalBase,
            $routePrefix,
            is_array($leaderboardPayload['leaderboard'] ?? null) ? $leaderboardPayload['leaderboard'] : [],
            $manifestRows
        );

        return view('admin.models.benchmark', array_merge($viewData, [
            'benchmarkLeaderboardPayload' => $leaderboardPayload,
            'benchmarkRunMetadataPayload' => $runMetadataPayload,
            'benchmarkSelectedPayload' => $selectedBenchmarkPayload,
            'benchmarkClaimComparisonRows' => $benchmarkClaimComparisonRows,
        ]));
    }

    public function createModel()
    {
        return view('admin.models.create');
    }

    public function storeModel(Request $request)
    {
        // Check for PHP upload errors first
        if (!$request->hasFile('model_file')) {
            // Check if this is due to file size limit
            $uploadError = $_FILES['model_file']['error'] ?? UPLOAD_ERR_NO_FILE;
            
            if ($uploadError === UPLOAD_ERR_INI_SIZE) {
                $maxFileSize = ini_get('upload_max_filesize');
                return redirect()->back()
                    ->withInput()
                    ->withErrors(['model_file' => "The model file is too large. Maximum allowed size is {$maxFileSize}. Please increase upload_max_filesize in PHP configuration."]);
            } elseif ($uploadError === UPLOAD_ERR_FORM_SIZE) {
                return redirect()->back()
                    ->withInput()
                    ->withErrors(['model_file' => 'The model file exceeds the form size limit.']);
            } elseif ($uploadError === UPLOAD_ERR_PARTIAL) {
                return redirect()->back()
                    ->withInput()
                    ->withErrors(['model_file' => 'The model file was only partially uploaded. Please try again.']);
            }
        }

        // Debug information
        \Log::info('File upload attempt:', [
            'has_file' => $request->hasFile('model_file'),
            'file_info' => $request->hasFile('model_file') ? [
                'name' => $request->file('model_file')->getClientOriginalName(),
                'extension' => $request->file('model_file')->getClientOriginalExtension(),
                'mime' => $request->file('model_file')->getMimeType(),
                'size' => $request->file('model_file')->getSize(),
            ] : null,
            'libtype' => $request->LibType,
            'upload_error' => $_FILES['model_file']['error'] ?? 'no error info'
        ]);

        $request->validate([
            'MLMName' => 'required|string|max:255',
            'MSEValue' => 'required|numeric|min:0',
            'MAEValue' => 'required|numeric|min:0',
            'model_file' => [
                'required',
                'file',
                'max:102400', // 100MB
                function ($attribute, $value, $fail) {
                    $allowedExtensions = ['h5', 'pkl', 'keras', 'json', 'pt', 'pth', 'joblib', 'xgb'];
                    $extension = strtolower($value->getClientOriginalExtension());
                    
                    \Log::info('File validation:', [
                        'extension' => $extension,
                        'allowed' => $allowedExtensions,
                        'in_array' => in_array($extension, $allowedExtensions)
                    ]);
                    
                    if (!in_array($extension, $allowedExtensions)) {
                        $fail('The ' . $attribute . ' must be a file of type: ' . implode(', ', $allowedExtensions) . '. Got: ' . $extension);
                    }

                    // Check file size against PHP limits
                    $maxUploadSize = $this->parseSize(ini_get('upload_max_filesize'));
                    $maxPostSize = $this->parseSize(ini_get('post_max_size'));
                    $fileSize = $value->getSize();
                    
                    if ($fileSize > $maxUploadSize) {
                        $fail('The ' . $attribute . ' exceeds PHP upload_max_filesize limit (' . ini_get('upload_max_filesize') . ').');
                    }
                    
                    if ($fileSize > $maxPostSize) {
                        $fail('The ' . $attribute . ' exceeds PHP post_max_size limit (' . ini_get('post_max_size') . ').');
                    }
                }
            ],
            'LibType' => 'required|string|in:keras,pytorch,sklearn,xgboost,pickle,joblib',
        ]);

        $file = $request->file('model_file');
        $filename = time() . '_' . $file->getClientOriginalName();
        
        // Store in public/models directory directly (not storage/app/public)
        $destinationPath = public_path('models');
        if (!file_exists($destinationPath)) {
            mkdir($destinationPath, 0755, true);
        }
        
        $file->move($destinationPath, $filename);
        
        MLModel::create([
            'MLMName' => $request->MLMName,
            'FilePath' => 'models/' . $filename, // Store relative path from public directory
            'LibType' => $request->LibType,
            'IsActive' => $request->has('IsActive'),
            'MSEValue' => $request->MSEValue ?? 0.0, // Default to 0 if not provided
            'MAEValue' => $request->MAEValue ?? 0.0, // Default to 0 if not provided
        ]);

        return redirect()->route('admin.models')->with('success', 'Model uploaded successfully.');
    }

    /**
     * Parse size string (like "2M", "128K") to bytes
     */
    private function parseSize($size) {
        $unit = preg_replace('/[^bkmgtpezy]/i', '', $size);
        $size = preg_replace('/[^0-9\.]/', '', $size);
        
        if ($unit) {
            return round($size * pow(1024, stripos('bkmgtpezy', $unit[0])));
        }
        
        return round($size);
    }

    public function editModel(MLModel $model)
    {
        return view('admin.models.edit', compact('model'));
    }

    public function updateModel(Request $request, MLModel $model)
    {
        // Check for PHP upload errors if file is being uploaded
        if ($request->hasFile('model_file') || (isset($_FILES['model_file']) && $_FILES['model_file']['error'] !== UPLOAD_ERR_NO_FILE)) {
            $uploadError = $_FILES['model_file']['error'] ?? UPLOAD_ERR_NO_FILE;
            
            if ($uploadError === UPLOAD_ERR_INI_SIZE) {
                $maxFileSize = ini_get('upload_max_filesize');
                return redirect()->back()
                    ->withInput()
                    ->withErrors(['model_file' => "The model file is too large. Maximum allowed size is {$maxFileSize}. Please increase upload_max_filesize in PHP configuration."]);
            } elseif ($uploadError === UPLOAD_ERR_FORM_SIZE) {
                return redirect()->back()
                    ->withInput()
                    ->withErrors(['model_file' => 'The model file exceeds the form size limit.']);
            } elseif ($uploadError === UPLOAD_ERR_PARTIAL) {
                return redirect()->back()
                    ->withInput()
                    ->withErrors(['model_file' => 'The model file was only partially uploaded. Please try again.']);
            }
        }

        $request->validate([
            'MLMName' => 'required|string|max:255',
            'MSEValue' => 'nullable|numeric|min:0',
            'MAEValue' => 'nullable|numeric|min:0',
            'model_file' => [
                'nullable',
                'file',
                'max:102400', // 100MB
                function ($attribute, $value, $fail) {
                    if ($value) {
                        $allowedExtensions = ['h5', 'pkl', 'keras', 'json', 'pt', 'pth', 'joblib', 'xgb'];
                        $extension = strtolower($value->getClientOriginalExtension());
                        
                        if (!in_array($extension, $allowedExtensions)) {
                            $fail('The ' . $attribute . ' must be a file of type: ' . implode(', ', $allowedExtensions) . '.');
                        }

                        // Check file size against PHP limits
                        $maxUploadSize = $this->parseSize(ini_get('upload_max_filesize'));
                        $maxPostSize = $this->parseSize(ini_get('post_max_size'));
                        $fileSize = $value->getSize();
                        
                        if ($fileSize > $maxUploadSize) {
                            $fail('The ' . $attribute . ' exceeds PHP upload_max_filesize limit (' . ini_get('upload_max_filesize') . ').');
                        }
                        
                        if ($fileSize > $maxPostSize) {
                            $fail('The ' . $attribute . ' exceeds PHP post_max_size limit (' . ini_get('post_max_size') . ').');
                        }
                    }
                }
            ],
            'LibType' => 'required|string|in:keras,pytorch,sklearn,xgboost,pickle,joblib',
        ]);

        $data = [
            'MLMName' => $request->MLMName,
            'LibType' => $request->LibType,
            'IsActive' => $request->has('IsActive'),
            'MSEValue' => $request->MSEValue ?? $model->MSEValue ?? 0.0,
            'MAEValue' => $request->MAEValue ?? $model->MAEValue ?? 0.0,
        ];

        if ($request->hasFile('model_file')) {
            // Delete old file from public/models
            if ($model->FilePath) {
                $oldFilePath = public_path($model->FilePath);
                if (file_exists($oldFilePath)) {
                    unlink($oldFilePath);
                }
            }

            // Upload new file to public/models
            $file = $request->file('model_file');
            $filename = time() . '_' . $file->getClientOriginalName();
            
            $destinationPath = public_path('models');
            if (!file_exists($destinationPath)) {
                mkdir($destinationPath, 0755, true);
            }
            
            $file->move($destinationPath, $filename);
            $data['FilePath'] = 'models/' . $filename;
        }

        $model->update($data);

        return redirect()->route('admin.models')->with('success', 'Model updated successfully.');
    }

    public function deleteModel(MLModel $model)
    {
        // Check if this is the default model (protect it)
        if ($this->isDefaultModel($model)) {
            return redirect()->route('admin.models')
                ->with('error', "Cannot delete '{$model->MLMName}' because it is the default system model. The system needs at least one default model to function properly.");
        }
        
        // Check if model has associated predictions
        $predictionCount = $model->predictions()->count();
        
        if ($predictionCount > 0) {
            return redirect()->route('admin.models')
                ->with('error', "Cannot delete model '{$model->MLMName}' because it has {$predictionCount} associated prediction(s). Please delete the predictions first or consider deactivating the model instead.");
        }
        
        // Delete file from public/models
        if ($model->FilePath) {
            $filePath = public_path($model->FilePath);
            if (file_exists($filePath)) {
                unlink($filePath);
            }
        }

        $modelName = $model->MLMName;
        $model->delete();
        
        return redirect()->route('admin.models')->with('success', "Model '{$modelName}' deleted successfully.");
    }

    private function isDefaultModel(MLModel $model): bool
    {
        return $model->id === 1;
    }

    public function forceDeleteModel(MLModel $model)
    {
        // Force delete: delete all associated predictions first
        $predictionCount = $model->predictions()->count();
        
        if ($predictionCount > 0) {
            $model->predictions()->delete();
        }
        
        // Delete file from public/models
        if ($model->FilePath) {
            $filePath = public_path($model->FilePath);
            if (file_exists($filePath)) {
                unlink($filePath);
            }
        }

        $modelName = $model->MLMName;
        $model->delete();
        
        return redirect()->route('admin.models')
            ->with('success', "Model '{$modelName}' and {$predictionCount} associated prediction(s) deleted successfully.");
    }

    public function testModel(Request $request, MLModel $model)
    {
        // Test the model with sample data
        $request->validate($this->predictionFeatureValidationRules());

        try {
            // Check if model file exists
            if (!$model->fileExists()) {
                return response()->json([
                    'success' => false,
                    'error' => 'Model file not found on server.'
                ], 404);
            }

            // Test API connection
            $apiUrl = config('services.predict_service.url', 'http://predict-service:5000');
            try {
                $healthResponse = Http::timeout(5)->get($apiUrl . '/predict/health');
                if (!$healthResponse->successful()) {
                    return response()->json([
                        'success' => false,
                        'error' => 'Prediction service is not available.'
                    ], 503);
                }
            } catch (\Exception $e) {
                return response()->json([
                    'success' => false,
                    'error' => 'Cannot connect to prediction service: ' . $e->getMessage()
                ], 503);
            }

            // Generate test token (similar to user token but for admin)
            $payload = [
                'user_id' => auth()->id(),
                'username' => auth()->user()->Username,
                'iat' => time(),
                'exp' => time() + (60 * 60), // 1 hour expiration
            ];
            $secretKey = env('JWT_SECRET', 'jwt_secret');
            $token = \Firebase\JWT\JWT::encode($payload, $secretKey, 'HS256');

            // Prepare test payload
            $testPayload = array_merge($this->extractPredictionFeatures($request), [
                'model_path' => $model->absolute_path,
                'model_type' => strtolower($model->LibType),
            ]);

            // Call Flask API using the new universal endpoint
            $response = Http::withHeaders([
                'Authorization' => 'Bearer ' . $token,
                'Content-Type' => 'application/json',
            ])->post($apiUrl . '/predict/model', $testPayload);

            if ($response->successful()) {
                $responseData = $response->json();
                return response()->json([
                    'success' => true,
                    'prediction' => round($responseData['prediction'], 2),
                    'model_used' => $responseData['model_used'] ?? $model->MLMName,
                    'message' => 'Model test successful!'
                ]);
            } else {
                $errorMessage = 'Model test failed';
                $responseBody = $response->json();
                
                if ($responseBody && isset($responseBody['error'])) {
                    $errorMessage = $responseBody['error'];
                }
                
                return response()->json([
                    'success' => false,
                    'error' => $errorMessage,
                    'debug_info' => env('APP_DEBUG') ? [
                        'api_status' => $response->status(),
                        'api_response' => $response->body()
                    ] : null
                ], $response->status());
            }

        } catch (\Exception $e) {
            \Log::error('Exception in testModel', [
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return response()->json([
                'success' => false,
                'error' => 'Error testing model: ' . $e->getMessage(),
            ], 500);
        }
    }

    // Prediction methods for admin
    public function predict()
    {
        // Only expose pipeline-trained MLflow models on the prediction page.
        $models = MLModel::where('IsActive', true)
            ->whereNotNull('mlflow_run_id')
            ->where('mlflow_run_id', '!=', '')
            ->whereNotNull('training_report')
            ->get();
        return view('admin.predict', compact('models'));
    }

    private function testApiConnection()
    {
        $apiUrl = config('services.predict_service.url', 'http://predict-service:5000');
        try {
            $response = Http::timeout(5)->get($apiUrl . '/predict/health');
            return $response->successful();
        } catch (\Exception $e) {
            \Log::error('API health check failed: ' . $e->getMessage());
            return false;
        }
    }

    public function makePrediction(Request $request)
    {
        $request->validate(array_merge(
            $this->predictionFeatureValidationRules(),
            ['ml_model_id' => 'required|exists:ml_models,id']
        ));

        try {
            // Get selected model
            $selectedModel = MLModel::findOrFail($request->ml_model_id);
            
            // Check if model is active
            if (!$selectedModel->IsActive) {
                return response()->json([
                    'success' => false,
                    'error' => 'Selected model is not active.'
                ], 400);
            }

            // Check if API service is available first
            if (!$this->testApiConnection()) {
                return response()->json([
                    'success' => false,
                    'error' => 'Prediction service is not available. Please try again later.'
                ], 503);
            }

            $apiUrl = config('services.predict_service.url', 'http://predict-service:5000');
            $token = $this->generateApiToken();

            if (empty($selectedModel->mlflow_run_id)) {
                return response()->json([
                    'success' => false,
                    'error' => 'Selected model is not registered in MLflow.'
                ], 400);
            }

            return $this->predictWithMLflow($selectedModel, $request, $apiUrl, $token);

        } catch (\Exception $e) {
            \Log::error('Exception in makePrediction (Admin)', [
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return response()->json([
                'success' => false,
                'error' => 'Error connecting to prediction service: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * 🆕 Predict using MLflow model (with intelligent caching)
     */
    private function predictWithMLflow($selectedModel, $request, $apiUrl, $token)
    {
        \Log::info('Using MLflow prediction (Admin)', [
            'model' => $selectedModel->MLMName,
            'mlflow_run_id' => $selectedModel->mlflow_run_id
        ]);

        // Prepare features for MLflow API
        $features = $this->extractPredictionFeatures($request);
        $payload = [
            'run_id' => $selectedModel->mlflow_run_id,
            'features' => $features,
        ];

        $response = Http::withHeaders([
            'Authorization' => 'Bearer ' . $token,
            'Content-Type' => 'application/json',
        ])->post($apiUrl . '/predict/mlflow', $payload);

        if ($response->successful()) {
            $responseData = $response->json();
            $prediction = $responseData['prediction'];
            
            // Save prediction to database
            Prediction::create($this->buildPredictionCreateData($selectedModel->id, $features, (float)$prediction));

            return response()->json([
                'success' => true,
                'prediction' => round($prediction, 2),
                'unit' => $responseData['unit'] ?? 'L/h/L',
                'model_used' => $selectedModel->MLMName,
                'model_source' => 'mlflow',  // 🆕 Indicate source
                'cached' => $responseData['cached'] ?? false,  // 🆕 Cache status
                'mlflow_run_id' => $selectedModel->mlflow_run_id,
                'message' => 'Prediction successful (MLflow) and saved to database!'
            ]);
        } else {
            $errorMessage = 'Failed to get prediction from MLflow API';
            $responseBody = $response->json();
            
            if ($responseBody && isset($responseBody['error'])) {
                $errorMessage = $responseBody['error'];
            }
            
            \Log::error('MLflow prediction failed (Admin)', [
                'status' => $response->status(),
                'response' => $response->body()
            ]);
            
            return response()->json([
                'success' => false,
                'error' => $errorMessage,
            ], $response->status());
        }
    }

    /**
     * Traditional file-based prediction (backward compatible)
     */
    private function predictWithFileModel($selectedModel, $request, $apiUrl, $token)
    {
        // Prepare model file path (convert relative path to absolute)
        $modelPath = public_path($selectedModel->FilePath);
        
        // Verify model file exists
        if (!file_exists($modelPath)) {
            return response()->json([
                'success' => false,
                'error' => 'Model file not found on server.'
            ], 404);
        }

        \Log::info('Using file-based prediction (Admin)', [
            'model' => $selectedModel->MLMName,
            'file_path' => $modelPath
        ]);

        $features = $this->extractPredictionFeatures($request);

        // Prepare payload with model path and type
        $payload = array_merge($features, [
            'model_path' => $modelPath,
            'model_type' => strtolower($selectedModel->LibType),
        ]);
        
        $response = Http::withHeaders([
            'Authorization' => 'Bearer ' . $token,
            'Content-Type' => 'application/json',
        ])->post($apiUrl . '/predict/model', $payload);

        if ($response->successful()) {
            $responseData = $response->json();
            $prediction = $responseData['prediction'];
            
            // Save prediction to database
            Prediction::create($this->buildPredictionCreateData($selectedModel->id, $features, (float)$prediction));

            return response()->json([
                'success' => true,
                'prediction' => round($prediction, 2),
                'unit' => $responseData['unit'] ?? 'L/h/L',
                'model_used' => $selectedModel->MLMName,
                'model_source' => 'file',  // 🆕 Indicate source
                'message' => 'Prediction successful and saved to database!'
            ]);
        } else {
            $errorMessage = 'Failed to get prediction from API';
            $responseBody = $response->json();
            
            if ($response->status() === 401) {
                $errorMessage = 'Authentication failed with prediction service';
            } elseif ($responseBody && isset($responseBody['error'])) {
                $errorMessage = $responseBody['error'];
            }
            
            \Log::error('File-based prediction failed (Admin)', [
                'status' => $response->status(),
                'response' => $response->body()
            ]);
            
            return response()->json([
                'success' => false,
                'error' => $errorMessage,
            ], $response->status());
        }
    }

    public function history()
    {
        $predictions = Prediction::with('mlModel')
            ->where('user_id', Auth::id())
            ->orderBy('created_at', 'desc')
            ->paginate(10);
        
        return view('admin.history', compact('predictions'));
    }

    private function predictionFeatureValidationRules(): array
    {
        $rules = [];

        foreach (config('prediction.features', []) as $fieldName => $fieldConfig) {
            $rules[$fieldName] = [
                'required',
                'numeric',
                'min:' . $fieldConfig['min'],
                'max:' . $fieldConfig['max'],
            ];
        }

        return $rules;
    }

    private function extractPredictionFeatures(Request $request): array
    {
        return [
            'ph' => (float) $request->ph,
            'vss' => (float) $request->vss,
            'ethanol' => (float) $request->ethanol,
            'acetate' => (float) $request->acetate,
            'propionate' => (float) $request->propionate,
            'butyrate' => (float) $request->butyrate,
            'sucrose_degradation' => (float) $request->sucrose_degradation,
            'orp_mid' => (float) $request->orp_mid,
            'orp_low' => (float) $request->orp_low,
            'vfa' => (float) $request->vfa,
            'cod_o' => (float) $request->cod_o,
        ];
    }

    private function buildPredictionCreateData(int $modelId, array $features, float $prediction): array
    {
        return [
            'user_id' => Auth::id(),
            'ml_model_id' => $modelId,
            'pH' => $features['ph'],
            'VSS' => $features['vss'],
            'Ethanol' => $features['ethanol'],
            'Acetate' => $features['acetate'],
            'Propionate' => $features['propionate'],
            'Butyrate' => $features['butyrate'],
            'Sucrose_Degradation' => $features['sucrose_degradation'],
            'ORP_Mid' => $features['orp_mid'],
            'ORP_Low' => $features['orp_low'],
            'VFA' => $features['vfa'],
            'COD_O' => $features['cod_o'],
            'HPR' => $prediction,
            'PredictionDateTime' => now(),
        ];
    }

    private function generateApiToken()
    {
        // Generate proper JWT token compatible with Flask API
        $payload = [
            'user_id' => Auth::id(),
            'username' => Auth::user()->Username,
            'iat' => time(),
            'exp' => time() + (60 * 60), // 1 hour expiration
        ];
        
        // Use the same secret key as Flask API (default: 'jwt_secret')
        $secretKey = env('JWT_SECRET', 'jwt_secret');
        
        // Create proper JWT token using Firebase JWT library
        return JWT::encode($payload, $secretKey, 'HS256');
    }

    // Role & Permission Management
    public function roles()
    {
        $roles = Role::with('permissions')->get();
        return view('admin.roles.index', compact('roles'));
    }

    public function showRole(Role $role)
    {
        $role->load('permissions');
        $allPermissions = Permission::all();
        return view('admin.roles.show', compact('role', 'allPermissions'));
    }

    public function updateRolePermissions(Request $request, Role $role)
    {
        $request->validate([
            'permissions' => 'array',
            'permissions.*' => 'exists:permissions,id'
        ]);

        try {
            $role->permissions()->sync($request->permissions ?? []);
            return redirect()->route('admin.roles')->with('success', __('permissions.updated_successfully'));
        } catch (\Exception $e) {
            return redirect()->back()->with('error', 'Failed to update permissions: ' . $e->getMessage());
        }
    }

    // User-specific Permission Management
    public function showUserPermissions(User $user)
    {
        $user->load(['role.permissions', 'userPermissions']);
        $allPermissions = Permission::all();
        
        // Get role permissions for reference
        $rolePermissions = $user->role->permissions->pluck('id')->toArray();
        
        // Get user-specific overrides
        $userPermissions = $user->userPermissions->mapWithKeys(function ($permission) {
            return [$permission->id => $permission->pivot->granted];
        })->toArray();
        
        return view('admin.users.permissions', compact('user', 'allPermissions', 'rolePermissions', 'userPermissions'));
    }

    public function updateUserPermissions(Request $request, User $user)
    {
        try {
            // Decode JSON permissions from hidden input
            $permissions = json_decode($request->input('permissions', '[]'), true) ?? [];
            
            // Sync user permissions with granted/revoked status
            $syncData = [];
            foreach ($permissions as $permission) {
                if (isset($permission['permission_id']) && isset($permission['granted'])) {
                    $syncData[$permission['permission_id']] = ['granted' => (bool)$permission['granted']];
                }
            }
            
            $user->userPermissions()->sync($syncData);
            
            return redirect()->route('admin.users.permissions', $user)->with('success', 'User permissions updated successfully!');
        } catch (\Exception $e) {
            \Log::error('Failed to update user permissions', [
                'user_id' => $user->id,
                'error' => $e->getMessage(),
                'request_data' => $request->all()
            ]);
            
            return redirect()->back()->with('error', 'Failed to update user permissions: ' . $e->getMessage());
        }
    }
    
    // Admin Profile Management
    public function profile()
    {
        $admin = Auth::user();
        return view('admin.profile.index', compact('admin'));
    }
    
    public function updateProfile(Request $request)
    {
        $admin = Auth::user();
        
        $request->validate([
            'FullName' => 'required|string|max:255',
            'Gender' => 'required|in:Male,Female',
            'BirthDate' => 'required|date',
            'Address' => 'required|string|max:255',
            'Username' => 'required|string|max:255|unique:users,Username,' . $admin->id,
            'email' => 'nullable|email|max:255|unique:users,email,' . $admin->id,
        ]);

        try {
            $admin->update([
                'FullName' => $request->FullName,
                'Gender' => $request->Gender,
                'BirthDate' => $request->BirthDate,
                'Address' => $request->Address,
                'Username' => $request->Username,
                'email' => $request->email,
            ]);

            return redirect()->route('admin.profile')->with('success', __('profile.update_success'));
        } catch (\Exception $e) {
            return redirect()->back()
                ->withInput()
                ->with('error', __('profile.update_error') . ': ' . $e->getMessage());
        }
    }
    
    public function updatePassword(Request $request)
    {
        $admin = Auth::user();
        
        $request->validate([
            'current_password' => 'required',
            'new_password' => 'required|string|min:6|confirmed',
        ]);

        try {
            // Verify current password
            if (!Hash::check($request->current_password, $admin->Password)) {
                return redirect()->back()->with('error', __('profile.current_password_incorrect'));
            }
            
            // Update password
            $admin->update([
                'Password' => Hash::make($request->new_password),
            ]);

            return redirect()->route('admin.profile')->with('success', __('profile.password_success'));
        } catch (\Exception $e) {
            return redirect()->back()->with('error', __('profile.password_error') . ': ' . $e->getMessage());
        }
    }

    // User Roles Management (Permission Groups)
    public function showUserRoles(User $user)
    {
        $user->load('roles.permissions', 'role');
        
        // Get all permission group roles (exclude admin and default user role)
        $permissionGroups = Role::whereNotIn('id', [1, 2])->with('permissions')->get();
        
        // Get currently assigned role IDs
        $assignedRoleIds = $user->roles->pluck('id')->toArray();
        
        return view('admin.users.roles', compact('user', 'permissionGroups', 'assignedRoleIds'));
    }

    public function updateUserRoles(Request $request, User $user)
    {
        $request->validate([
            'roles' => 'array',
            'roles.*' => 'exists:roles,id'
        ]);

        try {
            // Only sync permission group roles (exclude admin and default user)
            $roleIds = collect($request->roles ?? [])->filter(function($roleId) {
                return !in_array($roleId, [1, 2]);
            })->toArray();
            
            $user->roles()->sync($roleIds);
            
            return redirect()->route('admin.users.roles', $user)
                ->with('success', 'Permission groups updated successfully!');
        } catch (\Exception $e) {
            \Log::error('Failed to update user roles', [
                'user_id' => $user->id,
                'error' => $e->getMessage(),
                'request_data' => $request->all()
            ]);
            
            return redirect()->back()->with('error', 'Failed to update permission groups: ' . $e->getMessage());
        }
    }

    private function fetchReportCsvTable(string $url, int $maxRows = 60): ?array
    {
        try {
            $response = Http::timeout(20)->get($url);
            if (!$response->successful()) {
                return null;
            }

            return $this->parseCsvTable($response->body(), $maxRows);
        } catch (\Throwable $e) {
            return null;
        }
    }

    private function fetchReportJsonAsset(?string $url): ?array
    {
        if (!is_string($url) || trim($url) === '') {
            return null;
        }

        try {
            $response = Http::timeout(20)->acceptJson()->get($url);
            if (!$response->successful()) {
                return null;
            }

            $payload = $response->json();

            return is_array($payload) ? $payload : null;
        } catch (\Throwable $e) {
            return null;
        }
    }

    private function fetchReportTextAsset(?string $url): ?string
    {
        if (!is_string($url) || trim($url) === '') {
            return null;
        }

        try {
            $response = Http::timeout(20)->get($url);
            if (!$response->successful()) {
                return null;
            }

            return $response->body();
        } catch (\Throwable $e) {
            return null;
        }
    }

    private function parseJsonLines(string $content): array
    {
        $rows = [];
        foreach (preg_split("/\r\n|\n|\r/", $content) as $line) {
            $line = trim((string) $line);
            if ($line === '') {
                continue;
            }

            try {
                $decoded = json_decode($line, true, 512, JSON_THROW_ON_ERROR);
            } catch (\Throwable $e) {
                continue;
            }

            if (is_array($decoded)) {
                $rows[] = $decoded;
            }
        }

        return $rows;
    }

    private function parseCsvTable(string $csv, int $maxRows = 60): ?array
    {
        $stream = fopen('php://temp', 'r+');
        if ($stream === false) {
            return null;
        }

        fwrite($stream, $csv);
        rewind($stream);

        $headers = fgetcsv($stream);
        if (!is_array($headers) || empty($headers)) {
            fclose($stream);
            return null;
        }

        $rows = [];
        $rowCount = 0;
        while (($row = fgetcsv($stream)) !== false) {
            $rowCount++;
            if ($rowCount <= $maxRows) {
                $normalizedRow = [];
                foreach ($headers as $index => $header) {
                    $normalizedRow[(string) $header] = $row[$index] ?? '';
                }
                $rows[] = $normalizedRow;
            }
        }

        fclose($stream);

        return [
            'headers' => array_map('strval', $headers),
            'rows' => $rows,
            'row_count' => $rowCount,
            'truncated' => $rowCount > $maxRows,
        ];
    }

    private function sanitizeReportId(string $modelName): string
    {
        $cleaned = preg_replace('/[^A-Za-z0-9._-]+/', '_', $modelName) ?? '';
        $cleaned = trim($cleaned, '_');

        if ($cleaned === '') {
            $cleaned = 'model_' . uniqid();
        }

        return substr($cleaned, 0, 180);
    }

    private function benchmarkRowKey(array $row): string
    {
        $arm = trim((string) ($row['arm'] ?? ''));
        $condition = trim((string) ($row['input_condition'] ?? ''));
        $semanticLevel = trim((string) ($row['semantic_level'] ?? ''));

        if ($arm === '' || $condition === '') {
            return '';
        }

        return implode('|', [$arm, $condition, $semanticLevel !== '' ? $semanticLevel : '-']);
    }

    private function benchmarkRowLabel(array $row): string
    {
        $parts = [];
        $arm = trim((string) ($row['arm'] ?? ''));
        $condition = trim((string) ($row['input_condition'] ?? ''));
        $semanticLevel = trim((string) ($row['semantic_level'] ?? ''));

        if ($arm !== '') {
            $parts[] = $arm;
        }
        if ($condition !== '') {
            $parts[] = $condition;
        }
        if ($semanticLevel !== '') {
            $parts[] = $semanticLevel;
        }

        return !empty($parts) ? implode(' · ', $parts) : 'n/a';
    }

    private function normalizeSelectableBenchmarkRows(array $leaderboardRows): array
    {
        $rows = [];
        $seen = [];

        foreach ($leaderboardRows as $row) {
            if (!is_array($row)) {
                continue;
            }

            $arm = trim((string) ($row['arm'] ?? ''));
            $condition = trim((string) ($row['input_condition'] ?? ''));
            if ($arm === '' || $condition === '' || !in_array($arm, self::BENCHMARK_SELECTABLE_ARMS, true)) {
                continue;
            }

            $normalized = $row;
            $normalized['semantic_level'] = trim((string) ($row['semantic_level'] ?? '')) ?: null;
            $normalized['row_key'] = $this->benchmarkRowKey($normalized);
            $normalized['label'] = $this->benchmarkRowLabel($normalized);

            if ($normalized['row_key'] === '' || isset($seen[$normalized['row_key']])) {
                continue;
            }

            $rows[] = $normalized;
            $seen[$normalized['row_key']] = true;
        }

        return $rows;
    }

    private function findBenchmarkRowByKey(array $rows, ?string $rowKey): ?array
    {
        $rowKey = trim((string) $rowKey);
        if ($rowKey === '') {
            return null;
        }

        foreach ($rows as $row) {
            if (!is_array($row)) {
                continue;
            }

            if ((string) ($row['row_key'] ?? '') === $rowKey) {
                return $row;
            }
        }

        return null;
    }

    private function extractBenchmarkReferenceRow(array $payload): array
    {
        $selectedRow = is_array($payload['selected_row'] ?? null) ? $payload['selected_row'] : [];
        $arm = trim((string) ($selectedRow['arm'] ?? $payload['selected_arm'] ?? ''));
        $condition = trim((string) ($selectedRow['input_condition'] ?? $payload['selected_condition'] ?? ''));
        $semanticLevel = trim((string) ($selectedRow['semantic_level'] ?? $payload['selected_semantic_level'] ?? ''));

        if ($arm === '' || $condition === '') {
            return [];
        }

        return [
            'arm' => $arm,
            'input_condition' => $condition,
            'semantic_level' => $semanticLevel !== '' ? $semanticLevel : null,
        ];
    }

    private function resolveDefaultBenchmarkDisplayRow(
        array $selectableRows,
        array $selectedBenchmarkExplanations,
        array $benchmarkSummary
    ): ?array {
        $candidateRows = [
            $this->extractBenchmarkReferenceRow($selectedBenchmarkExplanations),
            $this->extractBenchmarkReferenceRow(is_array($benchmarkSummary['selected_explanations'] ?? null)
                ? $benchmarkSummary['selected_explanations']
                : []),
            $this->extractBenchmarkReferenceRow(is_array($benchmarkSummary['best_overall'] ?? null)
                ? $benchmarkSummary['best_overall']
                : []),
        ];

        foreach ($candidateRows as $candidate) {
            if (empty($candidate)) {
                continue;
            }

            $matched = $this->findBenchmarkRowByKey($selectableRows, $this->benchmarkRowKey($candidate));
            if ($matched !== null) {
                return $matched;
            }
        }

        $first = $selectableRows[0] ?? null;
        return is_array($first) ? $first : null;
    }

    private function benchmarkGenerationFileName(
        string $artifactId,
        string $arm,
        string $condition,
        ?string $semanticLevel = null
    ): string {
        $parts = [$artifactId, $arm];
        if (is_string($semanticLevel) && trim($semanticLevel) !== '') {
            $parts[] = trim($semanticLevel);
        }
        $parts[] = $condition;

        return $this->slugifyBenchmarkValue(implode('_', $parts)) . '.json';
    }

    private function slugifyBenchmarkValue(string $value): string
    {
        $cleaned = strtolower(preg_replace('/[^A-Za-z0-9]+/', '_', $value) ?? '');
        $cleaned = preg_replace('/_+/', '_', $cleaned) ?? '';
        $cleaned = trim($cleaned, '_');

        return $cleaned !== '' ? $cleaned : 'benchmark';
    }

    private function benchmarkGoldFileName(string $artifactId): string
    {
        return $this->slugifyBenchmarkValue($artifactId) . '.json';
    }

    private function fetchJsonAssetMap(array $urlMap, int $chunkSize = 24): array
    {
        $payloads = [];
        if (empty($urlMap)) {
            return $payloads;
        }

        foreach (array_chunk($urlMap, $chunkSize, true) as $chunk) {
            $responses = Http::pool(function (Pool $pool) use ($chunk) {
                $requests = [];
                foreach ($chunk as $key => $url) {
                    $requests[$key] = $pool
                        ->as((string) $key)
                        ->timeout(20)
                        ->acceptJson()
                        ->get($url);
                }
                return $requests;
            });

            foreach ($chunk as $key => $url) {
                $response = $responses[$key] ?? null;
                if ($response === null || !$response->successful()) {
                    continue;
                }

                $decoded = $response->json();
                if (is_array($decoded)) {
                    $payloads[$key] = $decoded;
                }
            }
        }

        return $payloads;
    }

    private function benchmarkArtifactTitle(array $manifestRow): string
    {
        $assetTitle = trim((string) ($manifestRow['asset_title'] ?? ''));
        if ($assetTitle !== '') {
            return $assetTitle;
        }

        $artifactType = trim((string) ($manifestRow['artifact_type'] ?? ''));
        return match ($artifactType) {
            'model_comparison/main' => 'Model comparison table',
            'incremental_feature_analysis/main' => 'Incremental feature analysis',
            'feature_ranking/gra' => 'GRA feature ranking',
            default => trim((string) ($manifestRow['asset_key'] ?? $manifestRow['artifact_id'] ?? 'n/a')),
        };
    }

    private function stringifyBenchmarkFactField($value): string
    {
        if (is_scalar($value) || $value === null) {
            return trim((string) $value);
        }

        if (is_array($value)) {
            $parts = [];
            foreach ($value as $item) {
                $text = $this->stringifyBenchmarkFactField($item);
                if ($text !== '') {
                    $parts[] = $text;
                }
            }
            return implode(' > ', $parts);
        }

        return trim((string) json_encode($value));
    }

    private function formatBenchmarkGoldFact(array $fact): string
    {
        $parts = [];
        $factType = trim((string) ($fact['fact_type'] ?? ''));
        $subject = trim((string) ($fact['subject'] ?? ''));
        $predicate = trim((string) ($fact['predicate'] ?? ''));
        $object = $this->stringifyBenchmarkFactField($fact['object'] ?? null);
        $value = $fact['value'] ?? null;

        if ($factType !== '') {
            $parts[] = $factType;
        }
        if ($subject !== '') {
            $parts[] = $subject;
        }
        if ($predicate !== '') {
            $parts[] = $predicate;
        }

        $label = implode(' · ', $parts);
        if ($object !== '') {
            $label .= ($label !== '' ? ' -> ' : '') . $object;
        }
        if (is_numeric($value)) {
            $label .= ($label !== '' ? ' = ' : '') . number_format((float) $value, 6, '.', '');
        } elseif ($value !== null) {
            $valueText = $this->stringifyBenchmarkFactField($value);
            if ($valueText !== '') {
                $label .= ($label !== '' ? ' = ' : '') . $valueText;
            }
        }

        return $label !== '' ? $label : 'n/a';
    }

    private function formatBenchmarkGoldEvidence(array $fact): string
    {
        $evidenceRows = is_array($fact['evidence'] ?? null) ? $fact['evidence'] : [];
        $parts = [];

        foreach ($evidenceRows as $evidence) {
            if (!is_array($evidence)) {
                continue;
            }
            $sourceFile = trim((string) ($evidence['source_file'] ?? ''));
            $detail = trim((string) ($evidence['detail'] ?? ''));
            $text = $sourceFile;
            if ($detail !== '') {
                $text .= ($text !== '' ? ' - ' : '') . $detail;
            }
            if ($text !== '') {
                $parts[] = $text;
            }
        }

        return !empty($parts) ? implode("\n", $parts) : 'n/a';
    }

    private function formatBenchmarkGoldValue(array $fact): string
    {
        $value = $fact['value'] ?? null;
        if (is_numeric($value)) {
            return number_format((float) $value, 6, '.', '');
        }

        $object = $this->stringifyBenchmarkFactField($fact['object'] ?? null);
        if ($object !== '') {
            return $object;
        }

        if ($value !== null) {
            $valueText = $this->stringifyBenchmarkFactField($value);
            if ($valueText !== '') {
                return $valueText;
            }
        }

        return 'n/a';
    }

    private function benchmarkPlaceholderGoldSummary(array $facts, int $limit = 2): string
    {
        $sortedFacts = array_values(array_filter($facts, 'is_array'));
        usort($sortedFacts, function ($left, $right) {
            return ((int) ($right['importance'] ?? 0)) <=> ((int) ($left['importance'] ?? 0));
        });

        $labels = [];
        foreach (array_slice($sortedFacts, 0, $limit) as $fact) {
            $labels[] = $this->formatBenchmarkGoldFact($fact);
        }

        return !empty($labels) ? implode("\n", $labels) : 'n/a';
    }

    private function formatStructuredClaimRelation(array $claim): string
    {
        $metric = trim((string) ($claim['metric'] ?? ''));
        if ($metric !== '') {
            return $metric;
        }

        $predicate = trim((string) ($claim['predicate'] ?? ''));
        return $predicate !== '' ? $predicate : 'n/a';
    }

    private function formatStructuredClaimValue(array $claim): string
    {
        $value = $claim['value'] ?? null;
        if (is_numeric($value)) {
            return number_format((float) $value, 6, '.', '');
        }

        $object = $this->stringifyBenchmarkFactField($claim['object'] ?? null);
        if ($object !== '') {
            return $object;
        }

        $orderedItems = is_array($claim['ordered_items'] ?? null) ? $claim['ordered_items'] : [];
        if (!empty($orderedItems)) {
            return $this->stringifyBenchmarkFactField($orderedItems);
        }

        if (is_numeric($claim['feature_count'] ?? null)) {
            return 'features=' . (int) $claim['feature_count'];
        }

        return 'n/a';
    }

    private function benchmarkStatusTone(string $status): string
    {
        return match ($status) {
            'supported' => 'success',
            'partially_supported' => 'warning',
            'contradicted' => 'danger',
            'unverifiable' => 'secondary',
            'no_claims' => 'dark',
            default => 'secondary',
        };
    }

    private function buildBenchmarkClaimComparisonRows(
        string $predictServiceInternalBase,
        string $routePrefix,
        array $leaderboardRows,
        array $manifestRows
    ): array {
        if ($routePrefix === '/' || empty($leaderboardRows) || empty($manifestRows)) {
            return [];
        }

        $manifestByArtifact = [];
        foreach ($manifestRows as $manifestRow) {
            if (!is_array($manifestRow)) {
                continue;
            }

            $artifactId = trim((string) ($manifestRow['artifact_id'] ?? ''));
            if ($artifactId === '') {
                continue;
            }

            $manifestByArtifact[$artifactId] = $manifestRow;
        }

        if (empty($manifestByArtifact)) {
            return [];
        }

        $goldUrls = [];
        foreach (array_keys($manifestByArtifact) as $artifactId) {
            $goldUrls[$artifactId] = $this->buildReportAssetUrl(
                $predictServiceInternalBase,
                $routePrefix,
                'benchmark_eval/gold/' . $this->benchmarkGoldFileName($artifactId)
            );
        }

        $verificationRequestMeta = [];
        $verificationUrls = [];
        $extractedClaimUrls = [];
        $requestIndex = 0;
        foreach ($leaderboardRows as $leaderboardRow) {
            if (!is_array($leaderboardRow)) {
                continue;
            }

            $arm = trim((string) ($leaderboardRow['arm'] ?? ''));
            $condition = trim((string) ($leaderboardRow['input_condition'] ?? ''));
            $semanticLevel = trim((string) ($leaderboardRow['semantic_level'] ?? '')) ?: null;
            if ($arm === '' || $condition === '') {
                continue;
            }

            foreach (array_keys($manifestByArtifact) as $artifactId) {
                $requestKey = 'verification_' . $requestIndex++;
                $verificationRequestMeta[$requestKey] = [
                    'artifact_id' => $artifactId,
                    'arm' => $arm,
                    'input_condition' => $condition,
                    'semantic_level' => $semanticLevel,
                ];
                $baseFileName = $this->benchmarkGenerationFileName(
                    $artifactId,
                    $arm,
                    $condition,
                    $semanticLevel
                );
                $verificationUrls[$requestKey] = $this->buildReportAssetUrl(
                    $predictServiceInternalBase,
                    $routePrefix,
                    'benchmark_eval/verifications/' . $baseFileName
                );
                $extractedClaimUrls[$requestKey] = $this->buildReportAssetUrl(
                    $predictServiceInternalBase,
                    $routePrefix,
                    'benchmark_eval/extracted_claims/' . $baseFileName
                );
            }
        }

        $goldPayloads = $this->fetchJsonAssetMap($goldUrls);
        $verificationPayloads = $this->fetchJsonAssetMap($verificationUrls);
        $extractedClaimPayloads = $this->fetchJsonAssetMap($extractedClaimUrls);

        $goldFactsByArtifact = [];
        foreach ($manifestByArtifact as $artifactId => $manifestRow) {
            $goldPayload = is_array($goldPayloads[$artifactId] ?? null) ? $goldPayloads[$artifactId] : [];
            $facts = is_array($goldPayload['ground_truth_facts'] ?? null) ? $goldPayload['ground_truth_facts'] : [];
            $indexedFacts = [];
            foreach ($facts as $fact) {
                if (!is_array($fact)) {
                    continue;
                }
                $factId = trim((string) ($fact['fact_id'] ?? ''));
                if ($factId !== '') {
                    $indexedFacts[$factId] = $fact;
                }
            }
            $goldFactsByArtifact[$artifactId] = [
                'facts' => $facts,
                'by_id' => $indexedFacts,
            ];
        }

        $rows = [];
        foreach ($verificationRequestMeta as $requestKey => $meta) {
            $artifactId = $meta['artifact_id'];
            $manifestRow = $manifestByArtifact[$artifactId] ?? [];
            $artifactTitle = $this->benchmarkArtifactTitle($manifestRow);
            $artifactScope = trim((string) ($manifestRow['asset_family'] ?? $manifestRow['artifact_type'] ?? ''));
            $goldFacts = $goldFactsByArtifact[$artifactId]['facts'] ?? [];
            $goldFactIndex = $goldFactsByArtifact[$artifactId]['by_id'] ?? [];
            $verificationPayload = is_array($verificationPayloads[$requestKey] ?? null) ? $verificationPayloads[$requestKey] : [];
            $verifications = is_array($verificationPayload['verifications'] ?? null) ? $verificationPayload['verifications'] : [];
            $extractedClaimsPayload = is_array($extractedClaimPayloads[$requestKey] ?? null) ? $extractedClaimPayloads[$requestKey] : [];
            $claims = is_array($extractedClaimsPayload['claims'] ?? null) ? $extractedClaimsPayload['claims'] : [];
            $claimsById = [];
            foreach ($claims as $claim) {
                if (!is_array($claim)) {
                    continue;
                }
                $claimId = trim((string) ($claim['claim_id'] ?? ''));
                if ($claimId !== '') {
                    $claimsById[$claimId] = $claim;
                }
            }

            if (empty($verifications)) {
                $rows[] = [
                    'artifact_title' => $artifactTitle,
                    'artifact_scope' => $artifactScope !== '' ? $artifactScope : 'n/a',
                    'artifact_id' => $artifactId,
                    'arm' => $meta['arm'],
                    'input_condition' => $meta['input_condition'],
                    'semantic_level' => $meta['semantic_level'],
                    'status' => 'no_claims',
                    'status_tone' => $this->benchmarkStatusTone('no_claims'),
                    'claim_type' => 'n/a',
                    'claim_subject' => 'n/a',
                    'claim_relation' => 'n/a',
                    'claim_value' => 'n/a',
                    'gold_value' => 'n/a',
                    'reason' => 'No verification rows were written for this artifact/arm run.',
                    'numeric_delta' => null,
                ];
                continue;
            }

            foreach ($verifications as $verification) {
                if (!is_array($verification)) {
                    continue;
                }

                $matchedFacts = [];
                $matchedValues = [];
                foreach ((array) ($verification['matched_fact_ids'] ?? []) as $factId) {
                    $factId = trim((string) $factId);
                    if ($factId === '' || !isset($goldFactIndex[$factId])) {
                        continue;
                    }
                    $matchedFacts[] = $this->formatBenchmarkGoldFact($goldFactIndex[$factId]);
                    $matchedValues[] = $this->formatBenchmarkGoldValue($goldFactIndex[$factId]);
                }

                $status = trim((string) ($verification['status'] ?? '')) ?: 'n/a';
                $claimId = trim((string) ($verification['claim_id'] ?? ''));
                $claim = $claimId !== '' && isset($claimsById[$claimId]) ? $claimsById[$claimId] : [];
                $rows[] = [
                    'artifact_title' => $artifactTitle,
                    'artifact_scope' => $artifactScope !== '' ? $artifactScope : 'n/a',
                    'artifact_id' => $artifactId,
                    'arm' => $meta['arm'],
                    'input_condition' => $meta['input_condition'],
                    'semantic_level' => $meta['semantic_level'],
                    'status' => $status,
                    'status_tone' => $this->benchmarkStatusTone($status),
                    'claim_type' => trim((string) ($claim['claim_type'] ?? '')) ?: 'n/a',
                    'claim_subject' => trim((string) ($claim['subject'] ?? '')) ?: 'n/a',
                    'claim_relation' => $this->formatStructuredClaimRelation($claim),
                    'claim_value' => $this->formatStructuredClaimValue($claim),
                    'gold_value' => !empty($matchedValues) ? implode("\n", $matchedValues) : 'n/a',
                    'reason' => trim((string) ($verification['reason'] ?? '')) ?: 'n/a',
                    'numeric_delta' => is_numeric($verification['numeric_delta'] ?? null)
                        ? (float) $verification['numeric_delta']
                        : null,
                ];
            }
        }

        return $rows;
    }

    private function benchmarkAssetPayload(string $text): array
    {
        return [
            'en' => $text,
            'zh_TW' => '',
        ];
    }

    private function benchmarkOverviewPayload(array $assets): array
    {
        $selectedTexts = [];
        foreach (self::BENCHMARK_OVERVIEW_PRIORITY_KEYS as $key) {
            $asset = is_array($assets[$key] ?? null) ? $assets[$key] : [];
            $text = trim((string) ($asset['en'] ?? ''));
            if ($text === '' || in_array($text, $selectedTexts, true)) {
                continue;
            }

            $selectedTexts[] = $text;
            if (count($selectedTexts) >= 3) {
                break;
            }
        }

        return [
            'en' => !empty($selectedTexts) ? implode("\n\n", $selectedTexts) : '',
            'zh_TW' => '',
        ];
    }

    private function buildBenchmarkExplanationPayload(
        string $predictServiceInternalBase,
        string $routePrefix,
        array $reportAssets,
        array $row,
        string $selectionMethod
    ): ?array {
        $manifestAsset = is_array($reportAssets['benchmark_manifest'] ?? null) ? $reportAssets['benchmark_manifest'] : [];
        $runMetadataAsset = is_array($reportAssets['benchmark_run_metadata'] ?? null) ? $reportAssets['benchmark_run_metadata'] : [];
        $manifestUrl = (string) ($manifestAsset['internal_url'] ?? $manifestAsset['public_url'] ?? '');
        $runMetadataUrl = (string) ($runMetadataAsset['internal_url'] ?? $runMetadataAsset['public_url'] ?? '');
        $manifestText = $this->fetchReportTextAsset($manifestUrl);

        if (!is_string($manifestText) || trim($manifestText) === '') {
            return null;
        }

        $manifestRows = $this->parseJsonLines($manifestText);
        if (empty($manifestRows)) {
            return null;
        }

        $runMetadata = $this->fetchReportJsonAsset($runMetadataUrl) ?? [];
        $arm = trim((string) ($row['arm'] ?? ''));
        $condition = trim((string) ($row['input_condition'] ?? ''));
        $semanticLevel = trim((string) ($row['semantic_level'] ?? '')) ?: null;
        if ($arm === '' || $condition === '') {
            return null;
        }

        $assets = [];
        foreach ($manifestRows as $manifestRow) {
            if (!is_array($manifestRow)) {
                continue;
            }

            $artifactId = trim((string) ($manifestRow['artifact_id'] ?? ''));
            if ($artifactId === '') {
                continue;
            }

            $generationFilename = $this->benchmarkGenerationFileName(
                $artifactId,
                $arm,
                $condition,
                $semanticLevel
            );
            $generationUrl = $this->buildReportAssetUrl(
                $predictServiceInternalBase,
                $routePrefix,
                'benchmark_eval/generations/' . $generationFilename
            );
            $generation = $this->fetchReportJsonAsset($generationUrl);
            if (!is_array($generation)) {
                continue;
            }

            $text = trim((string) ($generation['explanation_full'] ?? $generation['explanation_short'] ?? ''));
            if ($text === '') {
                continue;
            }

            $assetKey = trim((string) ($manifestRow['asset_key'] ?? ''));
            if ($assetKey !== '' && !isset($assets[$assetKey])) {
                $assets[$assetKey] = $this->benchmarkAssetPayload($text);
            }

            $artifactType = trim((string) ($manifestRow['artifact_type'] ?? ''));
            foreach (self::BENCHMARK_CORE_ARTIFACT_ASSET_KEYS[$artifactType] ?? [] as $derivedKey) {
                if (!isset($assets[$derivedKey])) {
                    $assets[$derivedKey] = $this->benchmarkAssetPayload($text);
                }
            }
        }

        if (empty($assets)) {
            return null;
        }

        return [
            'provider' => 'benchmark_selected',
            'model' => $runMetadata['client_model'] ?? null,
            'generated_at' => $runMetadata['created_at'] ?? null,
            'selection_method' => $selectionMethod,
            'selected_arm' => $arm,
            'selected_condition' => $condition,
            'selected_semantic_level' => $semanticLevel,
            'selected_row' => $row,
            'overview' => $this->benchmarkOverviewPayload($assets),
            'assets' => $assets,
        ];
    }

    private function buildModelReportViewData(MLModel $model): array
    {
        $model->load(['dataset', 'trainer']);
        $routeName = (string) optional(request()->route())->getName();
        $routeNamespace = str_starts_with($routeName, 'user.') ? 'user' : 'admin';

        $predictServiceInternalBase = rtrim(
            config('services.predict_service.url', 'http://predict-service:5000'),
            '/'
        );
        $predictServiceBrowserBase = rtrim(
            (string) config('services.predict_service.browser_url', ''),
            '/'
        );
        $predictServicePublicBase = rtrim(
            config('services.predict_service.public_url', config('services.predict_service.url', 'http://localhost:5000')),
            '/'
        );

        $reportInfo = is_array($model->training_report) ? $model->training_report : [];

        if (empty($reportInfo['report_id'])) {
            $reportInfo['report_id'] = $this->sanitizeReportId((string) $model->MLMName);
        }

        if (empty($reportInfo['route_prefix']) && !empty($reportInfo['report_id'])) {
            $reportInfo['route_prefix'] = '/train/reports/' . $reportInfo['report_id'];
        }

        $summary = [];
        $summaryError = null;
        $routePrefix = '/' . ltrim((string) ($reportInfo['route_prefix'] ?? ''), '/');
        $summaryPublicUrl = null;

        if (!empty($routePrefix) && $routePrefix !== '/') {
            $summaryUrl = $predictServiceInternalBase . $routePrefix . '/summary.json';
            $summaryPublicUrl = $this->buildReportAssetUrl($predictServiceBrowserBase, $routePrefix, 'summary.json');
            try {
                $summaryResponse = Http::timeout(15)->acceptJson()->get($summaryUrl);
                if ($summaryResponse->successful()) {
                    $payload = $summaryResponse->json();
                    $summary = is_array($payload) ? $payload : [];
                } else {
                    $summaryError = 'Could not load summary.json from report storage.';
                }
            } catch (\Throwable $e) {
                $summaryError = 'Could not connect to predict-service to load report data.';
            }
        } else {
            $summaryError = 'No training report metadata found for this model.';
        }

        $files = [];
        if (is_array($summary['files'] ?? null)) {
            $files = $summary['files'];
        } elseif (is_array($reportInfo['files'] ?? null)) {
            $files = $reportInfo['files'];
        }

        $reportAssets = [];
        foreach ($files as $key => $filename) {
            if (!is_string($filename) || trim($filename) === '') {
                continue;
            }

            $reportAssets[$key] = [
                'filename' => $filename,
                'url' => $this->buildReportAssetUrl('', $routePrefix, $filename),
                'public_url' => $this->buildReportAssetUrl($predictServicePublicBase, $routePrefix, $filename),
                'internal_url' => $this->buildReportAssetUrl($predictServiceInternalBase, $routePrefix, $filename),
            ];
        }

        $shouldExposeConventionalBenchmarkAssets = !empty($summary['benchmark_summary'])
            || !empty($summary['benchmark_status'])
            || !empty($summary['selected_benchmark_explanations']);

        if ($shouldExposeConventionalBenchmarkAssets) {
            $conventionalBenchmarkFiles = [
                'benchmark_manifest' => 'benchmark_eval/manifest.jsonl',
                'benchmark_run_metadata' => 'benchmark_eval/run_metadata.json',
                'benchmark_leaderboard_json' => 'benchmark_eval/scores/leaderboard.json',
                'benchmark_leaderboard_csv' => 'benchmark_eval/scores/leaderboard.csv',
                'benchmark_per_chart_json' => 'benchmark_eval/scores/per_chart_benchmark.json',
                'benchmark_per_chart_csv' => 'benchmark_eval/scores/per_chart_benchmark.csv',
                'benchmark_selected_explanations' => 'benchmark_eval/selected_explanations.json',
            ];

            foreach ($conventionalBenchmarkFiles as $key => $filename) {
                if (isset($reportAssets[$key])) {
                    continue;
                }

                $reportAssets[$key] = [
                    'filename' => $filename,
                    'url' => $this->buildReportAssetUrl('', $routePrefix, $filename),
                    'public_url' => $this->buildReportAssetUrl($predictServicePublicBase, $routePrefix, $filename),
                    'internal_url' => $this->buildReportAssetUrl($predictServiceInternalBase, $routePrefix, $filename),
                ];
            }
        }

        $benchmarkStatusPayload = is_array($summary['benchmark_status'] ?? null)
            ? $summary['benchmark_status']
            : [];
        $benchmarkStatus = strtolower(trim((string) ($benchmarkStatusPayload['status'] ?? '')));
        $selectedBenchmarkExplanations = is_array($summary['selected_benchmark_explanations'] ?? null)
            ? $summary['selected_benchmark_explanations']
            : [];
        $benchmarkSummary = is_array($summary['benchmark_summary'] ?? null)
            ? $summary['benchmark_summary']
            : [];
        $benchmarkLeaderboardAsset = is_array($reportAssets['benchmark_leaderboard_json'] ?? null)
            ? $reportAssets['benchmark_leaderboard_json']
            : [];
        $benchmarkLeaderboardPayload = $this->fetchReportJsonAsset(
            (string) ($benchmarkLeaderboardAsset['internal_url'] ?? $benchmarkLeaderboardAsset['public_url'] ?? '')
        ) ?? [];
        $benchmarkSelectableRows = $this->normalizeSelectableBenchmarkRows(
            is_array($benchmarkLeaderboardPayload['leaderboard'] ?? null)
                ? $benchmarkLeaderboardPayload['leaderboard']
                : []
        );
        $defaultBenchmarkDisplayRow = $this->resolveDefaultBenchmarkDisplayRow(
            $benchmarkSelectableRows,
            $selectedBenchmarkExplanations,
            $benchmarkSummary
        );
        $requestedBenchmarkRowKey = trim((string) request()->query('benchmark_row', ''));
        $requestedBenchmarkDisplayRow = $this->findBenchmarkRowByKey($benchmarkSelectableRows, $requestedBenchmarkRowKey);
        $displayedBenchmarkRow = $requestedBenchmarkDisplayRow ?? $defaultBenchmarkDisplayRow;
        $defaultBenchmarkRowKey = is_array($defaultBenchmarkDisplayRow)
            ? $this->benchmarkRowKey($defaultBenchmarkDisplayRow)
            : '';
        $displayedBenchmarkRowKey = is_array($displayedBenchmarkRow)
            ? $this->benchmarkRowKey($displayedBenchmarkRow)
            : '';
        $benchmarkDisplayOverrideActive = $requestedBenchmarkRowKey !== ''
            && $requestedBenchmarkDisplayRow !== null
            && $displayedBenchmarkRowKey !== ''
            && $displayedBenchmarkRowKey !== $defaultBenchmarkRowKey;

        if ($benchmarkStatus === 'success') {
            if (
                !$benchmarkDisplayOverrideActive
                && !empty($selectedBenchmarkExplanations)
            ) {
                $llmExplanations = $selectedBenchmarkExplanations;
            } elseif (is_array($displayedBenchmarkRow)) {
                $llmExplanations = $this->buildBenchmarkExplanationPayload(
                    $predictServiceInternalBase,
                    $routePrefix,
                    $reportAssets,
                    $displayedBenchmarkRow,
                    $benchmarkDisplayOverrideActive ? 'manual_report_view_selection' : 'best_leaderboard_row'
                ) ?? $selectedBenchmarkExplanations;
            } else {
                $llmExplanations = $selectedBenchmarkExplanations;
            }
        } else {
            $llmExplanations = [];
        }

        $inlineTableKeys = [
            'model_comparison_table',
            'feature_importance_table',
            'best_model_shap_importance',
            'table1_incremental_results',
            'descriptive_statistics',
            'correlation_matrix',
        ];
        $inlineTables = [];
        foreach ($inlineTableKeys as $tableKey) {
            $tableUrl = $reportAssets[$tableKey]['internal_url']
                ?? $reportAssets[$tableKey]['public_url']
                ?? $reportAssets[$tableKey]['url']
                ?? null;

            if (empty($tableUrl)) {
                continue;
            }

            $tableData = $this->fetchReportCsvTable($tableUrl);
            if ($tableData !== null) {
                $inlineTables[$tableKey] = $tableData;
            }
        }

        $imageKeys = [
            'model_comparison_bars',
            'predicted_vs_actual',
            'residuals',
            'feature_importance',
            'correlation_heatmap',
            'feature_distributions',
            'feature_vs_target',
            'boxplots',
            'time_series',
            'gra_ranking',
        ];
        $tableKeys = [
            'summary',
            'analysis_summary',
            'model_comparison_table',
            'feature_importance_table',
            'descriptive_statistics',
            'correlation_matrix',
        ];

        return [
            'model' => $model,
            'routeNamespace' => $routeNamespace,
            'reportInfo' => $reportInfo,
            'summary' => $summary,
            'summaryPublicUrl' => $summaryPublicUrl,
            'summaryError' => $summaryError,
            'reportAssets' => $reportAssets,
            'llmExplanations' => $llmExplanations,
            'selectedBenchmarkExplanations' => $selectedBenchmarkExplanations,
            'benchmarkSelectableRows' => $benchmarkSelectableRows,
            'benchmarkDisplayedRow' => $displayedBenchmarkRow,
            'benchmarkDefaultDisplayRow' => $defaultBenchmarkDisplayRow,
            'benchmarkDisplayOverrideActive' => $benchmarkDisplayOverrideActive,
            'benchmarkDisplayedRowKey' => $displayedBenchmarkRowKey,
            'benchmarkStatusPayload' => $benchmarkStatusPayload,
            'inlineTables' => $inlineTables,
            'imageKeys' => $imageKeys,
            'tableKeys' => $tableKeys,
        ];
    }

    private function buildReportAssetUrl(string $baseUrl, string $routePrefix, string $filename): string
    {
        $baseUrl = rtrim($baseUrl, '/');
        $routePrefix = '/' . ltrim($routePrefix, '/');
        $segments = array_map('rawurlencode', explode('/', $filename));
        $encodedFilename = implode('/', $segments);

        return $baseUrl . $routePrefix . '/' . $encodedFilename;
    }
}
