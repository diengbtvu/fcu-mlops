from __future__ import annotations

import json
import os
import random
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Linux container path is primary
    fcntl = None  # type: ignore[assignment]


class SharedOpenAIRequestGate:
    """Serialize OpenAI calls across threads and local processes."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        resolved = state_path or os.getenv("OPENAI_SHARED_GATE_STATE_PATH") or "/tmp/hydrogen_openai_gate.json"
        self.state_path = Path(resolved)
        self._thread_lock = threading.Lock()

    def _ensure_parent(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _lock_handle(self, handle: object) -> None:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def _unlock_handle(self, handle: object) -> None:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_state(self, handle: object) -> dict[str, float]:
        handle.seek(0)
        raw = handle.read()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _write_state(self, handle: object, state: dict[str, float]) -> None:
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(state))
        handle.flush()
        os.fsync(handle.fileno())

    @contextmanager
    def request_slot(self, min_interval_seconds: float, jitter_seconds: float = 0.0) -> Iterator[None]:
        interval = max(0.0, float(min_interval_seconds))
        jitter = max(0.0, float(jitter_seconds))
        self._ensure_parent()

        with self._thread_lock:
            with self.state_path.open("a+", encoding="utf-8") as handle:
                self._lock_handle(handle)
                try:
                    state = self._read_state(handle)
                    wait_until = float(state.get("next_request_at", 0.0) or 0.0)
                    wait_seconds = max(0.0, wait_until - time.time())
                    if wait_seconds > 0:
                        time.sleep(wait_seconds)

                    yield
                finally:
                    next_request_at = time.time() + interval + random.uniform(0.0, jitter)
                    self._write_state(handle, {"next_request_at": next_request_at})
                    self._unlock_handle(handle)

    def push_cooldown(self, delay_seconds: float) -> None:
        delay = max(0.0, float(delay_seconds))
        if delay <= 0:
            return

        self._ensure_parent()
        with self._thread_lock:
            with self.state_path.open("a+", encoding="utf-8") as handle:
                self._lock_handle(handle)
                try:
                    state = self._read_state(handle)
                    current = float(state.get("next_request_at", 0.0) or 0.0)
                    state["next_request_at"] = max(current, time.time() + delay)
                    self._write_state(handle, state)
                finally:
                    self._unlock_handle(handle)


_SHARED_GATE = SharedOpenAIRequestGate()


def shared_openai_request_gate() -> SharedOpenAIRequestGate:
    return _SHARED_GATE
