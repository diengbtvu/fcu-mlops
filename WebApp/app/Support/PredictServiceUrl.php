<?php

namespace App\Support;

class PredictServiceUrl
{
    public static function bases(bool $includeAppProxy = true): array
    {
        $requestBase = null;
        if (app()->bound('request')) {
            try {
                $requestBase = request()->getSchemeAndHttpHost();
            } catch (\Throwable) {
                $requestBase = null;
            }
        }

        $candidates = [
            config('services.predict_service.url'),
            config('services.predict_service.public_url'),
            config('services.predict_service.browser_url'),
        ];

        if ($includeAppProxy) {
            $candidates[] = $requestBase;
            $candidates[] = config('app.url');
        }

        $bases = [];
        foreach ($candidates as $candidate) {
            $base = rtrim(trim((string) $candidate), '/');
            if ($base === '' || in_array($base, $bases, true)) {
                continue;
            }
            $bases[] = $base;
        }

        return $bases;
    }

    public static function urls(string $path, bool $includeAppProxy = true): array
    {
        $normalizedPath = '/' . ltrim($path, '/');

        return array_map(
            static fn (string $base): string => $base . $normalizedPath,
            self::bases($includeAppProxy)
        );
    }
}
