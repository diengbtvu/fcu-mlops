# SPEC - Fix Arm C Claim Extraction and Benchmark Evaluation Contract

Version: v1
Owner: predict-service side
Status: Implemented
Depends on:
- `predict-service/benchmarking-spec.md`
- `predict-service/docs/arm-c-c2tfec-spec.md`
- current offline benchmarking package in `predict-service/benchmarking/`

---

## 1. Problem

Current benchmark results show low `fact_f1` for Arm C even when some generated explanations are readable and partly correct.

Example from `KNN_HPR_20260424`:

- Arm C: `fact_precision ~= 0.354`
- Arm C: `fact_recall ~= 0.146`
- Arm C: `fact_f1 ~= 0.192`
- Arm C: 76 extracted claims
- Supported claims: 18
- Contradicted claims: 24
- Unverifiable claims: 34

This does not mean Arm C text generation alone is bad. The score currently measures a mixed pipeline:

1. explanation generation quality
2. LLM claim extraction quality
3. claim normalization quality
4. verifier contract strictness
5. gold-fact coverage

The biggest observed failure is that explanation text is converted into malformed structured claims.

Concrete examples:

- A correct sentence about KNN having `R2 = 0.81717` and `MSE = 0.012810` became one `metric_value` claim with `source_variable_id = best_model`, `metric = null`, and `value = 0.01281`.
- A GRA rank statement became `gra_score = 2`, confusing rank position with score value.
- A top-feature statement was normalized into `feature_subset_optimum`, causing verifier output such as `Gold feature_subset_optimum count is 0`.

These are claim-contract failures, not only prompt-generation failures.

---

## 2. Goal

Make Arm C and benchmark scoring reliable enough that `fact_f1` primarily reflects whether the explanation states correct, grounded facts.

The fix should:

1. Make claim extraction variable-first and deterministic after mention detection.
2. Prevent LLM outputs from assigning incompatible `claim_type`, `metric`, or `source_variable_id`.
3. Prevent verifier from matching a claim to a gold fact with an incompatible fact type.
4. Keep Arm C correction trace inspectable.
5. Preserve existing leaderboard output shape where possible.
6. Add diagnostics that separate explanation quality from extraction/normalization failures.

---

## 3. Non-Goals

Do not do these in this fix:

- rewrite the whole benchmark framework
- add Laravel UI features
- add database tables for benchmark runs
- implement OCR-heavy chart parsing
- replace the rule-based verifier with a learned evaluator
- change Flask prediction endpoints
- tune the final text-generation prompt as the primary fix

Prompt changes are allowed, but they are secondary. The main fix is the structured claim contract.

---

## 4. Current Failure Points

### 4.1 LLM Extractor Has Too Much Authority

Today, `build_claim_extraction_prompt(...)` asks the LLM to return full claim objects:

- `claim_type`
- `subject`
- `predicate`
- `metric`
- `value`
- `object`
- `ordered_items`
- `feature_count`
- `source_variable_id`

This makes the LLM responsible for schema alignment. It can pick a valid JSON shape while still assigning the wrong semantic type.

### 4.2 Normalizer Can Override the Intended Gold Fact

`claim_extractor.py` canonicalizes `claim_type` from text patterns, numeric values, feature counts, and metrics. This is useful for repair, but it can override the meaning implied by `source_variable_id`.

Bad case:

- `source_variable_id` points to a `top_feature` fact
- claim text contains "features"
- normalizer changes the claim to `feature_subset_optimum`

That creates a valid-looking claim object that cannot be fairly verified.

### 4.3 Verifier Trusts `source_variable_id` Too Early

Verifier helpers often use `_fact_by_source_variable_id(...)` first. If the ID points to the wrong fact type, the verifier can compare the claim under an unrelated rule and produce misleading contradictions.

Verifier should require fact-type compatibility before accepting a source-variable match.

### 4.4 Corrector Can Reintroduce Bad Claims

Arm C corrector currently returns corrected text plus structured `claims`. Those claims pass through the same loose path. Even if corrected text improves, structured claims can remain malformed.

### 4.5 `fact_f1` Conflates Multiple Layers

Current `fact_f1` is still useful as an end-to-end benchmark metric, but it should not be interpreted as pure explanation quality until extraction quality is controlled.

---

## 5. Target Architecture

### 5.1 Variable-First Claim Extraction

The LLM should no longer emit final `Claim` objects directly.

Instead, it should emit lightweight variable mentions. Proposed object:

```python
@dataclass(frozen=True)
class ExtractedVariableMention:
    mention_id: str
    source_variable_id: str
    evidence_span: str
    stated_value: float | int | str | None = None
    stated_object: str | None = None
    stated_ordered_items: list[str] = field(default_factory=list)
    stated_feature_count: int | None = None
    confidence: float = 0.75
```

The LLM is only allowed to choose `source_variable_id` values from `allowed_variables`.

It must not emit:

- `claim_type`
- `subject`
- `predicate`
- `metric`
- `unit`
- `value_kind`

Those fields must be filled by code from the variable catalog / gold fact.

### 5.2 Deterministic Claim Builder

Add a deterministic builder:

```python
def build_claims_from_mentions(
    *,
    mentions: list[ExtractedVariableMention],
    variable_catalog: list[dict[str, Any]],
    artifact_id: str,
) -> tuple[list[Claim], list[ClaimAlignmentIssue]]:
    ...
```

The builder should:

1. Look up the selected `source_variable_id`.
2. Copy `claim_type`, `subject`, `predicate`, `metric`, `unit`, and `value_kind` from the catalog.
3. Parse only the stated value/object/order from the mention.
4. Drop mentions that cannot be aligned safely.
5. Record alignment warnings for diagnostics.

This makes `source_variable_id` the primary key and the catalog the schema authority.

### 5.3 Compatibility Guard

Before verification, every claim should pass:

```python
def validate_claim_catalog_alignment(claim: Claim, catalog_index: dict[str, dict[str, Any]]) -> ClaimAlignmentIssue | None:
    ...
```

Rules:

- If `source_variable_id` is missing, mark extraction issue.
- If `source_variable_id` is unknown, mark extraction issue.
- If `claim_type` differs from catalog `claim_type`, repair from catalog if safe.
- If `metric` differs from catalog `metric`, repair from catalog if safe.
- If `subject` differs from catalog `subject`, repair from catalog if safe.
- If `value_kind = numeric` and no numeric value is stated, keep the claim but tag as `missing_value`.
- If `value_kind = entity` and no entity/object is stated, tag as `missing_object`.

The verifier should receive repaired claims plus alignment issue metadata.

---

## 6. Arm C Pipeline After Fix

Target Arm C sequence:

1. Build evidence packet from bundle + gold facts.
2. Generate draft explanation.
3. Extract variable mentions from draft explanation.
4. Build deterministic draft claims from mentions and catalog.
5. Run rule-based verifier on draft claims.
6. Run Arm C validator over draft claims and evidence packet.
7. Run corrector to fix explanation text.
8. Extract variable mentions from corrected explanation, not trusted final claims.
9. Build deterministic corrected claims.
10. Re-verify corrected claims.
11. Select corrected output only if it improves or preserves factual quality.
12. Export trace with draft and corrected claim-alignment diagnostics.

Important change:

- Corrector may return `claims` for compatibility, but those claims must not be trusted as final.
- Final claims should come from the deterministic mention-to-claim builder.

---

## 7. Prompt Changes

### 7.1 Claim Extraction Prompt

Replace current claim extraction prompt contract with:

- "Select only variables from `allowed_variables` that are explicitly stated in the explanation."
- "Return one mention per stated variable."
- "Do not use rank numbers as metric values."
- "Do not infer missing values from allowed variables."
- "If a sentence states two metrics, return two mentions."
- "If the explanation only says a feature is top-ranked without a numeric score, use `stated_object`, not `stated_value`."

Required output:

```json
{
  "artifact_id": "...",
  "arm": "C",
  "input_condition": "image_table_summary",
  "semantic_level": null,
  "mentions": [
    {
      "mention_id": "m1",
      "source_variable_id": "...",
      "evidence_span": "KNN achieved an R2 score of 0.81717",
      "stated_value": 0.81717,
      "stated_object": null,
      "stated_ordered_items": [],
      "stated_feature_count": null,
      "confidence": 0.9
    }
  ]
}
```

### 7.2 Corrector Prompt

Corrector prompt should not ask the model to produce authoritative final claims.

It should receive:

- draft explanation
- draft verifier records
- alignment issues
- relevant validated facts

It should return:

- corrected `explanation_short`
- corrected `explanation_full`
- optional `edit_summary`

Claims should be extracted again after correction by the same variable-first extraction path.

---

## 8. Verifier Changes

### 8.1 Fact-Type Compatibility

Update `_fact_by_source_variable_id(...)` usage so source-variable matches are accepted only if compatible with the verifier path.

Examples:

- `top_feature` verifier may use facts with `fact_type == "top_feature"` only.
- `feature_subset_optimum` verifier may use facts with `fact_type == "feature_subset_optimum"` only.
- `metric_value` verifier may use facts with `fact_type in {"metric_value", "rank_score", "best_r2", "best_mse"}` only.
- `ranking` verifier may use facts with `fact_type == "ranking"` only.

If the source ID points to an incompatible fact type:

- do not verify against it
- emit an alignment warning
- fall back to normal subject/metric matching only if safe

### 8.2 Reason Clarity

Verifier reason should distinguish:

- `extraction_alignment_error`
- `missing_numeric_value`
- `no_matching_gold_fact`
- `numeric_mismatch`
- `unsupported_claim_type`

This lets the benchmark report tell whether low F1 comes from bad explanation or bad extraction.

---

## 9. Metric Changes

Keep current leaderboard metrics:

- `fact_precision`
- `fact_recall`
- `fact_f1`
- `unsupported_claim_rate`
- `contradiction_rate`
- `coverage_of_salient_facts`
- `numeric_accuracy`
- `numeric_tolerance_accuracy`

Add diagnostic metrics:

- `claim_alignment_error_rate`
- `missing_value_rate`
- `unknown_variable_rate`
- `extraction_drop_rate`
- `supported_claim_count`
- `contradicted_claim_count`
- `unverifiable_claim_count`

Interpretation:

- `fact_f1` remains end-to-end quality.
- `claim_alignment_error_rate` explains how much of the score loss came from extraction/schema problems.
- A run is not ready for explanation-quality reporting if `claim_alignment_error_rate` is high.

---

## 10. File-Level Plan

### Modify `benchmarking/schemas.py`

Add:

- `ExtractedVariableMention`
- `ClaimAlignmentIssue`

Optionally extend `ExplanationOutput` with:

- `claim_alignment_issues: list[ClaimAlignmentIssue]`

Keep backward compatibility when serializing old generation files.

### Modify `benchmarking/prompts.py`

Add:

- `build_variable_mention_extraction_prompt(...)`
- `extract_variable_mention_context(...)`

Keep existing `build_claim_extraction_prompt(...)` as a compatibility wrapper or deprecate it gradually.

### Modify `benchmarking/llm_client.py`

Add client method:

```python
def extract_variable_mentions_json(self, prompt: str) -> dict[str, Any]:
    ...
```

Add JSON schema for `mentions`.

Keep `extract_claims_json(...)` temporarily for A/B compatibility if needed.

### Add `benchmarking/claim_alignment.py`

Own:

- mention normalization
- catalog indexing
- deterministic `Claim` construction
- alignment issue generation

This module should be pure and heavily tested.

### Modify `benchmarking/arm_c_pipeline.py`

Change Arm C to:

- extract mentions from draft
- build deterministic claims
- validate/correct
- extract mentions from corrected text
- build deterministic corrected claims

Do not trust corrector-returned claims as final.

### Modify `benchmarking/verifier.py`

Add fact-type compatibility checks before source-variable matches are accepted.

### Modify `benchmarking/metrics.py`

Add diagnostic metrics from alignment issues.

Do not let new diagnostics change the existing leaderboard sort order initially.

### Modify `benchmarking/chart_reporting.py`

Expose alignment diagnostics in per-chart output:

- top alignment issue reasons
- alignment error count
- dropped mention count

---

## 11. Test Plan

Add tests under `predict-service/tests/benchmarking/`.

Required tests:

1. `test_variable_mention_schema_accepts_catalog_ids_only`
2. `test_claim_builder_copies_claim_type_from_catalog`
3. `test_claim_builder_does_not_convert_rank_to_score`
4. `test_top_feature_source_id_cannot_become_feature_subset_optimum`
5. `test_best_model_and_metric_sentence_splits_into_two_claims`
6. `test_verifier_rejects_incompatible_source_variable_fact_type`
7. `test_arm_c_uses_extracted_mentions_for_final_claims`
8. `test_corrector_claims_are_not_trusted_as_final`
9. `test_alignment_diagnostics_are_written_to_generation_output`
10. `test_leaderboard_preserves_existing_metric_keys`
11. `test_per_chart_report_includes_alignment_error_rate`
12. `test_fixture_cli_still_runs_without_api_credentials`

Regression fixtures should include:

- KNN best model sentence with R2 and MSE in one sentence
- GRA ranking sentence with rank positions and scores separated
- top-feature sentence without numeric value
- feature-importance sentence where the top feature is VSS, not VFA

---

## 12. Acceptance Criteria

This fix is complete when:

1. Arm C no longer accepts raw LLM claim objects as authoritative final claims.
2. Every final Arm C claim is built from a known `source_variable_id`.
3. Claim type, subject, metric, and unit come from the variable catalog, not LLM guesswork.
4. Source-variable fact-type mismatches cannot produce misleading verifier comparisons.
5. `fact_f1` can be interpreted as end-to-end explanation quality with extraction diagnostics available.
6. Existing output files still exist:
   - `manifest.jsonl`
   - `gold/*.json`
   - `generations/*.json`
   - `extracted_claims/*.json`
   - `verifications/*.json`
   - `scores/leaderboard.json`
   - `scores/per_chart_benchmark.json`
7. Fixture benchmark CLI passes.
8. New tests pass.

---

## 13. Rollout Plan

### Phase 1 - Verifier Guard

Implement fact-type compatibility checks in `verifier.py`.

This is the smallest safe patch and should reduce misleading contradictions.

### Phase 2 - Deterministic Claim Builder

Add `claim_alignment.py` and tests.

Use it for Arm C first.

### Phase 3 - Arm C Pipeline Switch

Change Arm C draft/corrected paths to use mention extraction and deterministic claims.

Keep A/B on current path temporarily.

### Phase 4 - Metrics and Reporting Diagnostics

Add alignment diagnostics to leaderboard payload and per-chart output.

### Phase 5 - Optional A/B Migration

If Arm C results improve and tests are stable, migrate A/B claim extraction to the same variable-first path.

---

## 14. Expected Impact

Expected improvements:

- fewer false contradictions from malformed claim objects
- fewer `freeform` and `missing numeric value` failures
- clearer reason codes when extraction fails
- Arm C correction quality becomes easier to inspect
- `fact_f1` becomes more useful for comparing prompts/arms

Expected non-improvements:

- Recall may remain low if explanations still omit salient facts.
- Some charts may still score poorly if gold facts are incomplete or too strict.
- Prompt generation may still need a separate pass after extraction alignment is stable.

---

## 15. Recommended Implementation Order

Do this first:

1. Add verifier fact-type compatibility guard.
2. Add `claim_alignment.py` with deterministic builder.
3. Switch Arm C final claims to builder output.
4. Add alignment diagnostics.
5. Rerun `KNN_HPR_20260424`.

Only after that, tune Arm C generation prompts for better recall.
