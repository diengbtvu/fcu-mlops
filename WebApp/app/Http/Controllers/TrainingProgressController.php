<?php

namespace App\Http\Controllers;

use App\Support\PredictServiceUrl;
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
        $candidateUrls = PredictServiceUrl::urls('/progress/' . rawurlencode($sessionId));
        $lastConnectionException = null;
        $lastResponse = null;

        foreach ($candidateUrls as $url) {
            try {
                $response = Http::acceptJson()
                    ->timeout(5)
                    ->get($url);
            } catch (ConnectionException $exception) {
                $lastConnectionException = $exception;

                Log::warning('Training progress request failed.', [
                    'session_id' => $sessionId,
                    'url' => $url,
                    'error' => $exception->getMessage(),
                ]);
                continue;
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

            if (is_array($payload)) {
                return response()->json($payload, $response->status());
            }

            $lastResponse = $response;
        }

        if ($lastConnectionException !== null) {
            Log::warning('Training progress service is unavailable after all fallbacks.', [
                'session_id' => $sessionId,
                'error' => $lastConnectionException->getMessage(),
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Training progress service is unavailable.',
            ], 502);
        }

        Log::warning('Training progress service returned a non-JSON response.', [
            'session_id' => $sessionId,
            'status' => $lastResponse?->status(),
            'body_preview' => $lastResponse ? mb_substr((string) $lastResponse->body(), 0, 500) : null,
        ]);

        return response()->json([
            'success' => false,
            'error' => 'Training progress service returned an invalid response.',
        ], 502);
    }
}
