# SPEC — Arm C Redesign: C2TFEC-Style Multi-Stage Self-Correction

Version: v1
Owner: predict-service side
Status: Proposed
Depends on:
- `predict-service/benchmarking-spec.md`
- current offline benchmarking package in `predict-service/benchmarking/`
- paper: "Do LVLMs Understand Charts? Analyzing and Correcting Factual Errors in Chart Captioning" (`arXiv:2312.10160`)

---

## 1. Problem

Current Arm C is not faithful to the original paper design.

Today, Arm C is only a prompt label:

- `Generate, self-check, and revise. Remove unsupported claims before returning the final explanation.`

In practice, the codebase does **not** run a dedicated correction pipeline for Arm C:

- there is no separate draft stage
- there is no dedicated validator stage
- there is no correction trace
- there is no iterative re-validation loop
- there is no model-role separation between generator and validator

This means Arm C currently behaves like:

- `single-pass generation with a stricter instruction`

instead of:

- `multi-stage generate -> validate -> correct -> re-validate`

That mismatch should be fixed.

---

## 2. Paper Grounding

The paper's correction framework is **C2TFEC**, not a one-shot prompt.

Core ideas from the paper:

1. It decomposes correction into **two explicit stages**:
   - chart-to-table conversion
   - table-based factual error rectification

2. The correction stage first produces an **explanatory breakdown of factual errors**, then uses that reasoning to produce the corrected caption.

3. The paper explicitly separates:
   - structured evidence extraction
   - factual verification
   - language correction

4. The paper also warns against using the same LVLM as both generator and evaluator because of **self-enhancement bias**.

Implication for our codebase:

- We should not model Arm C as "just another prompt".
- We should model Arm C as a **pipeline** with at least:
  - draft generation
  - claim extraction
  - validation
  - correction
  - re-validation

Important adaptation:

- The paper needs a chart-to-table model because it starts from raw chart images.
- Our system already has post-train bundle artifacts such as CSV/JSON/TXT tables and summaries.
- Therefore, we do **not** need to replicate the paper's chart-to-table training stage literally.
- Instead, we should treat our existing bundle outputs as the **symbolic evidence layer** that replaces the paper's generated table.

So the correct adaptation is:

- `chart -> table` in the paper
- becomes
- `artifact bundle -> normalized evidence packet` in our system

---

## 3. Goal

Redesign Arm C so it becomes a genuine correction pipeline:

1. Generate a draft explanation from artifact context
2. Extract structured claims from that draft
3. Validate each claim against normalized evidence
4. Produce a machine-readable correction plan
5. Rewrite the explanation with minimal factual edits
6. Re-extract claims and re-validate
7. Return the corrected explanation plus correction trace

Success means Arm C is:

- architecturally different from Arm A
- inspectable and debuggable
- closer to the paper's C2TFEC logic
- measurably better on contradiction and unsupported-claim rate

---

## 4. Non-Goals

Out of scope for this redesign:

- training a new chart-to-table vision model
- reproducing CHARTVE training from the paper
- replacing the whole benchmark with a learned NLI-only evaluator
- changing Arm A or Arm B behavior
- changing Laravel UI contracts beyond additive payload fields

---

## 5. High-Level Design

### 5.1 New Arm C Principle

Arm C must become:

- `Draft Generator` + `Validator` + `Corrector`

not:

- `single LLM prompt that claims it self-checked`

### 5.2 Evidence-First Architecture

Arm C should always reason over a normalized evidence packet built from:

- per-artifact CSV tables
- JSON payloads
- text summaries
- chart evidence metadata
- per-artifact allowed variable catalog

The evidence packet becomes the symbolic bridge analogous to the paper's table representation.

### 5.3 Minimal-Edit Correction

The corrector should:

- keep supported claims when possible
- revise contradicted claims if a supported replacement exists
- remove unsupported or unverifiable claims if no grounded replacement exists
- minimize unnecessary rewriting of style and structure

This mirrors the paper's idea that correction should preserve the caption while fixing factuality.

---

## 6. Proposed Arm C Pipeline

### Stage 0 — Evidence Packet Builder

Input:

- `ArtifactInputs`
- `GoldArtifact`
- per-artifact variable catalog

Output:

- `EvidencePacket`

The packet should include:

- `artifact_id`
- `artifact_type`
- `input_condition`
- `source_priority`
- `primary_entities`
- `allowed_variables`
- `table_evidence`
- `json_evidence`
- `summary_evidence`
- `chart_evidence`
- `salient_facts`

Design rule:

- only include evidence relevant to the current artifact
- never dump unrelated artifact facts into Arm C prompts

### Stage 1 — Draft Generator

Purpose:

- produce an initial explanation draft

Behavior:

- grounded generation only
- no self-check language in this stage
- explanation only, no correction reasoning yet

This stage may reuse most of the current Arm A generation protocol, but it must be stored as a draft rather than treated as final output.

Output:

- `draft_explanation_short`
- `draft_explanation_full`

### Stage 2 — Claim Extraction

Purpose:

- convert the draft into structured claims using the existing second-pass extraction flow

Behavior:

- reuse the current `build_claim_extraction_prompt(...)`
- constrain extraction by the per-artifact variable catalog
- no heuristic sentence fallback

Output:

- `draft_claims`

### Stage 3 — Validator

Purpose:

- determine which draft claims are supported, contradicted, partially supported, or unverifiable

Validator stack:

1. Primary validator:
   - deterministic verifier already implemented in `verifier.py`

2. Optional secondary validator:
   - separate LLM validator or lightweight NLI-style model
   - used only for cases not fully captured by rule-based verification
   - must be logically separate from the generator role

Validation output per claim:

- `claim_id`
- `status`
- `matched_fact_ids`
- `reason`
- `recommended_action`
- `replacement_value` if applicable

`recommended_action` enum:

- `keep`
- `edit`
- `drop`

Important rule:

- if an LLM validator is used, it should not be the sole source of truth for numeric claims when rule-based evidence exists

### Stage 4 — Correction Planner

Purpose:

- aggregate validator results into an explicit edit plan for the corrector

Output:

- `CorrectionPlan`

Fields:

- `supported_claim_ids`
- `contradicted_claim_ids`
- `unverifiable_claim_ids`
- `edit_instructions`
- `drop_instructions`
- `facts_that_must_appear`
- `facts_that_must_not_appear`

Edit instruction examples:

- replace `SVM r2_score = 0.81` with `SVM r2_score = 0.73`
- remove unsupported statement about a feature not present in evidence
- rewrite ranking to match verified order

### Stage 5 — Corrector

Purpose:

- rewrite the draft explanation according to the correction plan

Inputs:

- original draft
- evidence packet
- correction plan
- validator reasons

Rules:

- preserve supported content whenever possible
- fix wrong values and labels using provided evidence
- remove unverifiable speculation
- do not introduce facts absent from the evidence packet
- prefer small edits over full rewrites

Output:

- `corrected_explanation_short`
- `corrected_explanation_full`
- optional `correction_notes`

### Stage 6 — Re-Extraction and Re-Validation

Purpose:

- verify that the corrected explanation is actually better than the draft

Process:

1. extract claims again from corrected explanation
2. run verifier again
3. compare pre/post metrics

Stop conditions:

- no contradicted claims remain
- unsupported claim rate is below threshold
- no improvement between iterations
- `max_iters` reached

Default:

- `max_iters = 2`

### Stage 7 — Finalization

Final Arm C output should include:

- final corrected explanation
- final claims
- final verifications
- additive trace metadata for inspection

Leaderboard scoring should use the **final corrected output**, not the initial draft.

---

## 7. Operating Modes

To make rollout practical, Arm C should support two modes.

### 7.1 C-lite

Immediate implementation target.

Pipeline:

- draft generator
- claim extraction
- deterministic verifier
- correction planner
- corrector
- one re-validation pass

This mode requires no new trained model and can be built on current infrastructure.

### 7.2 C-full

Goal-state implementation.

Pipeline:

- draft generator
- claim extraction
- deterministic verifier
- separate validator model or NLI/LLM validator
- correction planner
- corrector
- iterative re-validation loop

This is closer to the paper's spirit of role separation and factual checking.

---

## 8. Data Contract Changes

### 8.1 New Schema Objects

Add to `benchmarking/schemas.py`:

```python
@dataclass(frozen=True)
class ValidationDecision:
    claim_id: str
    status: str
    matched_fact_ids: list[str]
    reason: str
    recommended_action: str  # keep | edit | drop
    replacement_value: Any = None


@dataclass(frozen=True)
class CorrectionIteration:
    iteration_index: int
    draft_explanation_short: str
    draft_explanation_full: str
    draft_claims: list[Claim]
    decisions: list[ValidationDecision]
    corrected_explanation_short: str
    corrected_explanation_full: str


@dataclass(frozen=True)
class ArmCTrace:
    mode: str  # c_lite | c_full
    iteration_count: int
    iterations: list[CorrectionIteration]
    final_decision_summary: dict[str, int]
```

### 8.2 Extend `ExplanationOutput`

Add additive fields:

```python
@dataclass(frozen=True)
class ExplanationOutput:
    ...
    generation_stage: str | None = None  # draft | corrected | single_pass
    correction_trace: ArmCTrace | None = None
    parent_draft_hash: str | None = None
```

Backward compatibility:

- Arms A/B/D keep these fields as `None`

---

## 9. File-Level Changes

### [NEW] `benchmarking/arm_c_pipeline.py`

Own the full Arm C orchestration:

- build evidence packet
- generate draft
- extract claims
- validate
- build correction plan
- correct
- re-validate

This logic should not be hidden inside generic prompt code.

### [MODIFY] `benchmarking/generator.py`

Current behavior:

- all arms go through the same generic path

New behavior:

- route `arm == "C"` into `run_arm_c_pipeline(...)`
- keep `A/B/D` on the current lightweight path

### [MODIFY] `benchmarking/prompts.py`

Remove the fake Arm C behavior:

- Arm C should no longer rely on a single instruction that says "self-check"

Add dedicated prompt builders:

- `build_arm_c_draft_prompt(...)`
- `build_arm_c_validator_prompt(...)`
- `build_arm_c_corrector_prompt(...)`

### [MODIFY] `benchmarking/llm_client.py`

Add role-aware methods:

```python
class BaseLLMClient(ABC):
    def generate_explanation_json(self, prompt: str) -> dict[str, Any]: ...
    def extract_claims_json(self, prompt: str) -> dict[str, Any]: ...
    def validate_claims_json(self, prompt: str) -> dict[str, Any]: ...
    def correct_explanation_json(self, prompt: str) -> dict[str, Any]: ...
```

Notes:

- `validate_claims_json(...)` may be optional in `C-lite`
- `FixtureLLMClient` must simulate validation and correction behavior

### [MODIFY] `benchmarking/verifier.py`

Reuse as deterministic backbone for Arm C.

Add helper:

- `build_validation_decisions(...)`

This helper should convert raw `ClaimVerification` records into correction-ready actions.

### [MODIFY] `benchmarking/metrics.py`

Add pre/post correction diagnostics for Arm C.

### [MODIFY] `benchmarking/cli.py`

Add optional flags:

```bash
--arm-c-mode c_lite|c_full
--arm-c-max-iters 2
--arm-c-validator-client rule|ollama|openai
--arm-c-validator-model <model_name>
```

Defaults:

- `arm-c-mode = c_lite`
- `arm-c-max-iters = 2`

---

## 10. Prompt Contracts

### 10.1 Draft Prompt

Purpose:

- produce a grounded first-pass explanation

Must return:

- `artifact_id`
- `arm`
- `input_condition`
- `explanation_short`
- `explanation_full`

Must not claim it has already self-checked.

### 10.2 Validator Prompt

Purpose:

- inspect structured claims against allowed evidence

Must return:

- per-claim status
- rationale
- recommended action
- optional replacement values

The validator prompt should receive:

- evidence packet
- structured claims
- allowed variables

It should not receive hidden gold facts outside the current artifact scope.

### 10.3 Corrector Prompt

Purpose:

- rewrite minimally using the validator decisions

Must return:

- corrected explanation
- optional brief explanation of edits

Key constraints:

- no new unsupported claims
- minimal edits
- preserve supported content

---

## 11. Evaluation Changes

Arm C should no longer be evaluated as a black box only on final explanation.

We should store both:

- `draft scores`
- `final corrected scores`

### New diagnostic metrics

Additive metrics:

- `correction_fact_f1_gain`
- `correction_precision_gain`
- `correction_recall_gain`
- `contradiction_drop`
- `unsupported_drop`
- `edit_distance_from_draft`
- `claims_removed_count`
- `claims_corrected_count`

Leaderboard behavior:

- main leaderboard still ranks final outputs only
- Arm C debug exports should include draft-vs-final delta

---

## 12. Output Layout Changes

Add new directories:

```text
benchmark_eval/
├── generations/
├── extracted_claims/
├── verifications/
├── arm_c_traces/
│   ├── <artifact>_c_<condition>.json
├── arm_c_drafts/
│   ├── <artifact>_c_<condition>.json
├── arm_c_corrections/
│   ├── <artifact>_c_<condition>.json
```

Each Arm C trace file should contain:

- evidence packet summary
- draft explanation
- draft claims
- validator decisions
- correction plan
- corrected explanation
- final claims
- final verifications

---

## 13. Selection Policy

No special selection privilege for Arm C.

Rules:

- Arm C wins only if its **final corrected output** wins on benchmark metrics
- correction trace is for auditability, not for automatic selection preference

This avoids repeating the previous mistake where a row was chosen for style rather than score.

---

## 14. Migration Plan

### Phase 1

Implement `C-lite`.

Deliverables:

- `arm_c_pipeline.py`
- dedicated draft/validator/corrector prompts
- deterministic validation decisions
- one correction iteration
- trace export

### Phase 2

Add optional separate validator model.

Deliverables:

- `validate_claims_json(...)`
- role-separated validator client/model settings
- hybrid validation logic for freeform/trend-heavy claims

### Phase 3

Optional research upgrades.

Deliverables:

- learned validator
- richer entailment module for chart-only conditions
- multi-iteration correction beyond 2 rounds

---

## 15. Test Plan

Add tests under `predict-service/tests/benchmarking/`.

Required tests:

1. `test_arm_c_routes_to_pipeline`
2. `test_arm_c_generates_draft_before_final_output`
3. `test_arm_c_builds_validation_decisions_from_verifier`
4. `test_arm_c_corrector_removes_contradicted_claims`
5. `test_arm_c_revalidation_improves_or_keeps_fact_f1`
6. `test_arm_c_trace_export_is_written`
7. `test_arm_c_lite_works_without_secondary_validator`
8. `test_arm_c_full_uses_separate_validator_role`
9. `test_arm_c_output_remains_backward_compatible_for_leaderboard`

Nice-to-have tests:

10. `test_arm_c_minimizes_edits_when_only_one_claim_is_wrong`
11. `test_arm_c_drops_unverifiable_claim_if_no_replacement_exists`
12. `test_arm_c_preserves_supported_claims`

---

## 16. Acceptance Criteria

Arm C redesign is considered complete when:

1. Arm C no longer relies on a one-line self-check instruction as its core mechanism
2. Arm C has an explicit multi-stage correction pipeline in code
3. Arm C exports an inspectable correction trace
4. Arm C final outputs are re-validated after correction
5. Benchmark artifacts expose draft-vs-final diagnostics
6. Arm C can run in `C-lite` mode without new model training

---

## 17. Recommended Implementation Decision

Adopt this interpretation of the paper for our system:

- preserve the paper's **decomposition principle**
- adapt the paper's `chart -> table` stage into our existing `artifact bundle -> evidence packet` stage
- implement Arm C first as `C-lite`
- do not pretend a single prompt is self-correction

This is the lowest-risk way to make Arm C faithful to the paper's method while staying compatible with the current benchmark architecture.

---

## 18. References

- Paper PDF: https://arxiv.org/pdf/2312.10160
- Paper abstract page: https://arxiv.org/abs/2312.10160
- Current benchmark spec: `predict-service/benchmarking-spec.md`
