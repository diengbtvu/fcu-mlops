from __future__ import annotations

import csv
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from zipfile import ZipFile

from .schemas import to_primitive

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
BUNDLE_MARKER_FILES = (
    "summary.json",
    "table_model_comparison.csv",
    "table1_incremental_results.csv",
    "gra_ranking.json",
)


class BundleResolutionError(RuntimeError):
    """Raised when a bundle path cannot be resolved to a usable directory."""


class BundleWorkspace:
    def __init__(
        self,
        source_path: Path,
        bundle_dir: Path,
        temp_dir: tempfile.TemporaryDirectory[str] | None = None,
    ) -> None:
        self.source_path = source_path
        self.bundle_dir = bundle_dir
        self._temp_dir = temp_dir

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()


def slugify(value: str) -> str:
    cleaned = []
    for char in value:
        if char.isalnum():
            cleaned.append(char.lower())
        else:
            cleaned.append("_")
    collapsed = "".join(cleaned)
    while "__" in collapsed:
        collapsed = collapsed.replace("__", "_")
    return collapsed.strip("_") or "benchmark"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_primitive(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(to_primitive(row), ensure_ascii=False) + "\n")


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: "" if value is None else value
                    for key, value in to_primitive(row).items()
                }
            )


def ensure_output_layout(output_dir: Path) -> dict[str, Path]:
    layout = {
        "root": output_dir,
        "gold": output_dir / "gold",
        "generations": output_dir / "generations",
        "extracted_claims": output_dir / "extracted_claims",
        "verifications": output_dir / "verifications",
        "arm_c_traces": output_dir / "arm_c_traces",
        "scores": output_dir / "scores",
    }
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    return layout


def _looks_like_bundle_dir(path: Path) -> bool:
    return all((path / marker).exists() for marker in BUNDLE_MARKER_FILES)


def _find_bundle_root(search_root: Path) -> Path:
    if _looks_like_bundle_dir(search_root):
        return search_root

    candidates: list[Path] = []
    for child in search_root.rglob("*"):
        if child.is_dir() and _looks_like_bundle_dir(child):
            candidates.append(child)

    if not candidates:
        raise BundleResolutionError(
            f"No extracted benchmark bundle found under '{search_root}'."
        )

    candidates.sort(key=lambda item: (len(item.parts), str(item)))
    return candidates[0]


@contextmanager
def bundle_workspace(bundle_path: str | Path) -> Iterator[BundleWorkspace]:
    path = Path(bundle_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Bundle path does not exist: {path}")

    if path.is_dir():
        workspace = BundleWorkspace(source_path=path, bundle_dir=_find_bundle_root(path))
        try:
            yield workspace
        finally:
            workspace.cleanup()
        return

    if path.suffix.lower() != ".zip":
        raise BundleResolutionError(
            f"Unsupported bundle input '{path}'. Use a directory or .zip bundle."
        )

    temp_dir = tempfile.TemporaryDirectory(prefix="benchmark_bundle_")
    extraction_root = Path(temp_dir.name)
    with ZipFile(path, "r") as archive:
        archive.extractall(extraction_root)

    workspace = BundleWorkspace(
        source_path=path,
        bundle_dir=_find_bundle_root(extraction_root),
        temp_dir=temp_dir,
    )
    try:
        yield workspace
    finally:
        workspace.cleanup()
