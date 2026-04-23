from __future__ import annotations

from pathlib import Path

from benchmarking.llm_client import OllamaLLMClient
from benchmarking.variable_catalog import build_variable_catalog
from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest, load_artifact_inputs


def test_ollama_client_falls_back_to_failed_generation_payload_on_single_pair_errors() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    client = object.__new__(OllamaLLMClient)
    client.model_name = "stub-model"

    def _raise_batch(_: dict[str, object]) -> dict[str, object]:
        raise ValueError("batch parse failed")

    def _raise_single(_: str) -> dict[str, object]:
        raise ValueError("single parse failed")

    client._call_ollama = _raise_batch  # type: ignore[attr-defined]
    client.generate_explanation_json = _raise_single  # type: ignore[method-assign]
    client.extract_claims_json = _raise_single  # type: ignore[method-assign]

    outputs = OllamaLLMClient.generate_artifact(
        client,
        inputs=inputs,
        variable_catalog=build_variable_catalog(gold_artifacts[0]),
        arms=["A"],
        conditions=["image_table_summary"],
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output["artifact_id"] == inputs.record.artifact_id
    assert output["arm"] == "A"
    assert output["input_condition"] == "image_table_summary"
    assert output["claims"] == []
    assert "single parse failed" in output["explanation_full"]
