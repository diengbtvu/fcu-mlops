from __future__ import annotations

from .claim_extractor import normalize_generation
from .llm_client import BaseLLMClient
from .schemas import ArtifactInputs, ExplanationOutput, GoldArtifact
from .variable_catalog import build_variable_catalog


def generate_explanations(
    inputs: ArtifactInputs,
    gold: GoldArtifact,
    arms: list[str],
    conditions: list[str],
    client: BaseLLMClient,
) -> list[ExplanationOutput]:
    raw_generations = client.generate_artifact(
        inputs=inputs,
        variable_catalog=build_variable_catalog(gold),
        arms=arms,
        conditions=conditions,
    )
    requested_pairs = [(arm, condition) for arm in arms for condition in conditions]
    outputs: list[ExplanationOutput] = []

    for index, raw_payload in enumerate(raw_generations):
        fallback_arm = ""
        fallback_condition = ""
        if index < len(requested_pairs):
            fallback_arm, fallback_condition = requested_pairs[index]

        outputs.append(
            normalize_generation(
                payload=raw_payload,
                artifact_id=inputs.record.artifact_id,
                arm=fallback_arm,
                input_condition=fallback_condition,
            )
        )

    return outputs
