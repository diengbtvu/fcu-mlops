<?php

namespace App\Support;

use App\Models\EmailSetting;

class GroqKeyStatus
{
    public const KEYS_SETTING = 'groq_api_keys';
    public const STATUS_SETTING = 'groq_api_key_statuses';

    public static function normalizeKeys(?string $rawValue): array
    {
        $items = preg_split('/[\s,;]+/', (string) $rawValue) ?: [];
        $keys = [];
        foreach ($items as $item) {
            $key = trim((string) $item);
            if ($key === '' || in_array($key, $keys, true)) {
                continue;
            }
            $keys[] = $key;
        }

        return $keys;
    }

    public static function hashKey(string $key): string
    {
        return hash('sha256', trim($key));
    }

    public static function maskKey(string $key): string
    {
        $key = trim($key);
        if ($key === '') {
            return '';
        }

        $prefix = substr($key, 0, min(7, strlen($key)));
        $suffix = strlen($key) > 4 ? substr($key, -4) : '';

        return $suffix !== '' ? $prefix . '...' . $suffix : $prefix . '...';
    }

    public static function loadStatusMap(?string $rawValue = null): array
    {
        $rawValue ??= (string) EmailSetting::get(self::STATUS_SETTING, '');
        $decoded = json_decode((string) $rawValue, true);
        if (!is_array($decoded)) {
            return [];
        }

        $statusMap = [];
        foreach ($decoded as $hash => $entry) {
            $hash = strtolower(trim((string) $hash));
            if (!preg_match('/^[a-f0-9]{64}$/', $hash) || !is_array($entry)) {
                continue;
            }

            $statusMap[$hash] = [
                'status' => (string) ($entry['status'] ?? ''),
                'reason' => (string) ($entry['reason'] ?? ''),
                'message' => (string) ($entry['message'] ?? ''),
                'masked_key' => (string) ($entry['masked_key'] ?? ''),
                'blocked_at' => (string) ($entry['blocked_at'] ?? ''),
                'updated_at' => (string) ($entry['updated_at'] ?? ''),
                'last_http_status' => isset($entry['last_http_status']) ? (int) $entry['last_http_status'] : null,
                'source' => (string) ($entry['source'] ?? ''),
            ];
        }

        return $statusMap;
    }

    public static function saveStatusMap(array $statusMap): void
    {
        EmailSetting::set(
            self::STATUS_SETTING,
            json_encode($statusMap, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES),
            [
                'type' => 'textarea',
                'group' => 'ai',
                'description' => 'Groq API key runtime statuses keyed by SHA-256 fingerprint',
                'is_encrypted' => false,
            ]
        );
    }

    public static function pruneStatusMap(array $statusMap, array $keys): array
    {
        $allowed = [];
        foreach ($keys as $key) {
            $allowed[self::hashKey((string) $key)] = true;
        }

        return array_filter(
            $statusMap,
            static fn ($entry, $hash) => isset($allowed[(string) $hash]),
            ARRAY_FILTER_USE_BOTH
        );
    }

    public static function statusForKey(array $statusMap, string $key): ?array
    {
        $hash = self::hashKey($key);
        $entry = $statusMap[$hash] ?? null;

        return is_array($entry) ? $entry : null;
    }

    public static function isBlocked(?array $status): bool
    {
        return is_array($status) && ($status['status'] ?? null) === 'blocked';
    }

    public static function filterUsableKeys(array $keys, array $statusMap): array
    {
        return array_values(array_filter(
            $keys,
            fn ($key) => !self::isBlocked(self::statusForKey($statusMap, (string) $key))
        ));
    }
}
