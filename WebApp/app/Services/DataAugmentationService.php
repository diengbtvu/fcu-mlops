<?php

namespace App\Services;

use App\Models\Dataset;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Http;

class DataAugmentationService
{
    /**
     * Thực hiện data augmentation cho dataset
     * 
     * @param Dataset $dataset
     * @param array $options
     * @return array
     */
    public function augmentDataset(Dataset $dataset, array $options = [])
    {
        try {
            // Lấy đường dẫn file dataset gốc
            $originalFilePath = storage_path('app/public/' . $dataset->FilePath);
            
            if (!file_exists($originalFilePath)) {
                throw new \Exception("Dataset file not found: {$originalFilePath}");
            }

            // Gọi API Python để thực hiện augmentation
            $response = Http::timeout(300)->post(config('services.predict_service.url') . '/augment', [
                'dataset_path' => $originalFilePath,
                'augmentation_method' => $options['method'] ?? 'smote',
                'sampling_strategy' => $options['sampling_strategy'] ?? 'auto',
                'k_neighbors' => $options['k_neighbors'] ?? 5,
                'noise_level' => $options['noise_level'] ?? 0.05,
                'duplicate_factor' => $options['duplicate_factor'] ?? 2,
                'output_name' => $options['output_name'] ?? null,
            ]);

            if (!$response->successful()) {
                throw new \Exception("Augmentation API failed: " . $response->body());
            }

            $result = $response->json();

            // Lưu augmented dataset vào database
            if (isset($result['augmented_file_path']) && $result['success']) {
                $augmentedDataset = $this->saveAugmentedDataset(
                    $dataset,
                    $result['augmented_file_path'],
                    $options
                );

                return [
                    'success' => true,
                    'dataset' => $augmentedDataset,
                    'original_rows' => $result['original_rows'] ?? 0,
                    'augmented_rows' => $result['augmented_rows'] ?? 0,
                    'message' => $result['message'] ?? 'Data augmentation completed successfully'
                ];
            }

            throw new \Exception("No augmented file path returned from API");

        } catch (\Exception $e) {
            Log::error('Data augmentation failed: ' . $e->getMessage());
            
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }

    /**
     * Lưu augmented dataset vào database
     */
    private function saveAugmentedDataset(Dataset $originalDataset, string $augmentedFilePath, array $options)
    {
        // Copy file từ predict-service sang storage của Laravel
        $fileName = basename($augmentedFilePath);
        $storagePath = 'datasets/' . $fileName;
        
        // Copy file vào storage
        Storage::disk('public')->put(
            $storagePath,
            file_get_contents($augmentedFilePath)
        );

        // Tạo dataset mới trong database
        $augmentedDataset = Dataset::create([
            'DatasetName' => $this->generateAugmentedName($originalDataset->DatasetName, $options),
            'FilePath' => $storagePath,
            'Description' => $this->generateAugmentedDescription($originalDataset, $options),
            'UploadedBy' => $originalDataset->UploadedBy,
            'UploadDate' => now(),
        ]);

        return $augmentedDataset;
    }

    /**
     * Tạo tên cho augmented dataset
     */
    private function generateAugmentedName(string $originalName, array $options): string
    {
        $method = $options['method'] ?? 'augmented';
        $timestamp = now()->format('YmdHis');
        
        return "{$originalName}_augmented_{$method}_{$timestamp}";
    }

    /**
     * Tạo mô tả cho augmented dataset
     */
    private function generateAugmentedDescription(Dataset $originalDataset, array $options): string
    {
        $method = $options['method'] ?? 'unknown';
        $methodNames = [
            'smote' => 'SMOTE (Synthetic Minority Over-sampling)',
            'random_oversample' => 'Random Oversampling',
            'random_undersample' => 'Random Undersampling',
            'noise_injection' => 'Noise Injection',
            'interpolation' => 'Data Interpolation',
            'duplication' => 'Data Duplication with Variation'
        ];
        
        $methodName = $methodNames[$method] ?? $method;
        
        $description = "Augmented from dataset: {$originalDataset->DatasetName}\n";
        $description .= "Augmentation method: {$methodName}\n";
        
        if ($originalDataset->Description) {
            $description .= "Original description: {$originalDataset->Description}";
        }
        
        return $description;
    }

    /**
     * Lấy danh sách các phương pháp augmentation có sẵn
     */
    public function getAvailableMethods(): array
    {
        return [
            'smote' => [
                'name' => 'SMOTE',
                'description' => 'Synthetic Minority Over-sampling Technique',
                'parameters' => ['k_neighbors', 'sampling_strategy']
            ],
            // 'random_oversample' => [
            //     'name' => 'Random Oversampling',
            //     'description' => 'Tăng số lượng mẫu bằng cách sao chép ngẫu nhiên các mẫu hiện có',
            //     'parameters' => ['sampling_strategy']
            // ],
            // 'random_undersample' => [
            //     'name' => 'Random Undersampling',
            //     'description' => 'Giảm số lượng mẫu đa số để cân bằng dataset',
            //     'parameters' => ['sampling_strategy']
            // ],
            'noise_injection' => [
                'name' => 'Noise Injection',
                'description' => 'Add Gaussian noise to data to increase diversity',
                'parameters' => ['noise_level', 'duplicate_factor']
            ],
            // 'interpolation' => [
            //     'name' => 'Linear Interpolation',
            //     'description' => 'Tạo dữ liệu mới bằng cách nội suy tuyến tính giữa các mẫu',
            //     'parameters' => ['duplicate_factor']
            // ],
            // 'duplication' => [
            //     'name' => 'Duplication with Variation',
            //     'description' => 'Nhân đôi dữ liệu với các biến thể nhỏ',
            //     'parameters' => ['duplicate_factor', 'noise_level']
            // ]
        ];
    }
}
