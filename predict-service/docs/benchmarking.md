# Offline Benchmarking

This module adds an additive, Python-only benchmark runner for evaluating artifact-grounded explanations offline. It does not touch Laravel, Flask prediction routes, or runtime prediction contracts.

Current scope:

- Core Phase 1 units: `model_comparison/main`, `incremental_feature_analysis/main`, `feature_ranking/gra`
- Phase 2 chart coverage: every `kind == "chart"` asset in `asset_evidence.json`, including:
  - GRA ranking, SHAP, combined feature analysis
  - univariate/correlation views and feature-vs-target correlation charts
  - feature-importance, distribution, and boxplot charts
  - model-comparison charts and per-model scatter diagnostics
  - predicted-vs-actual, residual, and time-series/prediction-over-time charts
- Conditions: `table_only`, `image_table`, `image_table_summary`
- Arms: `A`, `B`, `C` with a low-risk `D` scaffold
- Extraction flow: step 1 generates `explanation_short`/`explanation_full`; step 2 calls the benchmark LLM again to extract standardized claims from that explanation
- Standardization: claim extraction is constrained by a per-artifact variable catalog derived from post-train output artifacts / gold facts
- Variable scope: each chart/table only passes its own allowed variables into the claim-extraction prompt; the system does not dump all artifact facts into every extraction call
- Verification: rule-based claim checking with `supported`, `partially_supported`, `contradicted`, and `unverifiable`
- Metrics: fact precision, fact recall, fact F1, unsupported claim rate, contradiction rate, coverage of salient facts, and numeric accuracy variants

Run locally from `predict-service`:

```bash
python3 scripts/run_benchmark.py --fixture-only --output-dir ./tmp/benchmark-fixture
python3 scripts/run_benchmark.py --bundle-path app/reports/AI_Long_PostPatch_20260322_1 --output-dir ./tmp/benchmark-real
python3 scripts/run_benchmark.py --bundle-path app/reports/AI_Long_PostPatch_20260322_1 --output-dir ./tmp/benchmark-real-openai --client openai
```

`llm_explanations.json` is not part of benchmark scoring anymore. The benchmark compares only the configured prompt arms, such as `A/B/C`, and ignores any legacy explanation payload when building leaderboard rows.

Claim extraction no longer falls back to sentence splitting heuristics when a structured `claims` array is absent. Benchmark claims must come from the dedicated second-pass extraction call.

When `asset_evidence.json` is present, manifest generation automatically appends chart-specific artifact records on top of the core Phase 1 units. Unknown chart keys fail clearly instead of being skipped silently.

The training-report workflow can also publish benchmark progress back into `summary.json` using `benchmark_status` and `benchmark_summary`. Those fields are intended for the Laravel report page so users can see queued/running/completed benchmark state and open leaderboard artifacts directly from the report UI.

For runtime report updates, the service now benchmarks real `A/B/C` generations on the full Phase 2 chart bundle with `image_table_summary`, chooses the best leaderboard row, and writes the result to `selected_benchmark_explanations` plus `benchmark_eval/selected_explanations.json`. The Laravel report page renders only that benchmark-selected payload after benchmark success; it does not fall back to legacy raw explanation payloads.

Supported output layout:

- `manifest.jsonl`
- `gold/*.json`
- `generations/*.json`
- `extracted_claims/*.json`
- `verifications/*.json`
- `scores/leaderboard.json`
- `scores/leaderboard.csv`
- `run_metadata.json`

Important constraints:

- Table and JSON artifacts are the primary source of truth.
- Chart files are secondary evidence.
- Summary text is tertiary evidence.
- `llm_explanations.json` is never treated as a benchmark arm or as ground truth.
- Missing required files fail the CLI clearly instead of being skipped.

To extend coverage later, add a chart asset spec in `benchmarking/chart_assets.py`, add or reuse a gold builder in `benchmarking/gold_builders.py`, teach the fixture client how to emit normalized claims, and add small synthetic tests under `tests/benchmarking/`.
