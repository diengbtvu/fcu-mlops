<?php

namespace App\Http\Controllers;

use App\Models\MLModel;
use Illuminate\Http\Request;

class ModelComparisonController extends Controller
{
    /**
     * Hiển thị trang chọn models để so sánh
     */
    public function index()
    {
        $models = MLModel::with('dataset', 'trainer')
            ->orderBy('CreatedDate', 'desc')
            ->get();
        
        return view('admin.models.compare.index', compact('models'));
    }

    /**
     * So sánh 2 models
     */
    public function compare(Request $request)
    {
        $request->validate([
            'model1_id' => 'required|exists:ml_models,id',
            'model2_id' => 'required|exists:ml_models,id|different:model1_id',
        ]);

        $model1 = MLModel::with('dataset', 'trainer')->findOrFail($request->model1_id);
        $model2 = MLModel::with('dataset', 'trainer')->findOrFail($request->model2_id);

        // Calculate comparison metrics
        $comparison = $this->calculateComparison($model1, $model2);

        return view('admin.models.compare.result', compact('model1', 'model2', 'comparison'));
    }

    /**
     * Calculate comparison between two models
     */
    private function calculateComparison($model1, $model2)
    {
        $metrics = ['MSE', 'MAE', 'RMSE', 'R2'];
        $comparison = [
            'metrics' => [],
            'winner' => null,
            'score' => [
                'model1' => 0,
                'model2' => 0,
            ],
        ];

        foreach ($metrics as $metric) {
            // Get raw database values
            $value1 = $this->getMetricValue($model1, $metric);
            $value2 = $this->getMetricValue($model2, $metric);

            $comparison['metrics'][$metric] = [
                'model1' => $value1,
                'model2' => $value2,
                'difference' => abs($value1 - $value2),
                'percentage' => $value2 != 0 ? (($value1 - $value2) / $value2) * 100 : 0,
            ];

            // Determine winner for this metric
            // For MSE, MAE, RMSE: lower is better
            // For R2: higher is better
            if ($metric === 'R2') {
                if ($value1 > $value2) {
                    $comparison['metrics'][$metric]['winner'] = 'model1';
                    $comparison['score']['model1']++;
                } elseif ($value2 > $value1) {
                    $comparison['metrics'][$metric]['winner'] = 'model2';
                    $comparison['score']['model2']++;
                } else {
                    $comparison['metrics'][$metric]['winner'] = 'tie';
                }
            } else {
                // Lower is better for error metrics
                if ($value1 < $value2) {
                    $comparison['metrics'][$metric]['winner'] = 'model1';
                    $comparison['score']['model1']++;
                } elseif ($value2 < $value1) {
                    $comparison['metrics'][$metric]['winner'] = 'model2';
                    $comparison['score']['model2']++;
                } else {
                    $comparison['metrics'][$metric]['winner'] = 'tie';
                }
            }
        }

        // Determine overall winner
        if ($comparison['score']['model1'] > $comparison['score']['model2']) {
            $comparison['winner'] = 'model1';
        } elseif ($comparison['score']['model2'] > $comparison['score']['model1']) {
            $comparison['winner'] = 'model2';
        } else {
            $comparison['winner'] = 'tie';
        }

        return $comparison;
    }

    /**
     * Get metric value from model, handling null values
     */
    private function getMetricValue($model, $metric)
    {
        $columnMap = [
            'MSE' => 'MSEValue',
            'MAE' => 'MAEValue',
            'RMSE' => 'RMSEValue',
            'R2' => 'R2Value',
        ];

        $column = $columnMap[$metric] ?? null;
        if (!$column) {
            return 0;
        }

        $value = $model->$column;
        
        // If value is null, try to calculate RMSE from MSE
        if ($value === null && $metric === 'RMSE' && $model->MSEValue !== null) {
            return sqrt($model->MSEValue);
        }

        return $value ?? 0;
    }

    /**
     * Get comparison data as JSON for AJAX requests
     */
    public function getComparisonData(Request $request)
    {
        $request->validate([
            'model1_id' => 'required|exists:ml_models,id',
            'model2_id' => 'required|exists:ml_models,id|different:model1_id',
        ]);

        $model1 = MLModel::with('dataset')->findOrFail($request->model1_id);
        $model2 = MLModel::with('dataset')->findOrFail($request->model2_id);

        $comparison = $this->calculateComparison($model1, $model2);

        return response()->json([
            'success' => true,
            'model1' => [
                'id' => $model1->id,
                'name' => $model1->ModelName,
                'type' => $model1->LibraryType,
                'mse' => $model1->MSE,
                'mae' => $model1->MAE,
                'rmse' => $model1->RMSE,
                'r2' => $model1->R2,
            ],
            'model2' => [
                'id' => $model2->id,
                'name' => $model2->ModelName,
                'type' => $model2->LibraryType,
                'mse' => $model2->MSE,
                'mae' => $model2->MAE,
                'rmse' => $model2->RMSE,
                'r2' => $model2->R2,
            ],
            'comparison' => $comparison,
        ]);
    }
}
