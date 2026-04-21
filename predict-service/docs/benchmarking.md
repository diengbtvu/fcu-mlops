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
- Verification: rule-based claim checking with `supported`, `partially_supported`, `contradicted`, and `unverifiable`
- Metrics: fact precision, fact recall, fact F1, unsupported claim rate, contradiction rate, coverage of salient facts, and numeric accuracy variants

Run locally from `predict-service`:

```bash
python3 scripts/run_benchmark.py --fixture-only --output-dir ./tmp/benchmark-fixture
python3 scripts/run_benchmark.py --bundle-path app/reports/AI_Long_PostPatch_20260322_1 --output-dir ./tmp/benchmark-real
python3 scripts/run_benchmark.py --bundle-path app/reports/AI_Long_PostPatch_20260322_1 --output-dir ./tmp/benchmark-real-openai --client openai
```

If a bundle already contains `llm_explanations.json`, the CLI will ingest it automatically as the official `BASELINE_LLM` arm. This baseline is scored like any other arm, but it remains evidence only and is never treated as gold truth.

`BASELINE_LLM` is now strict-contract only. Each asset entry in `llm_explanations.json` must include a `benchmark_payload` object with:

- `explanation_short`
- `explanation_full`
- `claims[]`

Legacy freeform-only baseline files are rejected clearly instead of being parsed heuristically.

When `asset_evidence.json` is present, manifest generation automatically appends chart-specific artifact records on top of the core Phase 1 units. Unknown chart keys fail clearly instead of being skipped silently.

The training-report workflow can also publish benchmark progress back into `summary.json` using `benchmark_status` and `benchmark_summary`. Those fields are intended for the Laravel report page so users can see queued/running/completed benchmark state and open leaderboard artifacts directly from the report UI.

For runtime report updates, the service now benchmarks real `A/B/C` generations on the full Phase 2 chart bundle with `image_table_summary`, chooses the best non-baseline row, and writes the result to `selected_benchmark_explanations` plus `benchmark_eval/selected_explanations.json`. The Laravel report page renders only that benchmark-selected payload after benchmark success; it does not fall back to legacy raw explanation payloads.

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
- `llm_explanations.json` is baseline evidence only and is never treated as gold truth.
- Missing required files fail the CLI clearly instead of being skipped.

To extend coverage later, add a chart asset spec in `benchmarking/chart_assets.py`, add or reuse a gold builder in `benchmarking/gold_builders.py`, teach the fixture client and baseline adapter how to emit normalized claims, and add small synthetic tests under `tests/benchmarking/`.
