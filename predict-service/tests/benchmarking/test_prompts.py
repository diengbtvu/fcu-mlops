from __future__ import annotations

from pathlib import Path

from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest, load_artifact_inputs
from benchmarking.prompts import (
    build_arm_c_corrector_prompt,
    build_arm_c_draft_prompt,
    build_arm_c_validator_prompt,
    build_claim_extraction_prompt,
    build_explanation_prompt,
    build_variable_mention_extraction_prompt,
)
from benchmarking.variable_catalog import build_variable_catalog


def test_prompt_contains_semantic_level_prefix_for_arm_b() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    prompt = build_explanation_prompt(
        inputs=inputs,
        arm="B",
        condition="table_only",
        semantic_level="L1",
    )

    assert "SEMANTIC LEVEL: L1" in prompt
    assert '"semantic_level": "L1"' in prompt


def test_prompt_omits_semantic_level_prefix_for_arm_a() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    prompt = build_explanation_prompt(
        inputs=inputs,
        arm="A",
        condition="table_only",
        semantic_level=None,
    )

    assert "SEMANTIC LEVEL:" not in prompt


def test_arm_c_draft_prompt_marks_draft_stage() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)

    prompt = build_arm_c_draft_prompt(inputs=inputs, condition="table_only")

    assert '"arm_c_stage": "draft"' in prompt
    assert "draft stage of a multi-step factual correction pipeline" in prompt


def test_arm_c_validator_prompt_contains_validation_payload() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    catalog = build_variable_catalog(gold_artifacts[0])

    prompt = build_arm_c_validator_prompt(
        artifact_id=inputs.record.artifact_id,
        input_condition="table_only",
        evidence_packet={"artifact_id": inputs.record.artifact_id, "allowed_variables": catalog[:1]},
        explanation_short="Draft short",
        explanation_full="Draft full",
        claims=[
            {
                "claim_id": "claim-1",
                "claim_text": "Claim one",
            }
        ],
        validation_pass="draft",
    )

    assert '"arm_c_stage": "validator"' in prompt
    assert '"claims"' in prompt
    assert '"validation_targets"' in prompt
    assert '"validation_pass": "draft"' in prompt
    assert "Validate each claim only against evidence_packet" in prompt
    assert "Do NOT trust claim.source_variable_id" in prompt
    assert "Do not rubber-stamp the draft" in prompt


def test_arm_c_corrector_prompt_contains_validation_payload() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    inputs = load_artifact_inputs(records[0], bundle_dir)
    catalog = build_variable_catalog(gold_artifacts[0])

    prompt = build_arm_c_corrector_prompt(
        artifact_id=inputs.record.artifact_id,
        input_condition="table_only",
        evidence_packet={"artifact_id": inputs.record.artifact_id, "allowed_variables": catalog[:1]},
        draft_explanation_short="Draft short",
        draft_explanation_full="Draft full",
        validation_records=[
            {
                "claim_id": "claim-1",
                "status": "contradicted",
                "recommended_action": "edit",
                "grounded_fact_summary": "KNN r2_score=0.920000",
            }
        ],
    )

    assert '"arm_c_stage": "corrector"' in prompt
    assert '"validation_records"' in prompt
    assert "Revise the draft explanation" in prompt


def test_claim_extraction_prompt_has_strict_json_contract() -> None:
    prompt = build_claim_extraction_prompt(
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
    )

    assert "JSON OUTPUT CONTRACT" in prompt
    assert "Do not put the answer in hidden thinking" in prompt
    assert "claims: []" in prompt


def test_variable_mention_prompt_separates_mentions_from_claim_schema() -> None:
    prompt = build_variable_mention_extraction_prompt(
        artifact_id="artifact-1",
        arm="C",
        input_condition="table_only",
        semantic_level=None,
        explanation_short="KNN is best.",
        explanation_full="KNN has the highest R2 score of 0.92.",
        primary_entities=["KNN"],
        variable_catalog=[
            {
                "source_variable_id": "artifact-1:model_comparison/main:metric:KNN:r2_score",
                "fact_type": "metric_value",
                "subject": "KNN",
                "predicate": "r2_score",
            }
        ],
    )

    assert "mentions" in prompt
    assert "source_variable_id" in prompt
    assert "Do not emit claim_type" in prompt
    assert "Do not convert rank positions into score values" in prompt
