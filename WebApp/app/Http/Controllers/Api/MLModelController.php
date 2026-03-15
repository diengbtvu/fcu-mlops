<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\MLModel;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Validator;
use Carbon\Carbon;

class MLModelController extends Controller
{
    /**
     * Display a listing of ML models
     */
    public function index(): JsonResponse
    {
        try {
            $models = MLModel::with(['dataset', 'trainedByUser'])
                           ->orderBy('CreatedDate', 'desc')
                           ->get();
            
            return response()->json([
                'success' => true,
                'data' => $models
            ], 200);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Failed to retrieve models',
                'error' => $e->getMessage()
            ], 500);
        }
    }

    /**
     * Store a newly created ML model in storage
     */
    public function store(Request $request): JsonResponse
    {
        try {
            // Validate request data
            $validator = Validator::make($request->all(), [
                'MLMName' => 'required|string|max:255',
                'FilePath' => 'required|string|max:500',
                'LibType' => 'required|string|max:50',
                'IsActive' => 'boolean',
                'MSEValue' => 'nullable|numeric',
                'MAEValue' => 'nullable|numeric',
                'R2Value' => 'nullable|numeric',
                'RMSEValue' => 'nullable|numeric',
                'mlflow_run_id' => 'nullable|string|max:255',  // FIXED: snake_case
                'mlflow_experiment_id' => 'nullable|string|max:255',  // FIXED: snake_case
                'gra_ranking' => 'nullable|array',
                'training_report' => 'nullable|array',
                'TrainedBy' => 'nullable|integer',
                'DatasetId' => 'nullable|integer'
            ]);

            if ($validator->fails()) {
                return response()->json([
                    'success' => false,
                    'message' => 'Validation failed',
                    'errors' => $validator->errors()
                ], 400);
            }

            // Create new model record
            $modelData = $request->only([
                'MLMName', 'FilePath', 'LibType', 'IsActive', 'MSEValue', 'MAEValue',
                'R2Value', 'RMSEValue',
                'mlflow_run_id', 'mlflow_experiment_id', 'gra_ranking', 'training_report',
                'TrainedBy', 'DatasetId'  // FIXED: snake_case
            ]);
            
            // Set default values
            $modelData['IsActive'] = $request->get('IsActive', true);
            $modelData['CreatedDate'] = Carbon::now();
            $modelData['UpdatedDate'] = Carbon::now();

            $model = MLModel::create($modelData);

            // Load relationships only if needed - avoid N+1 queries
            // For API creation, we can return minimal data for faster response
            return response()->json([
                'success' => true,
                'message' => 'Model created successfully',
                'data' => $model  // Return without eager loading for speed
            ], 201);

        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Failed to create model',
                'error' => $e->getMessage()
            ], 500);
        }
    }

    /**
     * Display the specified ML model
     */
    public function show($id): JsonResponse
    {
        try {
            $model = MLModel::with(['dataset', 'trainedByUser', 'predictions'])->findOrFail($id);
            
            return response()->json([
                'success' => true,
                'data' => $model
            ], 200);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Model not found',
                'error' => $e->getMessage()
            ], 404);
        }
    }

    /**
     * Update the specified ML model in storage
     */
    public function update(Request $request, $id): JsonResponse
    {
        try {
            $model = MLModel::findOrFail($id);
            
            // Validate request data
            $validator = Validator::make($request->all(), [
                'MLMName' => 'string|max:255',
                'FilePath' => 'string|max:500',
                'LibType' => 'string|max:50',
                'IsActive' => 'boolean',
                'MSEValue' => 'nullable|numeric',
                'MAEValue' => 'nullable|numeric',
                'R2Value' => 'nullable|numeric',
                'RMSEValue' => 'nullable|numeric',
                'MlflowRunId' => 'nullable|string|max:255',
                'ZenmlPipelineId' => 'nullable|string|max:255',
                'gra_ranking' => 'nullable|array',
                'training_report' => 'nullable|array',
                'TrainedBy' => 'nullable|integer',
                'DatasetId' => 'nullable|integer'
            ]);

            if ($validator->fails()) {
                return response()->json([
                    'success' => false,
                    'message' => 'Validation failed',
                    'errors' => $validator->errors()
                ], 400);
            }

            // If setting this model as active, deactivate others
            if ($request->has('IsActive') && $request->get('IsActive')) {
                MLModel::where('id', '!=', $id)->update(['IsActive' => false]);
            }

            // Update model
            $updateData = $request->only([
                'MLMName', 'FilePath', 'LibType', 'IsActive', 'MSEValue', 'MAEValue',
                'R2Value', 'RMSEValue',
                'MlflowRunId', 'ZenmlPipelineId', 'gra_ranking', 'training_report',
                'TrainedBy', 'DatasetId'
            ]);
            $updateData['UpdatedDate'] = Carbon::now();

            $model->update($updateData);

            return response()->json([
                'success' => true,
                'message' => 'Model updated successfully',
                'data' => $model->load(['dataset', 'trainedByUser'])
            ], 200);

        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Failed to update model',
                'error' => $e->getMessage()
            ], 500);
        }
    }

    /**
     * Remove the specified ML model from storage
     */
    public function destroy($id): JsonResponse
    {
        try {
            $model = MLModel::findOrFail($id);
            
            // Check if model has predictions
            $predictionsCount = $model->predictions()->count();
            if ($predictionsCount > 0) {
                return response()->json([
                    'success' => false,
                    'message' => "Cannot delete model with {$predictionsCount} existing predictions"
                ], 400);
            }
            
            $model->delete();
            
            return response()->json([
                'success' => true,
                'message' => 'Model deleted successfully'
            ], 200);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Failed to delete model',
                'error' => $e->getMessage()
            ], 500);
        }
    }

    /**
     * Get the currently active model
     */
    public function getActiveModel(): JsonResponse
    {
        try {
            $activeModel = MLModel::active()
                                ->with(['dataset', 'trainedByUser'])
                                ->first();
            
            if (!$activeModel) {
                return response()->json([
                    'success' => false,
                    'message' => 'No active model found'
                ], 404);
            }
            
            return response()->json([
                'success' => true,
                'data' => $activeModel
            ], 200);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Failed to retrieve active model',
                'error' => $e->getMessage()
            ], 500);
        }
    }

    /**
     * Activate a specific model (and deactivate others)
     */
    public function activate($id): JsonResponse
    {
        try {
            $model = MLModel::findOrFail($id);
            
            // Deactivate all other models
            MLModel::where('id', '!=', $id)->update(['IsActive' => false]);
            
            // Activate the selected model
            $model->update([
                'IsActive' => true,
                'UpdatedDate' => Carbon::now()
            ]);
            
            return response()->json([
                'success' => true,
                'message' => 'Model activated successfully',
                'data' => $model
            ], 200);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => 'Failed to activate model',
                'error' => $e->getMessage()
            ], 500);
        }
    }
}
