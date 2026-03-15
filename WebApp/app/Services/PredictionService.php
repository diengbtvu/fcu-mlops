<?php

namespace App\Services;

use App\Models\Prediction;
use App\Models\User;
use App\Models\MLModel;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class PredictionService
{
    /**
     * Generate unique PredictionCode
     * 
     * @return string
     */
    public function generatePredictionCode(): string
    {
        do {
            // Generate random prediction code: PRED + timestamp + random
            $code = 'PRED' . date('Ymd') . '_' . mt_rand(100000, 999999);
            $exists = Prediction::where('PredictionCode', $code)->exists();
        } while ($exists);
        
        return $code;
    }

    /**
     * Make prediction using ML model
     * 
     * @param array $inputData
     * @param MLModel $model
     * @param User $user
     * @return array
     */
    public function makePrediction(array $inputData, MLModel $model, User $user): array
    {
        try {
            // Prepare prediction request — 11 biochemical features (Wang et al. 2024)
            $requestData = [
                'ph'                  => $inputData['ph'],
                'vss'                 => $inputData['vss'],
                'ethanol'             => $inputData['ethanol'],
                'acetate'             => $inputData['acetate'],
                'propionate'          => $inputData['propionate'],
                'butyrate'            => $inputData['butyrate'],
                'sucrose_degradation' => $inputData['sucrose_degradation'],
                'orp_mid'             => $inputData['orp_mid'],
                'orp_low'             => $inputData['orp_low'],
                'vfa'                 => $inputData['vfa'],
                'cod_o'               => $inputData['cod_o'],
                'model_path'          => $model->FilePath,
                'model_type'          => strtolower($model->LibType ?? 'sklearn'),
            ];

            // Make API call to prediction service
            $response = Http::timeout(30)->post(
                config('services.predict_service.url', 'http://predict-service:5000') . '/predict/model',
                $requestData
            );

            if (!$response->successful()) {
                throw new \Exception('Prediction API returned error: ' . $response->body());
            }

            $predictionResult = $response->json();

            // Validate response structure (Flask returns 'prediction' key)
            if (!isset($predictionResult['prediction'])) {
                throw new \Exception('Invalid prediction response format');
            }

            // Save prediction to database
            $prediction = $this->savePredictionResult(
                $inputData,
                $predictionResult,
                $model,
                $user
            );

            return [
                'success' => true,
                'data'    => [
                    'prediction'   => $prediction,
                    'hpr_value'    => $predictionResult['prediction'],  // L/h/L
                    'unit'         => $predictionResult['unit'] ?? 'L/h/L',
                    'model_info'   => [
                        'name' => $model->MLMName,
                        'type' => $model->LibType,
                        'id'   => $model->id,
                    ]
                ]
            ];

        } catch (\Exception $e) {
            Log::error('Prediction failed', [
                'error' => $e->getMessage(),
                'user_id' => $user->id,
                'model_id' => $model->id,
                'input_data' => $inputData
            ]);

            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }

    /**
     * Save prediction result to database
     * 
     * @param array $inputData
     * @param array $predictionResult
     * @param MLModel $model
     * @param User $user
     * @return Prediction
     */
    private function savePredictionResult(array $inputData, array $predictionResult, MLModel $model, User $user): Prediction
    {
        return Prediction::create([
            'user_id'             => $user->id,
            'ml_model_id'         => $model->id,
            // 11 hydrogen input features
            'pH'                  => $inputData['ph'],
            'VSS'                 => $inputData['vss'],
            'Ethanol'             => $inputData['ethanol'],
            'Acetate'             => $inputData['acetate'],
            'Propionate'          => $inputData['propionate'],
            'Butyrate'            => $inputData['butyrate'],
            'Sucrose_Degradation' => $inputData['sucrose_degradation'],
            'ORP_Mid'             => $inputData['orp_mid'],
            'ORP_Low'             => $inputData['orp_low'],
            'VFA'                 => $inputData['vfa'],
            'COD_O'               => $inputData['cod_o'],
            // Predicted output
            'HPR'                 => $predictionResult['prediction'],
        ]);
    }


    /**
     * Get user prediction history with pagination
     * 
     * @param User $user
     * @param int $perPage
     * @return \Illuminate\Pagination\LengthAwarePaginator
     */
    public function getUserPredictions(User $user, int $perPage = 10)
    {
        return Prediction::with(['user', 'mlModel'])
            ->where('user_id', $user->id)
            ->orderBy('created_at', 'desc')
            ->paginate($perPage);
    }

    /**
     * Get prediction statistics for user
     * 
     * @param User $user
     * @return array
     */
    public function getUserPredictionStats(User $user): array
    {
        $predictions = $user->predictions();

        $avgHpr = round($predictions->avg('HPR') ?? 0, 4);
        $maxHpr = round($predictions->max('HPR') ?? 0, 4);
        $minHpr = round($predictions->min('HPR') ?? 0, 4);

        return [
            'total_predictions' => $predictions->count(),
            'recent_predictions' => $predictions->where('created_at', '>=', now()->subDays(30))->count(),
            'avg_hpr' => $avgHpr,
            'max_hpr' => $maxHpr,
            'min_hpr' => $minHpr,
            'last_prediction' => $predictions->latest()->first()?->created_at,
        ];
    }

    /**
     * Delete prediction
     * 
     * @param Prediction $prediction
     * @param User $user
     * @return bool
     */
    public function deletePrediction(Prediction $prediction, User $user): bool
    {
        // Check if user owns this prediction or is admin
        if ($prediction->user_id !== $user->id && $user->role_id !== 1) {
            return false;
        }

        return $prediction->delete();
    }

    /**
     * Get popular input parameter ranges
     * 
     * @return array
     */
    public function getPopularParameterRanges(): array
    {
        return [
            'ph' => [
                'min' => Prediction::min('pH') ?? 0,
                'max' => Prediction::max('pH') ?? 0,
                'avg' => round(Prediction::avg('pH') ?? 0, 4),
            ],
            'vss' => [
                'min' => Prediction::min('VSS') ?? 0,
                'max' => Prediction::max('VSS') ?? 0,
                'avg' => round(Prediction::avg('VSS') ?? 0, 4),
            ],
            'ethanol' => [
                'min' => Prediction::min('Ethanol') ?? 0,
                'max' => Prediction::max('Ethanol') ?? 0,
                'avg' => round(Prediction::avg('Ethanol') ?? 0, 4),
            ],
            'acetate' => [
                'min' => Prediction::min('Acetate') ?? 0,
                'max' => Prediction::max('Acetate') ?? 0,
                'avg' => round(Prediction::avg('Acetate') ?? 0, 4),
            ],
            'propionate' => [
                'min' => Prediction::min('Propionate') ?? 0,
                'max' => Prediction::max('Propionate') ?? 0,
                'avg' => round(Prediction::avg('Propionate') ?? 0, 4),
            ],
            'butyrate' => [
                'min' => Prediction::min('Butyrate') ?? 0,
                'max' => Prediction::max('Butyrate') ?? 0,
                'avg' => round(Prediction::avg('Butyrate') ?? 0, 4),
            ],
            'sucrose_degradation' => [
                'min' => Prediction::min('Sucrose_Degradation') ?? 0,
                'max' => Prediction::max('Sucrose_Degradation') ?? 0,
                'avg' => round(Prediction::avg('Sucrose_Degradation') ?? 0, 4),
            ],
            'orp_mid' => [
                'min' => Prediction::min('ORP_Mid') ?? 0,
                'max' => Prediction::max('ORP_Mid') ?? 0,
                'avg' => round(Prediction::avg('ORP_Mid') ?? 0, 4),
            ],
            'orp_low' => [
                'min' => Prediction::min('ORP_Low') ?? 0,
                'max' => Prediction::max('ORP_Low') ?? 0,
                'avg' => round(Prediction::avg('ORP_Low') ?? 0, 4),
            ],
            'vfa' => [
                'min' => Prediction::min('VFA') ?? 0,
                'max' => Prediction::max('VFA') ?? 0,
                'avg' => round(Prediction::avg('VFA') ?? 0, 4),
            ],
            'cod_o' => [
                'min' => Prediction::min('COD_O') ?? 0,
                'max' => Prediction::max('COD_O') ?? 0,
                'avg' => round(Prediction::avg('COD_O') ?? 0, 4),
            ],
            'hpr' => [
                'min' => Prediction::min('HPR') ?? 0,
                'max' => Prediction::max('HPR') ?? 0,
                'avg' => round(Prediction::avg('HPR') ?? 0, 4),
            ],
        ];
    }
}
