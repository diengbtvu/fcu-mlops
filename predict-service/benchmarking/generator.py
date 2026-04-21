from __future__ import annotations

from .claim_extractor import normalize_generation
from .llm_client import BaseLLMClient
from .schemas import ArtifactInputs, ExplanationOutput


def generate_explanations(
    inputs: ArtifactInputs,
    arms: list[str],
    conditions: list[str],
    client: BaseLLMClient,
) -> list[ExplanationOutput]:
    raw_generations = client.generate_artifact(inputs=inputs, arms=arms, conditions=conditions)
    return [
        normalize_generation(
            payload=raw_payload,
            artifact_id=inputs.record.artifact_id,
            arm=str(raw_payload.get("arm") or ""),
            input_condition=str(raw_payload.get("input_condition") or ""),
        )
        for raw_payload in raw_generations
    ]
