from __future__ import annotations

from pathlib import Path

from benchmarking.gold_builders import build_gold_artifacts
from benchmarking.manifest import build_manifest
from benchmarking.variable_catalog import build_variable_catalog


def test_variable_catalog_filters_by_semantic_level() -> None:
    bundle_dir = Path(__file__).resolve().parent / "fixtures" / "sample_bundle"
    records = build_manifest(bundle_dir)
    gold_artifacts = build_gold_artifacts(bundle_dir, records)
    gold = next(item for item in gold_artifacts if item.artifact_type == "model_comparison/main")

    l1_catalog = build_variable_catalog(gold, semantic_level="L1")
    l2l3_catalog = build_variable_catalog(gold, semantic_level="L2L3")
    full_catalog = build_variable_catalog(gold, semantic_level="L1L2L3")

    assert l1_catalog
    assert l2l3_catalog
    assert all(item["semantic_level"] == "L1" for item in l1_catalog)
    assert all(item["semantic_level"] == "L2L3" for item in l2l3_catalog)
    assert len(full_catalog) >= len(l1_catalog) + len(l2l3_catalog)
