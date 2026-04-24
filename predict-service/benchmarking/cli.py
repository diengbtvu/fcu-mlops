from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .claim_extractor import normalize_generation
from .chart_reporting import write_per_chart_benchmark_outputs
from .generator import generate_explanations
from .gold_builders import build_gold_artifacts
from .io_utils import bundle_workspace, ensure_output_layout, slugify, write_csv_rows, write_json, write_jsonl
from .llm_client import FixtureLLMClient, OllamaLLMClient, OpenAILLMClient
from .manifest import build_manifest, load_artifact_inputs
from .metrics import build_leaderboard, compute_artifact_scores
from .schemas import SUPPORTED_ARMS, SUPPORTED_CONDITIONS, SUPPORTED_SEMANTIC_LEVELS
from .verifier import verify_claims

DEFAULT_ARMS = "A,B,C"
DEFAULT_CONDITIONS = "table_only,image_table,image_table_summary"
DEFAULT_LEVELS = "L1,L2L3,L1L2L3"


def _fixture_bundle_path() -> Path:
    return Path(__file__).resolve().parent.parent / "tests" / "benchmarking" / "fixtures" / "sample_bundle"


def _parse_csv_option(raw_value: str, allowed: tuple[str, ...], option_name: str) -> list[str]:
    items = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not items:
        raise ValueError(f"{option_name} cannot be empty.")
    invalid = [item for item in items if item not in allowed]
    if invalid:
        raise ValueError(
            f"Unsupported {option_name}: {', '.join(invalid)}. Allowed values: {', '.join(allowed)}."
        )
    return items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline artifact-grounded explanation benchmarking runner.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=("run", "build-manifest", "build-gold", "export"),
        help="Default command is 'run'. 'export' is an alias for the full run.",
    )
    parser.add_argument("--bundle-path", help="Path to an extracted bundle directory or .zip bundle.")
    parser.add_argument("--output-dir", required=True, help="Directory for benchmark outputs.")
    parser.add_argument("--arms", default=DEFAULT_ARMS, help=f"Comma-separated arms. Default: {DEFAULT_ARMS}.")
    parser.add_argument(
        "--conditions",
        default=DEFAULT_CONDITIONS,
        help=f"Comma-separated conditions. Default: {DEFAULT_CONDITIONS}.",
    )
    parser.add_argument(
        "--levels",
        help=(
            "Comma-separated semantic levels for Arm B only. "
            f"Default when Arm B is selected: {DEFAULT_LEVELS}."
        ),
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Use the bundled synthetic fixture bundle when --bundle-path is omitted.",
    )
    parser.add_argument(
        "--client",
        choices=("fixture", "openai", "ollama"),
        default="fixture",
        help="LLM client for benchmark generations. Default: fixture.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse any existing valid generation files in the output directory and regenerate only missing runs.",
    )
    return parser


def _resolve_bundle_path(bundle_path: str | None, fixture_only: bool) -> Path:
    if bundle_path:
        return Path(bundle_path).expanduser()
    if fixture_only:
        fixture_path = _fixture_bundle_path()
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture bundle is missing: {fixture_path}")
        return fixture_path
    raise FileNotFoundError("Missing --bundle-path. Use --fixture-only to run the built-in synthetic fixture.")


def _warning_messages(records: list[Any], conditions: list[str]) -> list[str]:
    warnings: list[str] = []
    if any(condition.startswith("image") for condition in conditions):
        for record in records:
            if not record.chart_file:
                warnings.append(
                    f"{record.artifact_id}: image-based condition requested but no chart file was available; "
                    "table/json evidence will still be used."
                )
    return warnings


def _metadata_payload(
    command: str,
    bundle_path: Path,
    resolved_bundle_dir: Path,
    output_dir: Path,
    arms: list[str],
    conditions: list[str],
    levels: list[str],
    warnings: list[str],
    manifest_count: int,
    generation_count: int,
    client_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "command": command,
        "source_bundle_path": str(bundle_path.resolve()),
        "resolved_bundle_dir": str(resolved_bundle_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "arms": arms,
        "conditions": conditions,
        "levels": levels,
        "client": client_metadata.get("client"),
        "client_model": client_metadata.get("model"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": manifest_count,
        "generation_count": generation_count,
        "warnings": warnings,
    }


def _build_llm_client(client_name: str) -> Any:
    if client_name == "fixture":
        return FixtureLLMClient()
    if client_name == "openai":
        return OpenAILLMClient()
    if client_name == "ollama":
        return OllamaLLMClient()
    raise ValueError(f"Unsupported benchmark client: {client_name}")


def _generation_base_name(generation: Any) -> str:
    name_parts = [generation.artifact_id, generation.arm]
    if getattr(generation, "semantic_level", None):
        name_parts.append(generation.semantic_level)
    name_parts.append(generation.input_condition)
    return slugify("_".join(name_parts))


def _generation_base_name_for_run(
    artifact_id: str,
    arm: str,
    input_condition: str,
    semantic_level: str | None,
) -> str:
    name_parts = [artifact_id, arm]
    if semantic_level:
        name_parts.append(semantic_level)
    name_parts.append(input_condition)
    return slugify("_".join(name_parts))


def _requested_runs(
    arms: list[str],
    conditions: list[str],
    levels: list[str],
) -> list[tuple[str, str, str | None]]:
    runs: list[tuple[str, str, str | None]] = []
    for arm in arms:
        for condition in conditions:
            if arm == "B":
                for level in levels:
                    runs.append((arm, condition, level))
            else:
                runs.append((arm, condition, None))
    return runs


def _prune_unexpected_output_files(layout: dict[str, Path], expected_base_names: set[str]) -> None:
    for key in ("generations", "extracted_claims", "verifications", "arm_c_traces"):
        directory = layout[key]
        for path in directory.glob("*.json"):
            if path.stem not in expected_base_names:
                path.unlink()


def _load_existing_generation(
    layout: dict[str, Path],
    artifact_id: str,
    arm: str,
    input_condition: str,
    semantic_level: str | None,
) -> Any | None:
    base_name = _generation_base_name_for_run(
        artifact_id=artifact_id,
        arm=arm,
        input_condition=input_condition,
        semantic_level=semantic_level,
    )
    path = layout["generations"] / f"{base_name}.json"
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    try:
        return normalize_generation(
            payload=payload,
            artifact_id=artifact_id,
            arm=arm,
            input_condition=input_condition,
            semantic_level=semantic_level,
        )
    except ValueError:
        return None


def _persist_generation_outputs(
    generation: Any,
    gold: Any,
    layout: dict[str, Path],
    artifact_scores: list[Any],
) -> None:
    base_name = _generation_base_name(generation)
    write_json(
        layout["generations"] / f"{base_name}.json",
        generation.to_dict(),
    )
    if getattr(generation, "correction_trace", None) is not None:
        write_json(
            layout["arm_c_traces"] / f"{base_name}.json",
            generation.correction_trace.to_dict(),
        )
    write_json(
        layout["extracted_claims"] / f"{base_name}.json",
        {
            "artifact_id": generation.artifact_id,
            "arm": generation.arm,
            "input_condition": generation.input_condition,
            "semantic_level": generation.semantic_level,
            "claims": [claim.to_dict() for claim in generation.claims],
        },
    )
    verifications = verify_claims(
        gold=gold,
        claims=generation.claims,
        arm=generation.arm,
        input_condition=generation.input_condition,
        semantic_level=generation.semantic_level,
    )
    write_json(
        layout["verifications"] / f"{base_name}.json",
        {
            "artifact_id": generation.artifact_id,
            "arm": generation.arm,
            "input_condition": generation.input_condition,
            "semantic_level": generation.semantic_level,
            "verifications": [item.to_dict() for item in verifications],
        },
    )
    artifact_scores.append(
        compute_artifact_scores(
            gold=gold,
            claims=generation.claims,
            verifications=verifications,
            arm=generation.arm,
            input_condition=generation.input_condition,
            semantic_level=generation.semantic_level,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        bundle_path = _resolve_bundle_path(args.bundle_path, args.fixture_only)
        output_dir = Path(args.output_dir).expanduser().resolve()
        arms = _parse_csv_option(args.arms, SUPPORTED_ARMS, "--arms")
        conditions = _parse_csv_option(args.conditions, SUPPORTED_CONDITIONS, "--conditions")
        if "B" in arms:
            levels = _parse_csv_option(
                args.levels or DEFAULT_LEVELS,
                SUPPORTED_SEMANTIC_LEVELS,
                "--levels",
            )
        else:
            levels = []
    except (FileNotFoundError, ValueError) as exc:
        print(f"benchmarking error: {exc}", file=sys.stderr)
        return 2

    try:
        client = _build_llm_client(args.client)
        layout = ensure_output_layout(output_dir)
        with bundle_workspace(bundle_path) as workspace:
            effective_arms = list(arms)
            records = build_manifest(workspace.bundle_dir)
            gold_artifacts = build_gold_artifacts(workspace.bundle_dir, records)
            warnings = _warning_messages(records, conditions)
            requested_runs = _requested_runs(effective_arms, conditions, levels)
            expected_base_names = {
                _generation_base_name_for_run(
                    artifact_id=record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    semantic_level=semantic_level,
                )
                for record in records
                for arm, condition, semantic_level in requested_runs
            }

            if args.resume:
                _prune_unexpected_output_files(layout, expected_base_names)

            write_jsonl(
                layout["root"] / "manifest.jsonl",
                [record.to_dict() for record in records],
            )
            for gold_artifact in gold_artifacts:
                file_name = f"{slugify(gold_artifact.artifact_id)}.json"
                write_json(layout["gold"] / file_name, gold_artifact.to_dict())

            command = "run" if args.command == "export" else args.command
            generation_count = 0
            artifact_scores = []

            if command in {"run"}:
                gold_by_artifact = {gold.artifact_id: gold for gold in gold_artifacts}
                for record in records:
                    inputs = load_artifact_inputs(record, workspace.bundle_dir)
                    gold = gold_by_artifact[record.artifact_id]
                    generation_count += len(requested_runs)
                    generation_by_run: dict[tuple[str, str, str | None], Any] = {}
                    missing_non_b: dict[str, set[str]] = {}
                    missing_b: dict[str, set[str]] = {}

                    for arm, condition, semantic_level in requested_runs:
                        existing_generation = (
                            _load_existing_generation(
                                layout=layout,
                                artifact_id=record.artifact_id,
                                arm=arm,
                                input_condition=condition,
                                semantic_level=semantic_level,
                            )
                            if args.resume
                            else None
                        )
                        if existing_generation is not None:
                            generation_by_run[(arm, condition, semantic_level)] = existing_generation
                            continue

                        if arm == "B":
                            missing_b.setdefault(condition, set()).add(str(semantic_level))
                        else:
                            missing_non_b.setdefault(arm, set()).add(condition)

                    for arm, missing_conditions in missing_non_b.items():
                        if not missing_conditions:
                            continue
                        generated = generate_explanations(
                            inputs=inputs,
                            gold=gold,
                            arms=[arm],
                            conditions=[condition for condition in conditions if condition in missing_conditions],
                            client=client,
                            semantic_levels=levels,
                        )
                        for generation in generated:
                            generation_by_run[
                                (generation.arm, generation.input_condition, generation.semantic_level)
                            ] = generation

                    for condition, missing_levels in missing_b.items():
                        if not missing_levels:
                            continue
                        generated = generate_explanations(
                            inputs=inputs,
                            gold=gold,
                            arms=["B"],
                            conditions=[condition],
                            client=client,
                            semantic_levels=[level for level in levels if level in missing_levels],
                        )
                        for generation in generated:
                            generation_by_run[
                                (generation.arm, generation.input_condition, generation.semantic_level)
                            ] = generation

                    for run in requested_runs:
                        generation = generation_by_run.get(run)
                        if generation is None:
                            raise RuntimeError(
                                "Missing generation output for "
                                f"{record.artifact_id} / {run[0]} / {run[1]} / {run[2]}"
                            )
                        _persist_generation_outputs(
                            generation=generation,
                            gold=gold,
                            layout=layout,
                            artifact_scores=artifact_scores,
                        )

                leaderboard = build_leaderboard(artifact_scores)
                write_json(
                    layout["scores"] / "leaderboard.json",
                    {
                        "leaderboard": leaderboard,
                        "artifact_scores": [score.to_dict() for score in artifact_scores],
                    },
                )
                write_csv_rows(layout["scores"] / "leaderboard.csv", leaderboard)
                write_per_chart_benchmark_outputs(
                    layout["root"],
                    artifact_scores=artifact_scores,
                )

            write_json(
                layout["root"] / "run_metadata.json",
                _metadata_payload(
                    command=command,
                    bundle_path=bundle_path,
                    resolved_bundle_dir=workspace.bundle_dir,
                    output_dir=output_dir,
                    arms=effective_arms,
                    conditions=conditions,
                    levels=levels,
                    warnings=warnings,
                    manifest_count=len(records),
                    generation_count=generation_count,
                    client_metadata=client.metadata(),
                ),
            )
    except Exception as exc:  # noqa: BLE001
        print(f"benchmarking error: {exc}", file=sys.stderr)
        return 2

    return 0
