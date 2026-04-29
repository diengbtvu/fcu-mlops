<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class TrainingProgressController extends Controller
{
    public function generateSession(): JsonResponse
    {
        return response()->json([
            'success' => true,
            'session_id' => (string) Str::uuid(),
        ]);
    }

    public function show(string $sessionId): JsonResponse
    {
        $localProgress = $this->readLocalProgress($sessionId);
        if ($localProgress !== null) {
            return response()->json([
                'success' => true,
                'progress' => $localProgress,
            ]);
        }

        return $this->proxyProgress($sessionId);
    }

    private function readLocalProgress(string $sessionId): ?array
    {
        foreach ($this->progressDirectories() as $directory) {
            $path = rtrim($directory, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . $sessionId . '.json';
            if (!is_file($path)) {
                continue;
            }

            $contents = @file_get_contents($path);
            if ($contents === false) {
                Log::warning('Unable to read training progress file.', [
                    'path' => $path,
                    'session_id' => $sessionId,
                ]);
                continue;
            }

            $payload = json_decode($contents, true);
            if (is_array($payload)) {
                return $payload;
            }

            Log::warning('Training progress file contains invalid JSON.', [
                'path' => $path,
                'session_id' => $sessionId,
            ]);
        }

        return null;
    }

    private function progressDirectories(): array
    {
        $configuredPath = (string) config('services.predict_service.progress_path', '');
        $repoPath = realpath(base_path('../predict-service/training_progress')) ?: null;

        return array_values(array_unique(array_filter([
            $configuredPath !== '' ? $configuredPath : null,
            storage_path('app/training-progress'),
            $repoPath,
        ])));
    }

    private function proxyProgress(string $sessionId): JsonResponse
    {
        $baseUrl = rtrim((string) config('services.predict_service.url', 'http://localhost:5000'), '/');
        $url = $baseUrl . '/progress/' . rawurlencode($sessionId);

        try {
            $response = Http::acceptJson()
                ->timeout(5)
                ->get($url);
        } catch (ConnectionException $exception) {
            Log::warning('Training progress request failed.', [
                'session_id' => $sessionId,
                'url' => $url,
                'error' => $exception->getMessage(),
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Training progress service is unavailable.',
            ], 502);
        }

        $payload = $response->json();
        if (!is_array($payload)) {
            $rawBody = trim((string) $response->body());
            if ($rawBody !== '') {
                $decoded = json_decode($rawBody, true);
                if (is_array($decoded)) {
                    $payload = $decoded;
                }
            }
        }

        if (!is_array($payload)) {
            Log::warning('Training progress service returned a non-JSON response.', [
                'session_id' => $sessionId,
                'status' => $response->status(),
                'body_preview' => mb_substr((string) $response->body(), 0, 500),
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Training progress service returned an invalid response.',
            ], 502);
        }

        return response()->json($payload, $response->status());
    }
}
