from __future__ import annotations

from .arm_c_pipeline import run_arm_c_pipeline
from .claim_extractor import normalize_generation
from .llm_client import BaseLLMClient
from .schemas import ArtifactInputs, ExplanationOutput, GoldArtifact, SUPPORTED_SEMANTIC_LEVELS
from .variable_catalog import build_variable_catalog


def generate_explanations(
    inputs: ArtifactInputs,
    gold: GoldArtifact,
    arms: list[str],
    conditions: list[str],
    client: BaseLLMClient,
    semantic_levels: list[str] | None = None,
) -> list[ExplanationOutput]:
    effective_semantic_levels = list(semantic_levels or SUPPORTED_SEMANTIC_LEVELS)
    variable_catalog_by_level = {
        None: build_variable_catalog(gold),
        "L1": build_variable_catalog(gold, semantic_level="L1"),
        "L2L3": build_variable_catalog(gold, semantic_level="L2L3"),
        "L1L2L3": build_variable_catalog(gold, semantic_level="L1L2L3"),
    }
    requested_runs: list[tuple[str, str, str | None]] = []
    for arm in arms:
        for condition in conditions:
            if arm == "B":
                for semantic_level in effective_semantic_levels:
                    requested_runs.append((arm, condition, semantic_level))
            else:
                requested_runs.append((arm, condition, None))
    outputs_by_run: dict[tuple[str, str, str | None], ExplanationOutput] = {}

    regular_arms = [arm for arm in arms if arm != "C"]
    if regular_arms:
        raw_generations = client.generate_artifact(
            inputs=inputs,
            arms=regular_arms,
            conditions=conditions,
            semantic_levels=effective_semantic_levels,
            variable_catalog_by_level=variable_catalog_by_level,
        )
        regular_runs = [run for run in requested_runs if run[0] != "C"]
        for index, raw_payload in enumerate(raw_generations):
            fallback_arm = ""
            fallback_condition = ""
            fallback_semantic_level = None
            if index < len(regular_runs):
                fallback_arm, fallback_condition, fallback_semantic_level = regular_runs[index]

            normalized = normalize_generation(
                payload=raw_payload,
                artifact_id=inputs.record.artifact_id,
                arm=fallback_arm,
                input_condition=fallback_condition,
                semantic_level=fallback_semantic_level,
            )
            outputs_by_run[(normalized.arm, normalized.input_condition, normalized.semantic_level)] = normalized

    if "C" in arms:
        for condition in conditions:
            outputs_by_run[("C", condition, None)] = run_arm_c_pipeline(
                inputs=inputs,
                gold=gold,
                input_condition=condition,
                client=client,
                variable_catalog=variable_catalog_by_level[None],
            )

    missing_runs = [run for run in requested_runs if run not in outputs_by_run]
    if missing_runs:
        raise RuntimeError(f"Missing benchmark generations for runs: {missing_runs}")

    return [outputs_by_run[run] for run in requested_runs]
