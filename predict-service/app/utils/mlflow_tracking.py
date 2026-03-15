"""
Shared MLflow tracking configuration helpers.

This module centralizes how the service picks a writable tracking directory.
When the default mounted volume is not writable, it falls back to /tmp.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

import mlflow

logger = logging.getLogger(__name__)


def _is_file_uri(uri: str) -> bool:
    return uri.startswith("file://") or uri.startswith("file:")


def _file_uri_to_path(uri: str) -> Optional[Path]:
    if uri.startswith("file://"):
        path_str = uri[7:]
    elif uri.startswith("file:"):
        path_str = uri[5:]
    else:
        return None

    if not path_str:
        return None

    return Path(path_str)


def _resolve_default_tracking_dir() -> Path:
    current_file = Path(__file__).resolve()
    app_dir = current_file.parent.parent
    return app_dir / "mlruns"


def _ensure_writable_tracking_dir(tracking_dir: Path) -> bool:
    probe_file = tracking_dir / ".mlflow_write_probe"

    try:
        tracking_dir.mkdir(parents=True, exist_ok=True)
        (tracking_dir / ".trash").mkdir(parents=True, exist_ok=True)

        with open(probe_file, "w", encoding="utf-8") as handle:
            handle.write("ok")

        probe_file.unlink(missing_ok=True)
        return True
    except Exception as exc:
        logger.warning("MLflow tracking directory is not writable: %s (%s)", tracking_dir, exc)
        return False


def configure_mlflow_tracking_uri(preferred_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Configure MLflow tracking URI with writable-path fallback.

    Priority:
    1) Non-file MLFLOW_TRACKING_URI (kept as-is)
    2) File URI from MLFLOW_TRACKING_URI
    3) preferred_dir (if provided)
    4) app/mlruns
    5) /tmp/hydrogen_mlops_mlruns
    """
    env_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()

    # Keep remote tracking server as configured by env.
    if env_tracking_uri and not _is_file_uri(env_tracking_uri):
        mlflow.set_tracking_uri(env_tracking_uri)
        return {
            "tracking_uri": env_tracking_uri,
            "tracking_dir": None,
            "used_fallback": False,
        }

    fallback_dir = Path(
        os.getenv(
            "MLFLOW_FALLBACK_TRACKING_DIR",
            os.path.join(tempfile.gettempdir(), "hydrogen_mlops_mlruns"),
        )
    ).expanduser().resolve()

    candidate_dirs = []
    env_tracking_dir = _file_uri_to_path(env_tracking_uri) if env_tracking_uri else None
    if env_tracking_dir:
        candidate_dirs.append(env_tracking_dir)

    if preferred_dir:
        candidate_dirs.append(Path(preferred_dir))

    candidate_dirs.append(_resolve_default_tracking_dir())
    candidate_dirs.append(fallback_dir)

    unique_candidates = []
    seen = set()
    for candidate in candidate_dirs:
        resolved = candidate.expanduser().resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(resolved)

    for candidate in unique_candidates:
        if not _ensure_writable_tracking_dir(candidate):
            continue

        tracking_uri = candidate.as_uri()
        mlflow.set_tracking_uri(tracking_uri)
        return {
            "tracking_uri": tracking_uri,
            "tracking_dir": str(candidate),
            "used_fallback": candidate == fallback_dir,
        }

    tried_paths = ", ".join(str(path) for path in unique_candidates)
    raise PermissionError(
        f"Could not find a writable MLflow tracking directory. Tried: {tried_paths}"
    )
