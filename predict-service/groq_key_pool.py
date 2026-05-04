from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import mysql.connector
import requests


_GLOBAL_KEY_COOLDOWNS: dict[str, float] = {}
_GLOBAL_POOL_CURSORS: dict[str, int] = {}
_GLOBAL_BLOCKED_KEY_IDS: set[str] = set()
GROQ_KEY_STATUSES_SETTING = "groq_api_key_statuses"
GROQ_KEY_POOL_REFRESH_INTERVAL_SECONDS = max(
    0.5,
    float(os.getenv("GROQ_KEY_POOL_REFRESH_INTERVAL_SECONDS", "2")),
)
GROQ_KEY_POOL_REQUEST_TIMEOUT_SECONDS = max(
    1.0,
    float(os.getenv("GROQ_KEY_POOL_REQUEST_TIMEOUT_SECONDS", "5")),
)
_LAST_LARAVEL_KEY_POOL_ERROR_AT = 0.0


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sql_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _mask_groq_key(key: str) -> str:
    key = str(key or "").strip()
    if not key:
        return ""
    prefix = key[: min(7, len(key))]
    suffix = key[-4:] if len(key) > 4 else ""
    return f"{prefix}...{suffix}" if suffix else f"{prefix}..."


def _laravel_groq_key_pool_url() -> str:
    base_url = str(os.getenv("LARAVEL_API_URL") or "").strip().rstrip("/")
    if not base_url:
        return ""
    if base_url.endswith("/internal/groq-key-pool"):
        return base_url
    return f"{base_url}/internal/groq-key-pool"


def _laravel_internal_token() -> str:
    return str(os.getenv("JWT_SECRET") or "").strip()


def _log_laravel_key_pool_error(message: str) -> None:
    global _LAST_LARAVEL_KEY_POOL_ERROR_AT

    now = time.monotonic()
    if now - _LAST_LARAVEL_KEY_POOL_ERROR_AT < 30:
        return
    _LAST_LARAVEL_KEY_POOL_ERROR_AT = now
    print(message)


def _db_connect_kwargs() -> dict[str, Any] | None:
    host = str(os.getenv("DB_HOST") or "").strip()
    database = str(os.getenv("DB_DATABASE") or "").strip()
    username = str(os.getenv("DB_USERNAME") or "").strip()
    if not host or not database or not username:
        return None

    return {
        "host": host,
        "port": int(str(os.getenv("DB_PORT") or "3306").strip() or "3306"),
        "user": username,
        "password": str(os.getenv("DB_PASSWORD") or ""),
        "database": database,
        "connection_timeout": 5,
        "autocommit": False,
    }


def _normalize_status_map(payload: object) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for key_hash, entry in payload.items():
        normalized_hash = str(key_hash or "").strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized_hash) or not isinstance(entry, dict):
            continue
        normalized[normalized_hash] = {
            "status": str(entry.get("status") or "").strip().lower(),
            "reason": str(entry.get("reason") or "").strip(),
            "message": str(entry.get("message") or "").strip()[:1000],
            "masked_key": str(entry.get("masked_key") or "").strip(),
            "blocked_at": str(entry.get("blocked_at") or "").strip(),
            "updated_at": str(entry.get("updated_at") or "").strip(),
            "last_http_status": entry.get("last_http_status"),
            "source": str(entry.get("source") or "").strip(),
        }
    return normalized


def _blocked_hashes_from_status_map(status_map: dict[str, dict[str, Any]]) -> set[str]:
    return {
        key_hash
        for key_hash, entry in status_map.items()
        if str(entry.get("status") or "").strip().lower() == "blocked"
    }


def _load_status_map_from_db() -> dict[str, dict[str, Any]] | None:
    connect_kwargs = _db_connect_kwargs()
    if connect_kwargs is None:
        return None

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(**connect_kwargs)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT value FROM email_settings WHERE `key` = %s LIMIT 1",
            (GROQ_KEY_STATUSES_SETTING,),
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return {}
        decoded = json.loads(str(row[0]))
        return _normalize_status_map(decoded)
    except Exception as exc:
        print(f"⚠️ Failed to load Groq key statuses from MySQL: {exc}")
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def _save_status_map_to_db(status_map: dict[str, dict[str, Any]]) -> bool:
    connect_kwargs = _db_connect_kwargs()
    if connect_kwargs is None:
        return False

    connection = None
    cursor = None
    try:
        payload = json.dumps(status_map, ensure_ascii=False, indent=2, sort_keys=True)
        now = _sql_timestamp()
        connection = mysql.connector.connect(**connect_kwargs)
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO email_settings (`key`, `value`, `type`, `group`, `description`, `is_encrypted`, `created_at`, `updated_at`)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                `value` = VALUES(`value`),
                `type` = VALUES(`type`),
                `group` = VALUES(`group`),
                `description` = VALUES(`description`),
                `is_encrypted` = VALUES(`is_encrypted`),
                `updated_at` = VALUES(`updated_at`)
            """,
            (
                GROQ_KEY_STATUSES_SETTING,
                payload,
                "textarea",
                "ai",
                "Groq API key runtime statuses keyed by SHA-256 fingerprint",
                0,
                now,
                now,
            ),
        )
        connection.commit()
        return True
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        print(f"⚠️ Failed to persist Groq key statuses to MySQL: {exc}")
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def refresh_blocked_key_ids_from_db() -> set[str]:
    status_map = _load_status_map_from_db()
    if status_map is not None:
        _GLOBAL_BLOCKED_KEY_IDS.clear()
        _GLOBAL_BLOCKED_KEY_IDS.update(_blocked_hashes_from_status_map(status_map))
    return set(_GLOBAL_BLOCKED_KEY_IDS)


def record_blocked_groq_key(
    api_key: str,
    *,
    reason: str,
    message: str,
    status_code: int | None = None,
    source: str = "predict-service",
) -> str:
    key_hash = sha256(api_key.encode("utf-8")).hexdigest()
    _GLOBAL_BLOCKED_KEY_IDS.add(key_hash)

    status_map = _load_status_map_from_db()
    if status_map is None:
        return key_hash

    existing = dict(status_map.get(key_hash) or {})
    blocked_at = str(existing.get("blocked_at") or "").strip() or _utc_timestamp()
    status_map[key_hash] = {
        "status": "blocked",
        "reason": str(reason or "").strip() or "blocked",
        "message": str(message or "").strip()[:1000],
        "masked_key": _mask_groq_key(api_key),
        "blocked_at": blocked_at,
        "updated_at": _utc_timestamp(),
        "last_http_status": int(status_code) if status_code is not None else None,
        "source": str(source or "").strip() or "predict-service",
    }
    _save_status_map_to_db(status_map)
    return key_hash


def parse_groq_api_keys(raw_value: object | None) -> list[str]:
    """Parse a Groq key list from a string/list while preserving order."""
    raw_items: list[str] = []
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        raw_items.extend(re.split(r"[\s,;]+", raw_value))
    elif isinstance(raw_value, Iterable):
        for item in raw_value:
            if isinstance(item, str):
                raw_items.extend(re.split(r"[\s,;]+", item))
    else:
        return []

    keys: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        key = item.strip()
        if not key or key in seen:
            continue
        keys.append(key)
        seen.add(key)
    return keys


def _fetch_latest_groq_key_pool_from_laravel() -> dict[str, Any] | None:
    api_url = _laravel_groq_key_pool_url()
    internal_token = _laravel_internal_token()
    if not api_url or not internal_token:
        return None

    try:
        response = requests.get(
            api_url,
            headers={
                "Accept": "application/json",
                "X-Internal-Token": internal_token,
            },
            timeout=GROQ_KEY_POOL_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError) as exc:
        _log_laravel_key_pool_error(f"⚠️ Failed to refresh Groq key pool from Laravel: {exc}")
        return None

    if not isinstance(payload, dict):
        _log_laravel_key_pool_error("⚠️ Failed to refresh Groq key pool from Laravel: invalid JSON payload.")
        return None

    payload["groq_api_keys"] = parse_groq_api_keys(
        payload.get("active_groq_api_keys") or payload.get("groq_api_keys")
    )
    return payload


def groq_api_keys_from_env() -> list[str]:
    latest_key_pool = _fetch_latest_groq_key_pool_from_laravel()
    if latest_key_pool is not None:
        return parse_groq_api_keys(latest_key_pool.get("groq_api_keys"))

    keys = parse_groq_api_keys(os.getenv("GROQ_API_KEYS"))
    keys.extend(parse_groq_api_keys(os.getenv("GROQ_API_KEY")))
    normalized = parse_groq_api_keys(keys)
    blocked_ids = refresh_blocked_key_ids_from_db()
    if not blocked_ids:
        return normalized
    return [
        key
        for key in normalized
        if sha256(key.encode("utf-8")).hexdigest() not in blocked_ids
    ]


class GroqApiKeyPool:
    def __init__(self, keys: Iterable[str]) -> None:
        self.keys: list[str] = []
        self._key_ids: list[str] = []
        self._pool_id = "groq-empty"
        self._cursor = 0
        self._cooldowns: dict[int, float] = {}
        self._last_refresh_at = 0.0
        self._blocked_key_ids = set(refresh_blocked_key_ids_from_db())
        self._replace_keys(parse_groq_api_keys(keys), keep_cursor=False)
        self.refresh_from_laravel(force=True)
        if not self.keys:
            raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not configured.")

    @property
    def size(self) -> int:
        return len(self.keys)

    def label(self, key_index: int | None) -> str:
        if key_index is None or self.size <= 0:
            return "Groq key"
        return f"Groq key {key_index + 1}/{self.size}"

    def is_blocked(self, key_index: int) -> bool:
        key_id = self._key_ids[key_index]
        return key_id in self._blocked_key_ids or key_id in _GLOBAL_BLOCKED_KEY_IDS

    def has_usable_key(self, ignore_cooldown: bool = False) -> bool:
        if self.size <= 0:
            return False
        now = time.monotonic()
        for index in range(self.size):
            if self.is_blocked(index):
                continue
            if ignore_cooldown or self._cooldown_until(index) <= now:
                return True
        return False

    def has_available_key(self) -> bool:
        return self.has_usable_key(ignore_cooldown=False)

    def mark_rate_limited(self, key_index: int | None, cooldown_seconds: float) -> None:
        if key_index is None or self.size <= 0:
            return
        cooldown = max(0.0, float(cooldown_seconds))
        until = time.monotonic() + cooldown
        self._cooldowns[key_index] = max(self._cooldowns.get(key_index, 0.0), until)
        key_id = self._key_ids[key_index]
        _GLOBAL_KEY_COOLDOWNS[key_id] = max(_GLOBAL_KEY_COOLDOWNS.get(key_id, 0.0), until)

    def _cooldown_until(self, key_index: int) -> float:
        return max(
            self._cooldowns.get(key_index, 0.0),
            _GLOBAL_KEY_COOLDOWNS.get(self._key_ids[key_index], 0.0),
        )

    def mark_blocked(self, key_index: int | None) -> None:
        if key_index is None or self.size <= 0:
            return
        key_id = self._key_ids[key_index]
        self._blocked_key_ids.add(key_id)
        _GLOBAL_BLOCKED_KEY_IDS.add(key_id)

    def wait_for_available_key(self, max_wait_seconds: float, sleep_fn=time.sleep) -> float:
        if self.size <= 0:
            return 0.0
        if not self.has_usable_key(ignore_cooldown=True):
            return 0.0
        now = time.monotonic()
        delays = [
            max(0.0, self._cooldown_until(index) - now)
            for index in range(self.size)
            if not self.is_blocked(index)
        ]
        wait_seconds = min(delays) if delays else 0.0
        wait_seconds = min(wait_seconds, max(0.0, float(max_wait_seconds)))
        if wait_seconds > 0:
            sleep_fn(wait_seconds)
        return wait_seconds

    def next_available_delay(self, exclude_index: int | None = None) -> float | None:
        if self.size <= 0:
            return None
        now = time.monotonic()
        delays = [
            max(0.0, self._cooldown_until(index) - now)
            for index in range(self.size)
            if index != exclude_index and not self.is_blocked(index)
        ]
        if not delays:
            return None
        return min(delays)

    def next_key(self) -> tuple[int, str]:
        if self.size <= 0:
            raise RuntimeError("No Groq API keys are currently configured.")
        if not self.has_usable_key(ignore_cooldown=True):
            raise RuntimeError(
                "All configured Groq API keys are marked blocked. "
                "Reactivate or replace a key in Admin > Settings > AI."
            )

        now = time.monotonic()
        for offset in range(self.size):
            index = (self._cursor + offset) % self.size
            if self.is_blocked(index):
                continue
            if self._cooldown_until(index) <= now:
                self._set_cursor((index + 1) % self.size)
                return index, self.keys[index]

        available_indexes = [
            index
            for index in range(self.size)
            if not self.is_blocked(index)
        ]
        index = min(available_indexes, key=lambda item: self._cooldown_until(item))
        self._set_cursor((index + 1) % self.size)
        return index, self.keys[index]

    def refresh_from_laravel(self, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and now - self._last_refresh_at < GROQ_KEY_POOL_REFRESH_INTERVAL_SECONDS:
            return False

        self._last_refresh_at = now
        latest_key_pool = _fetch_latest_groq_key_pool_from_laravel()
        self._blocked_key_ids = set(refresh_blocked_key_ids_from_db())
        if latest_key_pool is None:
            return False

        latest_keys = parse_groq_api_keys(latest_key_pool.get("groq_api_keys"))
        if latest_keys == self.keys:
            return False

        self._replace_keys(latest_keys, keep_cursor=True)
        return True

    def _replace_keys(self, keys: Iterable[str], *, keep_cursor: bool) -> None:
        normalized_keys = parse_groq_api_keys(keys)
        previous_key_ids = list(getattr(self, "_key_ids", []))
        previous_cooldowns = {
            previous_key_ids[index]: until
            for index, until in getattr(self, "_cooldowns", {}).items()
            if 0 <= index < len(previous_key_ids)
        }
        previous_cursor = getattr(self, "_cursor", 0)

        self.keys = normalized_keys
        self._key_ids = [sha256(key.encode("utf-8")).hexdigest() for key in self.keys]

        if not self.keys:
            self._pool_id = "groq-empty"
            self._cursor = 0
            self._cooldowns = {}
            return

        self._pool_id = sha256("\0".join(self._key_ids).encode("utf-8")).hexdigest()
        default_cursor = previous_cursor % len(self.keys) if keep_cursor else 0
        self._cursor = _GLOBAL_POOL_CURSORS.get(self._pool_id, default_cursor) % len(self.keys)
        self._cooldowns = {
            index: previous_cooldowns[key_id]
            for index, key_id in enumerate(self._key_ids)
            if key_id in previous_cooldowns
        }
        _GLOBAL_POOL_CURSORS[self._pool_id] = self._cursor

    def _set_cursor(self, cursor: int) -> None:
        if self.size <= 0:
            self._cursor = 0
            return
        self._cursor = cursor % self.size
        _GLOBAL_POOL_CURSORS[self._pool_id] = self._cursor
