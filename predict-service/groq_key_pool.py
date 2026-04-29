from __future__ import annotations

import os
import re
import time
from collections.abc import Iterable
from hashlib import sha256


_GLOBAL_KEY_COOLDOWNS: dict[str, float] = {}
_GLOBAL_POOL_CURSORS: dict[str, int] = {}


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


def groq_api_keys_from_env() -> list[str]:
    keys = parse_groq_api_keys(os.getenv("GROQ_API_KEYS"))
    keys.extend(parse_groq_api_keys(os.getenv("GROQ_API_KEY")))
    return parse_groq_api_keys(keys)


class GroqApiKeyPool:
    def __init__(self, keys: Iterable[str]) -> None:
        self.keys = parse_groq_api_keys(list(keys))
        if not self.keys:
            raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not configured.")
        self._key_ids = [sha256(key.encode("utf-8")).hexdigest() for key in self.keys]
        self._pool_id = sha256("\0".join(self._key_ids).encode("utf-8")).hexdigest()
        self._cursor = _GLOBAL_POOL_CURSORS.get(self._pool_id, 0) % self.size
        self._cooldowns: dict[int, float] = {}

    @property
    def size(self) -> int:
        return len(self.keys)

    def label(self, key_index: int | None) -> str:
        if key_index is None:
            return "Groq key"
        return f"Groq key {key_index + 1}/{self.size}"

    def has_available_key(self) -> bool:
        now = time.monotonic()
        return any(self._cooldown_until(index) <= now for index in range(self.size))

    def mark_rate_limited(self, key_index: int | None, cooldown_seconds: float) -> None:
        if key_index is None:
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

    def wait_for_available_key(self, max_wait_seconds: float, sleep_fn=time.sleep) -> float:
        now = time.monotonic()
        delays = [
            max(0.0, self._cooldown_until(index) - now)
            for index in range(self.size)
        ]
        wait_seconds = min(delays) if delays else 0.0
        wait_seconds = min(wait_seconds, max(0.0, float(max_wait_seconds)))
        if wait_seconds > 0:
            sleep_fn(wait_seconds)
        return wait_seconds

    def next_key(self) -> tuple[int, str]:
        now = time.monotonic()
        for offset in range(self.size):
            index = (self._cursor + offset) % self.size
            if self._cooldown_until(index) <= now:
                self._set_cursor((index + 1) % self.size)
                return index, self.keys[index]

        index = min(
            range(self.size),
            key=lambda item: self._cooldown_until(item),
        )
        self._set_cursor((index + 1) % self.size)
        return index, self.keys[index]

    def _set_cursor(self, cursor: int) -> None:
        self._cursor = cursor % self.size
        _GLOBAL_POOL_CURSORS[self._pool_id] = self._cursor
