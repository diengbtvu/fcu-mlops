<?php

namespace App\Http\Controllers\User;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;
use Firebase\JWT\JWT;
use App\Models\User;
use App\Models\MLModel;
use App\Models\Prediction;

class UserController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth');
        $this->middleware('user');
    }

    public function dashboard()
    {
        $user = Auth::user();
        $totalPredictions = Prediction::where('user_id', $user->id)->count();
        $recentPredictions = Prediction::with('mlModel')
            ->where('user_id', $user->id)
            ->orderBy('created_at', 'desc')
            ->limit(5)
            ->get();
        
        return view('user.dashboard', compact('totalPredictions', 'recentPredictions'));
    }

    public function predict()
    {
        // Get available active models for user selection
        $models = MLModel::where('IsActive', true)->get();
        return view('user.predict', compact('models'));
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

            // 🆕 STRATEGY: Check if model has MLflow tracking
            if (!empty($selectedModel->mlflow_run_id)) {
                // ✅ Use MLflow prediction endpoint (NEW - with cache)
                return $this->predictWithMLflow($selectedModel, $request, $apiUrl, $token);
            } else {
                // ✅ Use traditional file-based prediction (OLD)
                return $this->predictWithFileModel($selectedModel, $request, $apiUrl, $token);
            }

        } catch (\Exception $e) {
            \Log::error('Exception in makePrediction (User)', [
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
        \Log::info('Using MLflow prediction (User)', [
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
            
            \Log::error('MLflow prediction failed (User)', [
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

        \Log::info('Using file-based prediction (User)', [
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
            
            \Log::error('File-based prediction failed (User)', [
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
        
        return view('user.history', compact('predictions'));
    }

    public function profile()
    {
        $user = Auth::user();
        return view('user.profile', compact('user'));
    }

    public function updateProfile(Request $request)
    {
        $user = Auth::user();
        
        $request->validate([
            'FullName' => 'required|string|max:255',
            'Gender' => 'required|in:Male,Female',
            'BirthDate' => 'required|date',
            'Address' => 'required|string|max:255',
            'Username' => 'required|string|max:255|unique:users,Username,' . $user->id,
        ]);

        $user->update([
            'FullName' => $request->FullName,
            'Gender' => $request->Gender,
            'BirthDate' => $request->BirthDate,
            'Address' => $request->Address,
            'Username' => $request->Username,
        ]);

        return redirect()->route('user.profile')->with('success', 'Profile updated successfully.');
    }

    public function security()
    {
        return view('user.security');
    }

    public function changePassword(Request $request)
    {
        $request->validate([
            'current_password' => 'required',
            'new_password' => 'required|string|min:6|confirmed',
        ]);

        $user = Auth::user();

        if (!Hash::check($request->current_password, $user->Password)) {
            return back()->withErrors(['current_password' => 'Current password is incorrect.']);
        }

        $user->update([
            'Password' => Hash::make($request->new_password)
        ]);

        return redirect()->route('user.security')->with('success', 'Password changed successfully.');
    }

    private function predictionFeatureValidationRules(): array
    {
        return [
            'ph' => 'required|numeric|min:3|max:8',
            'vss' => 'required|numeric|min:0|max:10000',
            'ethanol' => 'required|numeric|min:0|max:100',
            'acetate' => 'required|numeric|min:0|max:200',
            'propionate' => 'required|numeric|min:0|max:100',
            'butyrate' => 'required|numeric|min:0|max:200',
            'sucrose_degradation' => 'required|numeric|min:0|max:100',
            'orp_mid' => 'required|numeric|min:-500|max:100',
            'orp_low' => 'required|numeric|min:-500|max:100',
            'vfa' => 'required|numeric|min:0|max:500',
            'cod_o' => 'required|numeric|min:0|max:50000',
        ];
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

    // Dataset Management for Users
    public function datasets()
    {
        // Reuse DatasetController logic but through user routes
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->index();
    }

    public function showDataset($id)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->show($id);
    }

    public function createDataset()
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->create();
    }

    public function storeDataset(Request $request)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->store($request);
    }

    public function destroyDataset($id)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->destroy($id);
    }

    public function showTrainForm($id)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->showTrainForm($id);
    }

    public function trainDataset(Request $request, $id)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->train($request, $id);
    }

    public function showAugmentForm($id)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->showAugmentForm($id);
    }

    public function augmentDataset(Request $request, $id)
    {
        $controller = app(\App\Http\Controllers\DatasetController::class);
        return $controller->augment($request, $id);
    }

    // Model Management for Users
    public function models()
    {
        // Reuse AdminController logic but through user routes
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->models();
    }

    public function createModel()
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->createModel();
    }

    public function storeModel(Request $request)
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->storeModel($request);
    }

    public function showModelReport(MLModel $model)
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->showModelReport($model);
    }

    public function editModel($model)
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->editModel($model);
    }

    public function updateModel(Request $request, $model)
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->updateModel($request, $model);
    }

    public function deleteModel($model)
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->deleteModel($model);
    }

    public function testModel($model)
    {
        $controller = app(\App\Http\Controllers\Admin\AdminController::class);
        return $controller->testModel($model);
    }
}
