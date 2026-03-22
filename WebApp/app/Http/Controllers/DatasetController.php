<?php

namespace App\Http\Controllers;

use App\Models\Dataset;
use App\Models\MLModel;
use App\Services\TrainingService;
use App\Services\DataAugmentationService;
use App\Mail\TrainingCompletedMail;
use App\Models\EmailSetting;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Config;
use Illuminate\Support\Facades\Http;
use Illuminate\Validation\ValidationException;
use Illuminate\Http\UploadedFile;

class DatasetController extends Controller
{
    private function routePrefix(): string
    {
        return Auth::user()?->role_id === 1 ? 'admin' : 'user';
    }

    private function inspectDatasetContents(
        string $realPath,
        string $originalFilename,
        ?string $selectedSheet,
        int $previewRows = 10
    ): array
    {
        $apiUrl = rtrim(
            (string) config('services.predict_service.url', 'http://predict-service:5000'),
            '/'
        ) . '/train/inspect';

        if (!is_file($realPath)) {
            throw new \RuntimeException('Dataset file not found on disk.');
        }

        $payload = [
            'preview_rows' => max(1, min($previewRows, 20)),
        ];
        if ($selectedSheet !== null && $selectedSheet !== '') {
            $payload['sheet_name'] = $selectedSheet;
        }

        $response = Http::timeout(120)
            ->attach(
                'dataset_file',
                file_get_contents($realPath),
                $originalFilename
            )
            ->post($apiUrl, $payload);

        $inspection = $response->json();

        if (!$response->successful()) {
            $message = is_array($inspection)
                ? ($inspection['error'] ?? 'Unable to inspect the dataset file.')
                : 'Unable to inspect the dataset file.';
            throw new \RuntimeException($message);
        }

        if (!is_array($inspection) || !($inspection['success'] ?? false)) {
            throw new \RuntimeException(
                is_array($inspection)
                    ? ($inspection['error'] ?? 'Unable to inspect the dataset file.')
                    : 'Unable to inspect the dataset file.'
            );
        }

        return $inspection;
    }

    private function buildReportAssetUrl(string $baseUrl, string $routePrefix, string $filename): string
    {
        $baseUrl = rtrim($baseUrl, '/');
        $routePrefix = '/' . ltrim($routePrefix, '/');
        $segments = array_map('rawurlencode', explode('/', $filename));
        $encodedFilename = implode('/', $segments);

        return $baseUrl . $routePrefix . '/' . $encodedFilename;
    }

    private function resolveTrainingBundleUrl(?MLModel $model): ?string
    {
        if (!$model instanceof MLModel) {
            return null;
        }

        $reportInfo = is_array($model->training_report) ? $model->training_report : [];
        $bundleFilename = $reportInfo['files']['training_bundle_zip'] ?? null;
        $routePrefix = (string) ($reportInfo['route_prefix'] ?? '');

        if (!is_string($bundleFilename) || trim($bundleFilename) === '' || trim($routePrefix) === '') {
            return null;
        }

        $predictServicePublicBase = rtrim(
            (string) config(
                'services.predict_service.public_url',
                config('services.predict_service.url', 'http://localhost:5000')
            ),
            '/'
        );

        return $this->buildReportAssetUrl(
            $predictServicePublicBase,
            $routePrefix,
            $bundleFilename
        );
    }

    private function inspectDatasetUpload(UploadedFile $uploadedFile, ?string $selectedSheet): array
    {
        try {
            return $this->inspectDatasetContents(
                $uploadedFile->getRealPath(),
                $uploadedFile->getClientOriginalName(),
                $selectedSheet,
                10
            );
        } catch (\RuntimeException $exception) {
            throw ValidationException::withMessages([
                'dataset_file' => $exception->getMessage(),
            ]);
        }
    }

    /**
     * Apply email settings from database to config
     */
    private function applyEmailConfig()
    {
        $settings = EmailSetting::getAllAsArray();

        if (isset($settings['smtp_host'])) {
            Config::set('mail.mailers.smtp.host', $settings['smtp_host']);
        }
        if (isset($settings['smtp_port'])) {
            Config::set('mail.mailers.smtp.port', $settings['smtp_port']);
        }
        if (isset($settings['smtp_username'])) {
            Config::set('mail.mailers.smtp.username', $settings['smtp_username']);
        }
        if (isset($settings['smtp_password'])) {
            Config::set('mail.mailers.smtp.password', $settings['smtp_password']);
        }
        if (isset($settings['smtp_encryption'])) {
            Config::set('mail.mailers.smtp.encryption', $settings['smtp_encryption']);
        }
        if (isset($settings['mail_from_address'])) {
            Config::set('mail.from.address', $settings['mail_from_address']);
        }
        if (isset($settings['mail_from_name'])) {
            Config::set('mail.from.name', $settings['mail_from_name']);
        }
    }

    /**
     * Hiển thị danh sách dataset.
     */
    public function index()
    {
        $datasets = Dataset::with([
            'user',
            'mlModels' => function ($query) {
                $query->orderByDesc('CreatedDate')->orderByDesc('id');
            },
        ])->orderByDesc('UploadDate')->get();

        $trainingBundleUrls = [];
        foreach ($datasets as $dataset) {
            $trainingBundleUrls[$dataset->DatasetId] = $this->resolveTrainingBundleUrl(
                $dataset->mlModels->first()
            );
        }

        return view('admin.datasets.index', compact('datasets', 'trainingBundleUrls'));
    }

    /**
     * Hiển thị form upload dataset mới.
     */
    public function create()
    {
        return view('admin.datasets.create');
    }

    /**
     * Lưu dataset mới vào cơ sở dữ liệu.
     */
    public function store(Request $request)
    {
        $request->validate([
            'DatasetName' => 'required|string|max:255',
            'Description' => 'nullable|string',
            'dataset_file' => 'required|file|mimes:csv,xls,xlsx|max:10240',
            'selected_sheet' => 'nullable|string|max:255',
        ]);

        $uploadedFile = $request->file('dataset_file');
        $selectedSheet = $request->input('selected_sheet');
        $inspection = $this->inspectDatasetUpload($uploadedFile, $selectedSheet);

        if (($inspection['requires_sheet_selection'] ?? false) && blank($selectedSheet)) {
            throw ValidationException::withMessages([
                'selected_sheet' => 'Please select a sheet before uploading this workbook.',
            ]);
        }

        if (!($inspection['is_valid'] ?? false)) {
            $message = $inspection['validation_error']
                ?? 'The selected sheet is not valid for training.';

            if (!empty($inspection['missing_columns'] ?? [])) {
                $message = 'Missing required columns: ' . implode(', ', $inspection['missing_columns']);
            }

            throw ValidationException::withMessages([
                'dataset_file' => $message,
            ]);
        }

        $resolvedSelectedSheet = $inspection['selected_sheet'] ?? null;

        // Lưu file vào storage/app/datasets
        $path = $uploadedFile->store('datasets', 'public');

        // Lưu thông tin vào DB
        Dataset::create([
            'DatasetName' => $request->DatasetName,
            'FilePath' => $path,
            'SelectedSheet' => $resolvedSelectedSheet,
            'Description' => $request->Description,
            'UploadedBy' => Auth::id(), // user đang đăng nhập
        ]);

        return redirect()->route($this->routePrefix() . '.datasets.index')
            ->with('success', 'Dataset uploaded successfully!');
    }

    /**
     * Hiển thị chi tiết dataset.
     */
    public function show($id)
    {
        $dataset = Dataset::with([
            'user',
            'mlModels' => function ($query) {
                $query->orderByDesc('CreatedDate')->orderByDesc('id');
            },
        ])->findOrFail($id);
        $preview = null;
        $previewError = null;
        $storagePath = storage_path('app/public/' . $dataset->FilePath);
        $latestTrainedModel = $dataset->mlModels->first();
        $trainingBundleUrl = $this->resolveTrainingBundleUrl($latestTrainedModel);

        if (!is_file($storagePath)) {
            $previewError = 'Dataset file not found on disk.';
        } else {
            try {
                $preview = $this->inspectDatasetContents(
                    $storagePath,
                    basename($dataset->FilePath),
                    $dataset->SelectedSheet,
                    20
                );
            } catch (\Throwable $exception) {
                Log::warning('Failed to inspect stored dataset preview', [
                    'dataset_id' => $dataset->DatasetId,
                    'file_path' => $dataset->FilePath,
                    'selected_sheet' => $dataset->SelectedSheet,
                    'error' => $exception->getMessage(),
                ]);
                $previewError = $exception->getMessage();
            }
        }

        return view('admin.datasets.show', compact(
            'dataset',
            'preview',
            'previewError',
            'latestTrainedModel',
            'trainingBundleUrl'
        ));
    }

    /**
     * Xóa dataset.
     */
    public function destroy($id)
    {
        $dataset = Dataset::findOrFail($id);

        // Xóa file vật lý nếu có
        if (Storage::exists($dataset->FilePath)) {
            Storage::delete($dataset->FilePath);
        }

        $dataset->delete();

        return redirect()->route($this->routePrefix() . '.datasets.index')
            ->with('success', 'Dataset deleted successfully.');
    }

    /**
     * Hiển thị form training configuration
     */
    public function showTrainForm($id)
    {
        $dataset = Dataset::with('user')->findOrFail($id);
        return view('admin.datasets.train', compact('dataset'));
    }

    /**
     * Train model với dataset được chọn
     */
    public function train(Request $request, $id)
    {
        $dataset = Dataset::findOrFail($id);
        $user = Auth::user();

        // Validate training parameters
        $request->validate([
            'model_type' => 'required|in:random_forest,xgboost,svm,knn,decision_tree,dt',
            'training_method' => 'nullable|in:process,api',
            'training_scope' => 'nullable|in:single_model,all_models_compare',
            'model_name' => 'nullable|string|max:255',
            'session_id' => 'nullable|string', // Session ID for progress tracking
            // Tree-based model parameters (RF, XGBoost, DT)
            'n_estimators' => 'nullable|integer|min:10|max:1000',
            'max_depth' => 'nullable|integer|min:1|max:50',
            'learning_rate' => 'nullable|numeric|min:0.001|max:1',
            // SVM parameters
            'C' => 'nullable|numeric|min:0.0001|max:1000',
            'gamma' => 'nullable|string|max:50',
            'kernel' => 'nullable|in:rbf,linear,poly,sigmoid',
            // KNN parameters
            'n_neighbors' => 'nullable|integer|min:1|max:100',
            // Common parameters
            'test_size' => 'nullable|integer|min:10|max:50',
            'random_state' => 'nullable|integer|min:0',
        ]);

        // Prepare training options based on model type
        $modelType = $request->input('model_type', 'random_forest');
        
        $options = [
            'model_type' => $modelType,
            'training_scope' => $request->input('training_scope', 'all_models_compare'),
            'model_name' => $request->input('model_name'),
            'test_size' => $request->input('test_size', 20) / 100,
            'random_state' => $request->input('random_state', 42),
            'session_id' => $request->input('session_id'), // Pass session ID
            'selected_sheet' => $dataset->SelectedSheet,
        ];

        // Add model-specific parameters
        if ($modelType === 'random_forest' || $modelType === 'xgboost') {
            $options['n_estimators'] = $request->input('n_estimators', 100);
            $options['max_depth'] = $request->input('max_depth');
            
            if ($modelType === 'xgboost') {
                $options['learning_rate'] = $request->input('learning_rate', 0.1);
            }
        } elseif ($modelType === 'decision_tree' || $modelType === 'dt') {
            $options['max_depth'] = $request->input('max_depth');
        } elseif ($modelType === 'svm') {
            $options['C'] = $request->input('C', 1.0);
            $options['gamma'] = $request->input('gamma', 'scale');
            $options['kernel'] = $request->input('kernel', 'rbf');
        } elseif ($modelType === 'knn') {
            $options['n_neighbors'] = $request->input('n_neighbors', 5);
        }

        // Sử dụng TrainingService để xử lý training
        $trainingService = app(TrainingService::class);
        
        // Choose training method
        $trainingMethod = $request->input('training_method', 'api');
        
        if ($trainingMethod === 'api') {
            $result = $trainingService->trainModelViaAPI($dataset, $user, $options);
        } else {
            $result = $trainingService->trainModel($dataset, $user, $options);
        }

        // Prepare training data for email
        $trainingData = [
            'model_type' => $modelType,
            'dataset_path' => $dataset->FilePath,
            'model_name' => $options['model_name'] ?? 'Model_' . time(),
            'test_size' => $options['test_size'] ?? 0.2,
            'dataset_name' => $dataset->DatasetName,
        ];

        // Send email notification
        try {
            $notificationEmail = EmailSetting::get('notification_email');
            if ($notificationEmail) {
                // Apply email config from database
                $this->applyEmailConfig();
                Mail::to($notificationEmail)->send(new TrainingCompletedMail($trainingData, $result));
            } elseif ($user && $user->email) {
                // Fallback to user email if notification email not set
                Mail::to($user->email)->send(new TrainingCompletedMail($trainingData, $result));
            }
        } catch (\Exception $e) {
            Log::warning('Failed to send training notification email: ' . $e->getMessage());
        }

        // Trả về kết quả
        if ($result['success']) {
            $message = 'Model trained successfully with dataset: ' . $dataset->DatasetName;
            if (isset($result['metrics'])) {
                $message .= sprintf(
                    ' | R²: %.4f | RMSE: %.4f | MAE: %.4f',
                    $result['metrics']['r2_score'] ?? 0,
                    $result['metrics']['rmse'] ?? 0,
                    $result['metrics']['mae'] ?? 0
                );
            }
            
            // Check if request is AJAX
            if ($request->ajax() || $request->wantsJson()) {
                return response()->json([
                    'success' => true,
                    'message' => $message,
                    'metrics' => $result['metrics'] ?? null
                ]);
            }
            
            return redirect()->route($this->routePrefix() . '.datasets.index')
                ->with('success', $message);
        } else {
            // Check if request is AJAX
            if ($request->ajax() || $request->wantsJson()) {
                return response()->json([
                    'success' => false,
                    'error' => $result['error'] ?? 'Unknown error'
                ], 500);
            }
            
            return redirect()->route($this->routePrefix() . '.datasets.index')
                ->with('error', 'Training failed: ' . ($result['error'] ?? 'Unknown error'));
        }
    }

    /**
     * Hiển thị form data augmentation
     */
    public function showAugmentForm($id)
    {
        $dataset = Dataset::with('user')->findOrFail($id);
        $augmentationService = app(DataAugmentationService::class);
        $availableMethods = $augmentationService->getAvailableMethods();
        
        return view('admin.datasets.augment', compact('dataset', 'availableMethods'));
    }

    /**
     * Thực hiện data augmentation
     */
    public function augment(Request $request, $id)
    {
        $dataset = Dataset::findOrFail($id);

        // Validate augmentation parameters
        $request->validate([
            'method' => 'required|in:smote,random_oversample,random_undersample,noise_injection,interpolation,duplication',
            'output_name' => 'nullable|string|max:255',
            'sampling_strategy' => 'nullable|in:auto,minority,not majority,not minority,all',
            'k_neighbors' => 'nullable|integer|min:1|max:20',
            'noise_level' => 'nullable|numeric|min:0|max:1',
            'duplicate_factor' => 'nullable|integer|min:2|max:10',
        ]);

        // Prepare augmentation options
        $options = [
            'method' => $request->input('method'),
            'output_name' => $request->input('output_name'),
            'sampling_strategy' => $request->input('sampling_strategy', 'auto'),
            'k_neighbors' => $request->input('k_neighbors', 5),
            'noise_level' => $request->input('noise_level', 0.05),
            'duplicate_factor' => $request->input('duplicate_factor', 2),
        ];

        // Thực hiện augmentation
        $augmentationService = app(DataAugmentationService::class);
        $result = $augmentationService->augmentDataset($dataset, $options);

        // Trả về kết quả
        if ($result['success']) {
            $message = sprintf(
                'Data augmentation completed! Original rows: %d → Augmented rows: %d',
                $result['original_rows'] ?? 0,
                $result['augmented_rows'] ?? 0
            );
            
            return redirect()->route($this->routePrefix() . '.datasets.index')
                ->with('success', $message);
        } else {
            return redirect()->route($this->routePrefix() . '.datasets.index')
                ->with('error', 'Augmentation failed: ' . ($result['error'] ?? 'Unknown error'));
        }
    }
}
