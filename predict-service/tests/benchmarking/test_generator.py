from __future__ import annotations

from pathlib import Path

from benchmarking.generator import generate_explanations
from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.llm_client import FixtureLLMClient
from benchmarking.manifest import build_manifest, load_artifact_inputs
from benchmarking.schemas import ArtifactInputs


class _BlankMetadataClient:
    def generate_artifact(  # type: ignore[no-untyped-def]
        self,
        inputs,
        arms,
        conditions,
        semantic_levels,
        variable_catalog_by_level,
    ):
        assert variable_catalog_by_level
        rows = []
        effective_levels = semantic_levels or []
        for _arm in arms:
            for _condition in conditions:
                run_levels = effective_levels if _arm == "B" else [None]
                for semantic_level in run_levels:
                    rows.append(
                        {
                            "artifact_id": "",
                            "arm": "",
                            "input_condition": "",
                            "semantic_level": semantic_level,
                            "explanation_short": "stub",
                            "explanation_full": "stub",
                            "claims": [
                                {
                                    "claim_id": "claim-1",
                                    "claim_text": "stub",
                                    "claim_type": "freeform",
                                    "span_category": "sentence",
                                    "is_numeric": False,
                                    "requires_grounding_from": "table/json",
                                    "confidence": 0.0,
                                    "source_variable_id": None,
                                    "subject": None,
                                    "predicate": None,
                                    "object": None,
                                    "metric": None,
                                    "value": None,
                                    "unit": None,
                                    "ordered_items": [],
                                    "feature_count": None,
                                    "hedged": False,
                                }
                            ],
                        }
                    )
        return rows


def test_generate_explanations_backfills_requested_arm_and_condition() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    outputs = generate_explanations(
        inputs=inputs,
        gold=gold_artifacts[0],
        arms=["A", "B"],
        conditions=["image_table_summary"],
        client=_BlankMetadataClient(),
    )

    assert len(outputs) == 4
    assert outputs[0].artifact_id == inputs.record.artifact_id
    assert outputs[0].arm == "A"
    assert outputs[0].input_condition == "image_table_summary"
    assert outputs[0].semantic_level is None
    assert outputs[1].arm == "B"
    assert outputs[1].input_condition == "image_table_summary"
    assert outputs[1].semantic_level == "L1"
    assert outputs[2].semantic_level == "L2L3"
    assert outputs[3].semantic_level == "L1L2L3"


def test_generate_explanations_runs_arm_c_correction_pipeline() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    outputs = generate_explanations(
        inputs=inputs,
        gold=gold_artifacts[0],
        arms=["C"],
        conditions=["table_only"],
        client=FixtureLLMClient(),
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output.arm == "C"
    assert output.input_condition == "table_only"
    assert output.generation_stage == "corrected"
    assert output.correction_trace is not None
    assert output.parent_draft_hash is not None

    iteration = output.correction_trace.iterations[0]
    assert any(item.status == "contradicted" for item in iteration.draft_validations)
    assert any(item.recommended_action == "edit" for item in iteration.draft_validations)
    assert all(item.status != "contradicted" for item in iteration.corrected_validations)


class _ArmCVariableMentionClient:
    source_variable_id = "fixture_bundle:model_comparison/main:metric:KNN:r2_score"

    def generate_explanation_json(self, prompt: str) -> dict[str, object]:
        return {
            "artifact_id": "fixture_bundle:model_comparison/main",
            "arm": "C",
            "input_condition": "table_only",
            "semantic_level": None,
            "explanation_short": "KNN achieved R2 score of 0.70.",
            "explanation_full": "KNN achieved R2 score of 0.70.",
        }

    def extract_variable_mentions_json(self, prompt: str) -> dict[str, object]:
        value = 0.92 if "0.92" in prompt else 0.70
        return {
            "artifact_id": "fixture_bundle:model_comparison/main",
            "arm": "C",
            "input_condition": "table_only",
            "semantic_level": None,
            "mentions": [
                {
                    "mention_id": "mention-1",
                    "source_variable_id": self.source_variable_id,
                    "evidence_span": f"KNN achieved R2 score of {value}.",
                    "stated_value": value,
                    "stated_object": None,
                    "stated_ordered_items": [],
                    "stated_feature_count": None,
                    "confidence": 1.0,
                }
            ],
        }

    def validate_arm_c_json(self, prompt: str) -> dict[str, object]:
        from benchmarking.prompts import extract_prompt_context

        context = extract_prompt_context(prompt)
        claims = list(context.get("claims") or [])
        supported = any(isinstance(claim, dict) and claim.get("value") == 0.92 for claim in claims)
        return {
            "artifact_id": "fixture_bundle:model_comparison/main",
            "arm": "C",
            "input_condition": "table_only",
            "validation_records": [
                {
                    "claim_id": "claim-1",
                    "claim_text": "KNN achieved R2 score.",
                    "status": "supported" if supported else "contradicted",
                    "recommended_action": "keep" if supported else "edit",
                    "rationale": "Fixture validator response.",
                    "matched_fact_ids": [self.source_variable_id],
                    "grounded_fact_summary": "KNN r2_score=0.920000.",
                }
            ],
        }

    def correct_arm_c_json(self, prompt: str) -> dict[str, object]:
        return {
            "artifact_id": "fixture_bundle:model_comparison/main",
            "arm": "C",
            "input_condition": "table_only",
            "semantic_level": None,
            "explanation_short": "KNN achieved R2 score of 0.92.",
            "explanation_full": "KNN achieved R2 score of 0.92.",
            "claims": [
                {
                    "claim_id": "malicious-embedded-claim",
                    "claim_text": "The best subset uses 5 features.",
                    "claim_type": "feature_subset_optimum",
                    "source_variable_id": "fixture_bundle:model_comparison/main:metric:KNN:r2_score",
                    "feature_count": 5,
                }
            ],
        }


def test_arm_c_reextracts_claims_from_corrected_text_and_ignores_embedded_claims() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    outputs = generate_explanations(
        inputs=inputs,
        gold=gold_artifacts[0],
        arms=["C"],
        conditions=["table_only"],
        client=_ArmCVariableMentionClient(),
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output.generation_stage == "corrected"
    assert len(output.claims) == 1
    assert output.claims[0].claim_type == "metric_value"
    assert output.claims[0].source_variable_id == _ArmCVariableMentionClient.source_variable_id
    assert output.claims[0].value == 0.92
    assert output.claims[0].feature_count is None
    assert output.extracted_variable_mentions


class _ArmCDraftOnlyClient:
    def __init__(self) -> None:
        self.corrector_calls = 0

    def generate_explanation_json(self, prompt: str) -> dict[str, object]:
        if '"arm_c_stage": "corrector"' in prompt:
            self.corrector_calls += 1
            raise AssertionError("corrector should not be called when draft is already supported")
        return {
            "artifact_id": "fixture_bundle_feature_ranking_gra",
            "arm": "C",
            "input_condition": "table_only",
            "semantic_level": None,
            "explanation_short": "VFA is the top ranked feature.",
            "explanation_full": "VFA is the top ranked feature, followed by Butyrate and Acetate.",
        }

    def extract_claims_json(self, prompt: str) -> dict[str, object]:
        return {
            "artifact_id": "fixture_bundle_feature_ranking_gra",
            "arm": "C",
            "input_condition": "table_only",
            "semantic_level": None,
            "claims": [
                {
                    "claim_id": "claim_1",
                    "claim_text": "VFA is the top ranked feature",
                    "claim_type": "top_feature",
                    "span_category": "feature_name",
                    "is_numeric": False,
                    "requires_grounding_from": "explanation_full",
                    "confidence": 1.0,
                    "source_variable_id": "fixture_bundle:feature_ranking/gra:top_feature",
                    "subject": "gra",
                    "predicate": "top_feature",
                    "object": "VFA",
                    "metric": None,
                    "value": None,
                    "unit": None,
                    "ordered_items": [],
                    "feature_count": None,
                    "hedged": False,
                }
            ],
        }

    def validate_arm_c_json(self, prompt: str) -> dict[str, object]:
        return {
            "artifact_id": "fixture_bundle_feature_ranking_gra",
            "arm": "C",
            "input_condition": "table_only",
            "validation_records": [
                {
                    "claim_id": "claim_1",
                    "claim_text": "VFA is the top ranked feature",
                    "status": "supported",
                    "recommended_action": "keep",
                    "rationale": "Supported by the evidence packet.",
                    "matched_fact_ids": ["fixture_bundle:feature_ranking/gra:top_feature"],
                    "grounded_fact_summary": "VFA is the highest-ranked feature.",
                }
            ],
        }


def test_generate_explanations_skips_arm_c_corrector_when_draft_is_supported() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    gra_index = next(
        index for index, record in enumerate(records) if record.artifact_id == "fixture_bundle:feature_ranking/gra"
    )
    inputs = load_artifact_inputs(records[gra_index], bundle_dir)
    client = _ArmCDraftOnlyClient()

    outputs = generate_explanations(
        inputs=inputs,
        gold=gold_artifacts[gra_index],
        arms=["C"],
        conditions=["table_only"],
        client=client,
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert output.generation_stage == "draft"
    assert output.correction_trace is not None
    assert output.correction_trace.selected_generation_stage == "draft"
    assert client.corrector_calls == 0


class _ArmCFlakyValidatorClient(FixtureLLMClient):
    def __init__(self) -> None:
        super().__init__()
        self.validator_attempts = 0

    def validate_arm_c_json(self, prompt: str) -> dict[str, object]:
        self.validator_attempts += 1
        if self.validator_attempts == 1:
            raise ValueError("Ollama benchmark response returned empty content.")
        return super().validate_arm_c_json(prompt)


def test_generate_explanations_retries_arm_c_validator_stage() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    client = _ArmCFlakyValidatorClient()

    outputs = generate_explanations(
        inputs=inputs,
        gold=gold_artifacts[0],
        arms=["C"],
        conditions=["table_only"],
        client=client,
    )

    assert len(outputs) == 1
    output = outputs[0]
    assert client.validator_attempts >= 2
    assert output.generation_stage == "corrected"
