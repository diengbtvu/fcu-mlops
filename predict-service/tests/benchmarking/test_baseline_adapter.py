from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from benchmarking.baseline_adapter import load_llm_baseline_generations
from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest
from benchmarking.metrics import compute_artifact_scores
from benchmarking.schemas import BASELINE_ARM
from benchmarking.verifier import verify_claims

FIXTURE_BUNDLE = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"


def test_baseline_adapter_loads_official_baseline_arm() -> None:
    records = build_manifest(FIXTURE_BUNDLE)
    generations, warnings = load_llm_baseline_generations(FIXTURE_BUNDLE, records)

    assert warnings == []
    assert len(generations) == len(records)
    assert {generation.arm for generation in generations} == {BASELINE_ARM}
    assert {generation.artifact_id for generation in generations} == {
        record.artifact_id for record in records
    }


def test_baseline_adapter_produces_verifiable_claims() -> None:
    records = build_manifest(FIXTURE_BUNDLE)
    gold_by_artifact = {
        gold.artifact_id: gold
        for gold in build_gold_artifacts(FIXTURE_BUNDLE, records)
    }
    generations, _warnings = load_llm_baseline_generations(FIXTURE_BUNDLE, records)
    target_artifacts = {
        "model_comparison/main",
        "incremental_feature_analysis/main",
        "feature_ranking/gra",
    }

    for generation in generations:
        assert generation.explanation_short
        assert generation.explanation_full
        gold = gold_by_artifact[generation.artifact_id]
        verifications = verify_claims(
            gold=gold,
            claims=generation.claims,
            arm=generation.arm,
            input_condition=generation.input_condition,
        )
        score = compute_artifact_scores(
            gold=gold,
            claims=generation.claims,
            verifications=verifications,
            arm=generation.arm,
            input_condition=generation.input_condition,
        )
        if generation.artifact_id in target_artifacts:
            assert any(item.status == "supported" for item in verifications)
            assert score.metrics["fact_precision"] > 0.0


def test_baseline_adapter_rejects_legacy_unstructured_payload(tmp_path: Path) -> None:
    bundle_copy = tmp_path / "bundle"
    shutil.copytree(FIXTURE_BUNDLE, bundle_copy)
    payload = json.loads((bundle_copy / "llm_explanations.json").read_text(encoding="utf-8"))
    del payload["assets"]["fig5_model_comparison"]["benchmark_payload"]
    (bundle_copy / "llm_explanations.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    records = build_manifest(bundle_copy)

    with pytest.raises(ValueError, match="benchmark_payload"):
        load_llm_baseline_generations(bundle_copy, records)
