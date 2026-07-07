from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from benchmarking.arm_c_pipeline import build_arm_c_evidence_packet
from benchmarking.llm_client import FixtureLLMClient
from benchmarking.llm_client import GroqLLMClient
from benchmarking.llm_client import OLLAMA_BENCHMARK_JSON_NUM_PREDICT
from benchmarking.llm_client import OllamaLLMClient
from benchmarking.llm_client import _claim_schema
from benchmarking.llm_client import _variable_mention_schema
from benchmarking.prompts import (
    build_arm_c_draft_prompt,
    build_arm_c_validator_prompt,
    build_claim_extraction_prompt,
)
from benchmarking.variable_catalog import build_variable_catalog
from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest, load_artifact_inputs


def _anyof_type_sets(schema: object) -> list[set[str]]:
    type_sets: list[set[str]] = []
    if isinstance(schema, dict):
        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            types = {
                str(item.get("type"))
                for item in any_of
                if isinstance(item, dict) and isinstance(item.get("type"), str)
            }
            if types:
                type_sets.append(types)
        for value in schema.values():
            type_sets.extend(_anyof_type_sets(value))
    elif isinstance(schema, list):
        for item in schema:
            type_sets.extend(_anyof_type_sets(item))
    return type_sets


def test_benchmark_schemas_avoid_ambiguous_integer_number_unions() -> None:
    schemas = [_claim_schema(), _variable_mention_schema()]

    assert all(
        {"integer", "number"} - type_set
        for schema in schemas
        for type_set in _anyof_type_sets(schema)
    )


def test_groq_client_uses_inline_json_for_gpt_oss_model() -> None:
    client = object.__new__(GroqLLMClient)
    client.model_name = "openai/gpt-oss-120b"

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_claims",
            "schema": {
                "type": "object",
                "properties": {
                    "claims": {"type": "array"},
                },
                "required": ["claims"],
            },
        },
    }
    payload = {
        "model": "placeholder",
        "messages": [{"role": "system", "content": "Return JSON only."}],
        "response_format": response_format,
        "reasoning_effort": "low",
        "verbosity": "low",
    }

    prepared = GroqLLMClient._prepare_groq_payload(client, payload)

    assert "response_format" not in prepared
    assert prepared["reasoning_effort"] == "low"
    assert "verbosity" not in prepared
    assert prepared["temperature"] == 0
    assert "The JSON must exactly match this schema" in prepared["messages"][0]["content"]


def test_groq_client_uses_inline_json_for_llama_model() -> None:
    client = object.__new__(GroqLLMClient)
    client.model_name = "llama-3.3-70b-versatile"

    payload = {
        "model": "placeholder",
        "messages": [{"role": "system", "content": "Return JSON only."}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "benchmark_claims",
                "schema": {
                    "type": "object",
                    "properties": {
                        "artifact_id": {"type": "string"},
                        "claims": {"type": "array"},
                    },
                    "required": ["artifact_id", "claims"],
                },
            },
        },
        "reasoning_effort": "low",
        "verbosity": "low",
    }

    prepared = GroqLLMClient._prepare_groq_payload(client, payload)

    assert "response_format" not in prepared
    assert "reasoning_effort" not in prepared
    assert "verbosity" not in prepared
    assert prepared["temperature"] == 0
    assert "The JSON must exactly match this schema" in prepared["messages"][0]["content"]


def test_groq_client_call_posts_to_openai_compatible_endpoint(monkeypatch) -> None:
    client = object.__new__(GroqLLMClient)
    client.api_key = "test-key"
    client.model_name = "llama-3.3-70b-versatile"
    client.timeout_seconds = 60
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"artifact_id":"artifact-1","arm":"C",'
                                '"input_condition":"table_only","semantic_level":null,"claims":[]}'
                            )
                        }
                    }
                ]
            }

    def fake_post(url: str, **kwargs: object) -> Response:
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr("benchmarking.llm_client.GROQ_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS", 0)

    class Gate:
        @contextmanager
        def request_slot(self, _min_interval_seconds: float, _jitter_seconds: float = 0.0):
            yield

        def push_cooldown(self, _delay_seconds: float) -> None:
            return None

    monkeypatch.setattr("benchmarking.llm_client.shared_openai_request_gate", lambda: Gate())

    response = GroqLLMClient._call_openai(
        client,
        {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": "Return JSON only."}],
            "response_format": {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}},
            "reasoning_effort": "low",
            "verbosity": "low",
        },
    )

    assert response["artifact_id"] == "artifact-1"
    assert str(captured["url"]).endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"  # type: ignore[index]
    assert "response_format" not in captured["json"]  # type: ignore[operator]


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
        arms=["A"],
        conditions=["image_table_summary"],
        semantic_levels=["L1", "L2L3", "L1L2L3"],
        variable_catalog_by_level={
            None: build_variable_catalog(gold_artifacts[0]),
            "L1": build_variable_catalog(gold_artifacts[0], semantic_level="L1"),
            "L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L2L3"),
            "L1L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L1L2L3"),
        },
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output["artifact_id"] == inputs.record.artifact_id
    assert output["arm"] == "A"
    assert output["input_condition"] == "image_table_summary"
    assert output["claims"] == []
    assert "single parse failed" in output["explanation_full"]


def test_ollama_claim_extraction_uses_hardened_json_payload() -> None:
    client = object.__new__(OllamaLLMClient)
    client.model_name = "stub-model"
    client.timeout_seconds = 60
    captured_payload: dict[str, object] = {}

    def _capture(payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update(payload)
        return {
            "artifact_id": "artifact-1",
            "arm": "C",
            "input_condition": "table_only",
            "semantic_level": None,
            "claims": [],
        }

    client._call_ollama = _capture  # type: ignore[attr-defined]

    response = OllamaLLMClient.extract_claims_json(
        client,
        build_claim_extraction_prompt(
            artifact_id="artifact-1",
            arm="C",
            input_condition="table_only",
            semantic_level=None,
            explanation_short="KNN is best.",
            explanation_full="KNN has the highest R2.",
            primary_entities=["KNN"],
            variable_catalog=[
                {
                    "source_variable_id": "artifact-1:model_comparison/main:best_model",
                    "fact_type": "best_model",
                    "subject": "KNN",
                }
            ],
        ),
    )

    assert response["claims"] == []
    assert (captured_payload["options"] or {})["num_predict"] >= OLLAMA_BENCHMARK_JSON_NUM_PREDICT
    assert "hidden thinking field" in captured_payload["messages"][0]["content"]


def test_fixture_client_l1_output_is_structural_only() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    client = FixtureLLMClient()

    outputs = client.generate_artifact(
        inputs=inputs,
        arms=["B"],
        conditions=["table_only"],
        semantic_levels=["L1"],
        variable_catalog_by_level={
            None: build_variable_catalog(gold_artifacts[0]),
            "L1": build_variable_catalog(gold_artifacts[0], semantic_level="L1"),
            "L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L2L3"),
            "L1L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L1L2L3"),
        },
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output["semantic_level"] == "L1"
    assert "model comparison table" in output["explanation_short"].lower()
    assert {claim["claim_type"] for claim in output["claims"]} <= {"metric_value", "rank_score"}


def test_fixture_client_l2l3_output_is_analytical_only() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    client = FixtureLLMClient()

    outputs = client.generate_artifact(
        inputs=inputs,
        arms=["B"],
        conditions=["table_only"],
        semantic_levels=["L2L3"],
        variable_catalog_by_level={
            None: build_variable_catalog(gold_artifacts[0]),
            "L1": build_variable_catalog(gold_artifacts[0], semantic_level="L1"),
            "L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L2L3"),
            "L1L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L1L2L3"),
        },
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output["semantic_level"] == "L2L3"
    assert {claim["claim_type"] for claim in output["claims"]} <= {
        "best_model",
        "ranking",
        "top_feature",
        "feature_subset_optimum",
        "plateau",
    }


def test_fixture_client_l1l2l3_output_contains_both_levels() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    client = FixtureLLMClient()

    outputs = client.generate_artifact(
        inputs=inputs,
        arms=["B"],
        conditions=["table_only"],
        semantic_levels=["L1L2L3"],
        variable_catalog_by_level={
            None: build_variable_catalog(gold_artifacts[0]),
            "L1": build_variable_catalog(gold_artifacts[0], semantic_level="L1"),
            "L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L2L3"),
            "L1L2L3": build_variable_catalog(gold_artifacts[0], semantic_level="L1L2L3"),
        },
    )

    output = outputs[0]
    claim_types = {claim["claim_type"] for claim in output["claims"]}
    assert output["semantic_level"] == "L1L2L3"
    assert "model comparison table" in output["explanation_full"].lower()
    assert "metric_value" in claim_types
    assert "best_model" in claim_types


def test_fixture_client_arm_c_validator_marks_draft_error_for_edit() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    gold = gold_artifacts[0]
    client = FixtureLLMClient()
    variable_catalog = build_variable_catalog(gold)

    draft_explanation = client.generate_explanation_json(
        build_arm_c_draft_prompt(
            inputs=inputs,
            condition="table_only",
        )
    )
    draft_claims = client.extract_claims_json(
        build_claim_extraction_prompt(
            artifact_id=inputs.record.artifact_id,
            arm="C",
            input_condition="table_only",
            semantic_level=None,
            explanation_short=str(draft_explanation.get("explanation_short") or ""),
            explanation_full=str(draft_explanation.get("explanation_full") or ""),
            primary_entities=inputs.record.primary_entities,
            variable_catalog=variable_catalog,
        )
    )
    validation_payload = client.validate_arm_c_json(
        build_arm_c_validator_prompt(
            artifact_id=inputs.record.artifact_id,
            input_condition="table_only",
            evidence_packet=build_arm_c_evidence_packet(
                inputs=inputs,
                gold=gold,
                input_condition="table_only",
                variable_catalog=variable_catalog,
            ),
            explanation_short=str(draft_explanation.get("explanation_short") or ""),
            explanation_full=str(draft_explanation.get("explanation_full") or ""),
            claims=list(draft_claims.get("claims") or []),
            validation_pass="draft",
        )
    )

    records_payload = list(validation_payload.get("validation_records") or [])
    assert records_payload
    assert any(item["recommended_action"] == "edit" for item in records_payload)
    assert any(item["status"] == "contradicted" for item in records_payload)
