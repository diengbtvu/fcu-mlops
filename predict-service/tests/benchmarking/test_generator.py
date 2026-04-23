from __future__ import annotations

from pathlib import Path

from benchmarking.generator import generate_explanations
from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest, load_artifact_inputs


class _BlankMetadataClient:
    def generate_artifact(self, inputs, variable_catalog, arms, conditions):  # type: ignore[no-untyped-def]
        assert variable_catalog
        rows = []
        for _arm in arms:
            for _condition in conditions:
                rows.append(
                    {
                        "artifact_id": "",
                        "arm": "",
                        "input_condition": "",
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

    assert len(outputs) == 2
    assert outputs[0].artifact_id == inputs.record.artifact_id
    assert outputs[0].arm == "A"
    assert outputs[0].input_condition == "image_table_summary"
    assert outputs[1].arm == "B"
    assert outputs[1].input_condition == "image_table_summary"
