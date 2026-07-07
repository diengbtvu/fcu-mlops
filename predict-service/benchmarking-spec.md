# SPEC — Offline Benchmarking Module for Artifact-Grounded Explanations
Version: v1
Owner: predict-service side
Status: Phase 1 implementation

## 1. Goal

Add an offline benchmarking module to the Python side of the repository so we can evaluate LLM-generated explanations for post-training ML artifacts.

This module is for research/evaluation only.
It must NOT change the existing web app behavior, existing Flask prediction runtime, or existing database flows.

The benchmark target is:
- generate faithful and useful explanations for post-training artifacts
- compare multiple prompting/protocol styles
- score explanations at claim level

## 2. Scope

### In scope for Phase 1
Implement a minimal but production-clean benchmarking package that can:

1. Read an extracted artifact bundle directory or a zip bundle.
2. Build a manifest of artifact units.
3. Build machine-checkable gold facts from table/json files.
4. Generate explanations for benchmark arms:
   - Arm A: direct chart-to-text
   - Arm B: VisText-style layered explanation
   - Arm C: CHOCOLATE-style generate + self-correction
5. Provide a scaffold for Arm D:
   - prompt builder + schema support only
   - full dense scoring can come later
6. Extract or normalize claims from model outputs.
7. Verify claims against gold facts using rule-based verification first.
8. Compute benchmark metrics and output leaderboard files.
9. Run from CLI without requiring any web UI.

### Out of scope for Phase 1
Do NOT implement:
- Laravel UI integration
- new Flask HTTP endpoints
- database tables/migrations for benchmark runs
- OCR-heavy chart parsing
- image regeneration or advanced VCS image reconstruction
- broad refactors of existing app code
- changes to `/predict/model` or `/predict/health`

## 3. Core Grounding Rules

The module must enforce these rules:

1. Source-of-truth priority:
   - primary: table/json
   - secondary: chart image
   - tertiary: summary text
2. `llm_explanations.json` is not ingested as a benchmark arm and is never gold truth.
3. Unsupported claims must be penalized heavily.
4. Omission is better than speculation.
5. Claim-level evaluation is mandatory.
6. Text-overlap metrics are not primary metrics.

## 4. Placement in Repository

All new benchmark code must live on the Python side and remain isolated from runtime inference code.

Preferred new paths:

predict-service/
├── benchmarking/
│   ├── __init__.py
│   ├── schemas.py
│   ├── manifest.py
│   ├── gold_builders.py
│   ├── prompts.py
│   ├── llm_client.py
│   ├── generator.py
│   ├── claim_extractor.py
│   ├── verifier.py
│   ├── metrics.py
│   ├── io_utils.py
│   └── cli.py
├── scripts/
│   └── run_benchmark.py
├── tests/
│   └── benchmarking/
│       ├── fixtures/
│       ├── test_manifest.py
│       ├── test_gold_builders.py
│       ├── test_verifier.py
│       └── test_metrics.py
└── docs/
    └── benchmarking-spec.md

If the repo already has a Python test layout or scripts layout, reuse it conservatively instead of forcing this exact tree.

## 5. Architectural Decisions

### 5.1 Keep benchmark additive
Implementation must be additive. Avoid modifying existing Flask app runtime unless there is a very small import-path fix required.

### 5.2 Provider-agnostic LLM interface
Create an abstract client interface so benchmark logic is separate from vendor APIs.

Required:
- `BaseLLMClient.generate_json(prompt: str) -> dict`
- `FixtureLLMClient` or `DummyLLMClient` for local tests without credentials

Optional:
- real provider client if current repo already has safe infrastructure for it

### 5.3 Typed, testable modules
Use:
- Python typing
- small pure functions where possible
- dataclasses or pydantic models
- explicit exceptions with readable messages

Prefer standard library + existing dependencies.
Add new dependencies only if clearly justified.

## 6. Phase 1 Artifact Units

Implement these 3 unit types first:

1. `model_comparison/main`
   Inputs:
   - `table_model_comparison.csv`
   - `summary.json`
   - optional chart image
   Gold facts:
   - best_model
   - metric_value per model
   - model_ranking
   - pairwise_metric_gap

2. `incremental_feature_analysis/main`
   Inputs:
   - `table1_incremental_results.csv`
   - optional chart image
   - optional results summary
   Gold facts:
   - feature_subset_optimum
   - best_r2
   - best_mse
   - plateau

3. `feature_ranking/gra`
   Inputs:
   - `gra_ranking.json`
   - optional feature chart
   Gold facts:
   - top_feature
   - rank ordering
   - rank scores

Everything else should be left for future phases.

## 7. Data Contracts

### 7.1 Manifest record
Each artifact unit must serialize to JSONL with fields at least:

- artifact_id
- artifact_type
- chart_type
- source_files
- primary_entities

### 7.2 Gold schema
Need a normalized schema with fields at least:

- artifact_id
- artifact_type
- source_files
- chart_type
- primary_entities
- ground_truth_facts[]
  - fact_id
  - fact_type
  - subject
  - predicate
  - object
  - value
  - unit
  - evidence[]
  - importance
- salient_facts[]
- forbidden_inferences[]

### 7.3 Explanation output schema
All arms must output the same schema:

- artifact_id
- arm
- input_condition
- explanation_short
- explanation_full
- claims[]

Each claim should include:
- claim_id
- claim_text
- claim_type
- span_category
- is_numeric
- requires_grounding_from
- confidence

## 8. Input Conditions

Phase 1 required conditions:
- `table_only`
- `image_table`
- `image_table_summary`

Optional scaffold:
- `image_only`

If multimodal image handling is not stable in the existing environment, implement the condition flags first and keep image handling conservative.

## 9. Metrics for Phase 1

Implement these first:

1. Fact Precision
2. Fact Recall
3. Fact F1
4. Unsupported Claim Rate
5. Contradiction Rate
6. Coverage of Salient Facts

Recommended if easy:
7. Numeric Accuracy
8. Numeric Tolerance Accuracy

Do not block Phase 1 on full VCS-style scoring.
Just prepare architecture so later metrics can be added.

## 10. Verification Strategy

Phase 1 verifier must be rule-based first.

Implement support for:
- metric_value
- ranking
- top_feature
- feature_subset_optimum
- plateau

Statuses:
- supported
- partially_supported
- contradicted
- unverifiable

Rules:
- numeric mismatch => contradicted
- approximate near-match => partially_supported if hedged
- missing evidence => unverifiable
- summary text cannot override table/json

## 11. CLI Requirements

Provide a CLI runnable from `predict-service`.

Minimum supported usage:

- build manifest
- build gold
- run benchmark
- export results

Examples:
- `python scripts/run_benchmark.py --bundle-path <path> --output-dir <dir>`
- `python scripts/run_benchmark.py --bundle-path <path> --output-dir <dir> --arms A,B,C --conditions table_only,image_table,image_table_summary`

CLI must:
- create output directories if missing
- fail clearly on missing files
- write run metadata
- support dummy/fixture client mode

## 12. Outputs

Each run should write:

<output_dir>/
├── manifest.jsonl
├── gold/
│   └── *.json
├── generations/
│   └── *.json
├── extracted_claims/
│   └── *.json
├── verifications/
│   └── *.json
├── scores/
│   ├── leaderboard.json
│   └── leaderboard.csv
└── run_metadata.json

## 13. Documentation

Add a short benchmark README section that explains:
- purpose
- how to run locally
- current scope
- limitations
- how to add new artifact unit types later

Do not rewrite the whole repo README.
Prefer adding:
- `predict-service/docs/benchmarking-spec.md`
- a short section in `predict-service/README.md` if appropriate

## 14. Testing Requirements

Before considering Phase 1 done, add tests for:

1. Gold builder:
   - parses model comparison fixture correctly
   - extracts best model and key metrics
2. Incremental analysis:
   - detects best feature count and plateau fact
3. Feature ranking:
   - extracts top ranked features correctly
4. Verifier:
   - supported numeric claim
   - contradicted numeric claim
   - supported ranking claim
   - unsupported claim
5. Metrics:
   - fact precision / recall / f1
   - unsupported rate
   - contradiction rate

Use tiny synthetic fixtures under tests.
Do not depend on large real artifact bundles in CI.

If the repo already uses `pytest`, continue with it.
If not, use the lightest existing Python test convention in the repo.

## 15. Acceptance Criteria

Phase 1 is complete only when all are true:

1. New benchmark code is isolated to Python side.
2. Existing Flask prediction runtime still works unchanged.
3. CLI runs successfully in fixture mode without external API credentials.
4. Manifest + gold + generations + verifications + scores are emitted.
5. Tests pass.
6. Docs are added.
7. No unrelated refactors were introduced.

## 16. Coding Guardrails

- Prefer additive changes over edits to core runtime.
- Keep functions small and typed.
- Avoid clever abstractions too early.
- Do not guess hidden repo structure; inspect before editing.
- If an existing file layout differs from this spec, adapt conservatively and document the difference.
- Keep logs readable.
- Do not hardcode secrets or provider tokens.
- Do not make Laravel changes in this phase.
