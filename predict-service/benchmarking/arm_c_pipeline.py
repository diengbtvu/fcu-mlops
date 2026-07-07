from __future__ import annotations

import hashlib
import os
import random
import time
from collections import Counter
from typing import Any

from .claim_alignment import (
    build_claims_from_mentions,
    claims_payload_to_variable_mentions,
    normalize_variable_mentions,
)
from .llm_client import BaseLLMClient
from .prompts import (
    build_arm_c_corrector_prompt,
    build_arm_c_draft_prompt,
    build_arm_c_validator_prompt,
    build_claim_extraction_prompt,
    build_prompt_context,
    build_variable_mention_extraction_prompt,
)
from .schemas import (
    ArmCTrace,
    ArmCValidationRecord,
    ArtifactInputs,
    Claim,
    ClaimAlignmentIssue,
    CorrectionIteration,
    ExtractedVariableMention,
    ExplanationOutput,
    GoldArtifact,
)
from .variable_catalog import allowed_variable_facts

_VALID_STATUSES = {"supported", "partially_supported", "contradicted", "unverifiable"}
_VALID_ACTIONS = {"keep", "edit", "drop"}
ARM_C_STAGE_MAX_RETRIES = max(1, int(os.getenv("ARM_C_STAGE_MAX_RETRIES", "3")))
ARM_C_STAGE_RETRY_BACKOFF_SECONDS = max(
    0.0,
    float(os.getenv("ARM_C_STAGE_RETRY_BACKOFF_SECONDS", "2")),
)
ARM_C_STAGE_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("ARM_C_STAGE_RETRY_JITTER_SECONDS", "0.5")),
)


def _draft_hash(explanation_short: str, explanation_full: str) -> str:
    digest = hashlib.sha1()
    digest.update(explanation_short.encode("utf-8"))
    digest.update(b"\n")
    digest.update(explanation_full.encode("utf-8"))
    return digest.hexdigest()


def _fact_payload(fact: Any) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "fact_type": fact.fact_type,
        "subject": fact.subject,
        "predicate": fact.predicate,
        "object": fact.object,
        "value": fact.value,
        "unit": fact.unit,
        "importance": fact.importance,
        "semantic_level": fact.semantic_level,
        "evidence": [item.to_dict() for item in fact.evidence],
    }


def build_arm_c_evidence_packet(
    *,
    inputs: ArtifactInputs,
    gold: GoldArtifact,
    input_condition: str,
    variable_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = build_prompt_context(
        inputs=inputs,
        arm="C",
        condition=input_condition,
        semantic_level=None,
    )
    facts = allowed_variable_facts(gold)
    payload["allowed_variables"] = variable_catalog
    payload["validated_facts"] = [_fact_payload(fact) for fact in facts]
    payload["salient_fact_ids"] = [
        fact_id
        for fact_id in gold.salient_facts
        if any(fact.fact_id == fact_id for fact in facts)
    ]
    return payload


def _build_correction_evidence_packet(
    evidence_packet: dict[str, Any],
    draft_validations: list[ArmCValidationRecord],
) -> dict[str, Any]:
    matched_fact_ids = {
        fact_id
        for record in draft_validations
        for fact_id in record.matched_fact_ids
        if str(fact_id).strip()
    }
    if not matched_fact_ids:
        return evidence_packet

    allowed_variables = list(evidence_packet.get("allowed_variables") or [])
    validated_facts = list(evidence_packet.get("validated_facts") or [])
    salient_fact_ids = [
        fact_id
        for fact_id in list(evidence_packet.get("salient_fact_ids") or [])
        if fact_id in matched_fact_ids
    ]

    reduced_facts = [
        fact
        for fact in validated_facts
        if str(fact.get("fact_id") or "").strip() in matched_fact_ids
    ]
    reduced_variables = [
        variable
        for variable in allowed_variables
        if str(variable.get("source_variable_id") or "").strip() in matched_fact_ids
    ]

    reduced_packet = dict(evidence_packet)
    reduced_packet["validated_facts"] = reduced_facts or validated_facts
    reduced_packet["allowed_variables"] = reduced_variables or allowed_variables
    reduced_packet["salient_fact_ids"] = salient_fact_ids or list(evidence_packet.get("salient_fact_ids") or [])
    return reduced_packet


def _extract_claims_payload(
    *,
    client: BaseLLMClient,
    inputs: ArtifactInputs,
    input_condition: str,
    explanation_payload: dict[str, Any],
    variable_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    empty_payload = {
        "artifact_id": inputs.record.artifact_id,
        "arm": "C",
        "input_condition": input_condition,
        "semantic_level": None,
        "claims": [],
        "extracted_variable_mentions": [],
        "claim_alignment_issues": [],
    }
    set_runtime_context = getattr(client, "set_runtime_context", None)
    clear_runtime_context = getattr(client, "clear_runtime_context", None)
    client_name = str(getattr(client, "name", "") or "").strip().lower()
    if client_name == "groq":
        return empty_payload
    if callable(set_runtime_context):
        set_runtime_context(
            artifact_id=inputs.record.artifact_id,
            arm="C",
            input_condition=input_condition,
            semantic_level=None,
            stage="extract_claims",
        )
    mention_payload: dict[str, Any] | None = None
    try:
        extractor = getattr(client, "extract_variable_mentions_json", None)
        if callable(extractor) and client_name != "groq":
            try:
                mention_payload = extractor(
                    build_variable_mention_extraction_prompt(
                        artifact_id=inputs.record.artifact_id,
                        arm="C",
                        input_condition=input_condition,
                        semantic_level=None,
                        explanation_short=str(explanation_payload.get("explanation_short") or ""),
                        explanation_full=str(explanation_payload.get("explanation_full") or ""),
                        primary_entities=inputs.record.primary_entities,
                        variable_catalog=variable_catalog,
                    )
                )
            except Exception as exc:
                print(
                    "⚠️ Arm C "
                    f"variable mention extraction failed for {inputs.record.artifact_id}: {exc}. "
                    "Falling back to legacy claim extraction."
                )
                mention_payload = None

        if mention_payload is None:
            try:
                legacy_payload = client.extract_claims_json(
                    build_claim_extraction_prompt(
                        artifact_id=inputs.record.artifact_id,
                        arm="C",
                        input_condition=input_condition,
                        semantic_level=None,
                        explanation_short=str(explanation_payload.get("explanation_short") or ""),
                        explanation_full=str(explanation_payload.get("explanation_full") or ""),
                        primary_entities=inputs.record.primary_entities,
                        variable_catalog=variable_catalog,
                    )
                )
            except Exception as exc:
                if client_name == "groq":
                    print(
                        "⚠️ Arm C "
                        f"legacy claim extraction failed for {inputs.record.artifact_id}: {exc}. "
                        "Continuing with empty claims."
                    )
                    return empty_payload
                raise
            mentions = claims_payload_to_variable_mentions(
                legacy_payload,
                artifact_id=inputs.record.artifact_id,
            )
        else:
            mentions = normalize_variable_mentions(
                mention_payload,
                artifact_id=inputs.record.artifact_id,
            )

        claims, issues = build_claims_from_mentions(
            mentions=mentions,
            variable_catalog=variable_catalog,
            artifact_id=inputs.record.artifact_id,
        )
        return {
            "artifact_id": inputs.record.artifact_id,
            "arm": "C",
            "input_condition": input_condition,
            "semantic_level": None,
            "claims": [claim.to_dict() for claim in claims],
            "extracted_variable_mentions": [mention.to_dict() for mention in mentions],
            "claim_alignment_issues": [issue.to_dict() for issue in issues],
        }
    finally:
        if callable(clear_runtime_context):
            clear_runtime_context()


def _normalize_output(
    *,
    inputs: ArtifactInputs,
    input_condition: str,
    explanation_payload: dict[str, Any],
    claims_payload: dict[str, Any],
    generation_stage: str,
    correction_trace: ArmCTrace | None = None,
    parent_draft_hash: str | None = None,
) -> ExplanationOutput:
    def _as_int(value: Any) -> int | None:
        try:
            return int(float(value)) if value is not None and str(value).strip() else None
        except (TypeError, ValueError):
            return None

    claims: list[Claim] = []
    for index, item in enumerate(list(claims_payload.get("claims") or []), start=1):
        if isinstance(item, Claim):
            claims.append(item)
            continue
        if not isinstance(item, dict):
            continue
        claims.append(
            Claim(
                claim_id=str(item.get("claim_id") or f"{inputs.record.artifact_id}:claim:{index}"),
                claim_text=str(item.get("claim_text") or "").strip(),
                claim_type=str(item.get("claim_type") or "freeform").strip() or "freeform",
                span_category=str(item.get("span_category") or "sentence"),
                is_numeric=bool(item.get("is_numeric")),
                requires_grounding_from=str(item.get("requires_grounding_from") or "table/json"),
                confidence=float(item.get("confidence") or 0.75),
                source_variable_id=str(item.get("source_variable_id") or "").strip() or None,
                subject=str(item.get("subject") or "").strip() or None,
                predicate=str(item.get("predicate") or "").strip() or None,
                object=item.get("object"),
                metric=str(item.get("metric") or "").strip() or None,
                value=item.get("value"),
                unit=str(item.get("unit") or "").strip() or None,
                ordered_items=[
                    str(value).strip()
                    for value in list(item.get("ordered_items") or [])
                    if str(value).strip()
                ],
                feature_count=_as_int(item.get("feature_count")),
                hedged=bool(item.get("hedged")),
            )
        )
    return ExplanationOutput(
        artifact_id=inputs.record.artifact_id,
        arm="C",
        input_condition=input_condition,
        explanation_short=str(explanation_payload.get("explanation_short") or "").strip(),
        explanation_full=str(
            explanation_payload.get("explanation_full") or explanation_payload.get("explanation_short") or ""
        ).strip(),
        claims=claims,
        semantic_level=None,
        generation_stage=generation_stage,
        correction_trace=correction_trace,
        parent_draft_hash=parent_draft_hash,
        claim_alignment_issues=[
            issue
            if isinstance(issue, ClaimAlignmentIssue)
            else ClaimAlignmentIssue(
                issue_id=str(issue.get("issue_id") or f"alignment-{index}"),
                issue_type=str(issue.get("issue_type") or "alignment_issue"),
                message=str(issue.get("message") or ""),
                source_variable_id=str(issue.get("source_variable_id") or "").strip() or None,
                mention_id=str(issue.get("mention_id") or "").strip() or None,
                claim_id=str(issue.get("claim_id") or "").strip() or None,
                action=str(issue.get("action") or "warn"),
            )
            for index, issue in enumerate(list(claims_payload.get("claim_alignment_issues") or []), start=1)
            if isinstance(issue, (ClaimAlignmentIssue, dict))
        ],
        extracted_variable_mentions=[
            mention
            if isinstance(mention, ExtractedVariableMention)
            else ExtractedVariableMention(
                mention_id=str(mention.get("mention_id") or f"mention-{index}"),
                source_variable_id=str(mention.get("source_variable_id") or ""),
                evidence_span=str(mention.get("evidence_span") or ""),
                stated_value=mention.get("stated_value"),
                stated_object=str(mention.get("stated_object") or "").strip() or None,
                stated_ordered_items=[
                    str(item)
                    for item in list(mention.get("stated_ordered_items") or [])
                    if str(item).strip()
                ],
                stated_feature_count=_as_int(mention.get("stated_feature_count")),
                confidence=float(mention.get("confidence") or 0.75),
            )
            for index, mention in enumerate(list(claims_payload.get("extracted_variable_mentions") or []), start=1)
            if isinstance(mention, (ExtractedVariableMention, dict))
        ],
    )


def _normalize_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _VALID_STATUSES:
        return normalized
    return "unverifiable"


def _normalize_action(value: Any, status: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _VALID_ACTIONS:
        return normalized
    if status == "supported":
        return "keep"
    if status in {"partially_supported", "contradicted"}:
        return "edit"
    return "drop"


def _normalize_validation_payload(payload: dict[str, Any]) -> list[ArmCValidationRecord]:
    records: list[ArmCValidationRecord] = []
    for item in list(payload.get("validation_records") or []):
        if not isinstance(item, dict):
            continue
        status = _normalize_status(item.get("status"))
        records.append(
            ArmCValidationRecord(
                claim_id=str(item.get("claim_id") or "").strip(),
                claim_text=str(item.get("claim_text") or "").strip(),
                status=status,
                recommended_action=_normalize_action(item.get("recommended_action"), status),
                rationale=str(item.get("rationale") or "").strip(),
                matched_fact_ids=[
                    str(fact_id).strip()
                    for fact_id in list(item.get("matched_fact_ids") or [])
                    if str(fact_id).strip()
                ],
                grounded_fact_summary=str(item.get("grounded_fact_summary") or "").strip() or None,
            )
        )
    return records


def _validate_output(
    *,
    client: BaseLLMClient,
    inputs: ArtifactInputs,
    input_condition: str,
    evidence_packet: dict[str, Any],
    output: ExplanationOutput,
    validation_pass: str,
) -> list[ArmCValidationRecord]:
    payload = client.validate_arm_c_json(
        build_arm_c_validator_prompt(
            artifact_id=inputs.record.artifact_id,
            input_condition=input_condition,
            evidence_packet=evidence_packet,
            explanation_short=output.explanation_short,
            explanation_full=output.explanation_full,
            claims=[claim.to_dict() for claim in output.claims],
            validation_pass=validation_pass,
        )
    )
    return _normalize_validation_payload(payload)


def _trace_decision_counts(iterations: list[CorrectionIteration]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for iteration in iterations:
        for record in iteration.draft_validations:
            counter[record.recommended_action] += 1
    return dict(counter)


def _validation_quality(validations: list[ArmCValidationRecord]) -> tuple[int, int, int, int]:
    contradicted = sum(1 for record in validations if record.status == "contradicted")
    unverifiable = sum(1 for record in validations if record.status == "unverifiable")
    partially_supported = sum(1 for record in validations if record.status == "partially_supported")
    supported = sum(1 for record in validations if record.status == "supported")
    return (contradicted, unverifiable, partially_supported, -supported)


def _run_with_retries(
    *,
    step_label: str,
    operation: Any,
    max_attempts: int = ARM_C_STAGE_MAX_RETRIES,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_attempts:
                break
            wait_seconds = (
                ARM_C_STAGE_RETRY_BACKOFF_SECONDS * attempt
                + random.uniform(0.0, ARM_C_STAGE_RETRY_JITTER_SECONDS)
            )
            print(
                "⚠️ Arm C "
                f"{step_label} attempt {attempt}/{max_attempts} failed: {exc}. "
                f"Retrying in {wait_seconds:.1f}s."
            )
            if wait_seconds > 0:
                time.sleep(wait_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Arm C {step_label} failed without raising an exception.")


def _failed_output(
    *,
    inputs: ArtifactInputs,
    input_condition: str,
    error_message: str,
) -> ExplanationOutput:
    trimmed_error = str(error_message or "arm_c_failed").strip()[:240]
    return ExplanationOutput(
        artifact_id=inputs.record.artifact_id,
        arm="C",
        input_condition=input_condition,
        explanation_short="Arm C correction pipeline failed.",
        explanation_full=(
            "Arm C failed before producing a corrected explanation. "
            f"Error: {trimmed_error}"
        ),
        claims=[],
        generation_stage="failed",
    )


def _build_trace(
    *,
    iteration: CorrectionIteration,
    selected_generation_stage: str,
) -> ArmCTrace:
    return ArmCTrace(
        mode="c_llm_validator_corrector",
        iteration_count=1,
        selected_generation_stage=selected_generation_stage,
        iterations=[iteration],
        decision_counts=_trace_decision_counts([iteration]),
    )


def _return_draft_output(
    *,
    draft_output: ExplanationOutput,
    draft_hash: str,
    draft_validations: list[ArmCValidationRecord],
    corrected_output: ExplanationOutput | None = None,
    corrected_validations: list[ArmCValidationRecord] | None = None,
) -> ExplanationOutput:
    iteration = CorrectionIteration(
        iteration_index=1,
        draft_explanation_short=draft_output.explanation_short,
        draft_explanation_full=draft_output.explanation_full,
        draft_claims=draft_output.claims,
        draft_validations=draft_validations,
        corrected_explanation_short=(
            corrected_output.explanation_short if corrected_output is not None else ""
        ),
        corrected_explanation_full=(
            corrected_output.explanation_full if corrected_output is not None else ""
        ),
        corrected_claims=corrected_output.claims if corrected_output is not None else [],
        corrected_validations=corrected_validations or [],
        draft_alignment_issues=draft_output.claim_alignment_issues,
        corrected_alignment_issues=(
            corrected_output.claim_alignment_issues if corrected_output is not None else []
        ),
    )
    return ExplanationOutput(
        artifact_id=draft_output.artifact_id,
        arm=draft_output.arm,
        input_condition=draft_output.input_condition,
        explanation_short=draft_output.explanation_short,
        explanation_full=draft_output.explanation_full,
        claims=draft_output.claims,
        semantic_level=draft_output.semantic_level,
        generation_stage="draft",
        correction_trace=_build_trace(
            iteration=iteration,
            selected_generation_stage="draft",
        ),
        parent_draft_hash=draft_hash,
        claim_alignment_issues=draft_output.claim_alignment_issues,
        extracted_variable_mentions=draft_output.extracted_variable_mentions,
    )


def run_arm_c_pipeline(
    *,
    inputs: ArtifactInputs,
    gold: GoldArtifact,
    input_condition: str,
    client: BaseLLMClient,
    variable_catalog: list[dict[str, Any]],
) -> ExplanationOutput:
    evidence_packet = build_arm_c_evidence_packet(
        inputs=inputs,
        gold=gold,
        input_condition=input_condition,
        variable_catalog=variable_catalog,
    )

    try:
        draft_explanation_payload = _run_with_retries(
            step_label=f"draft generation for {inputs.record.artifact_id}",
            operation=lambda: client.generate_explanation_json(
                build_arm_c_draft_prompt(
                    inputs=inputs,
                    condition=input_condition,
                )
            ),
        )
    except Exception as exc:
        return _failed_output(
            inputs=inputs,
            input_condition=input_condition,
            error_message=str(exc),
        )

    try:
        draft_claims_payload = _run_with_retries(
            step_label=f"draft claim extraction for {inputs.record.artifact_id}",
            operation=lambda: _extract_claims_payload(
                client=client,
                inputs=inputs,
                input_condition=input_condition,
                explanation_payload=draft_explanation_payload,
                variable_catalog=variable_catalog,
            ),
        )
    except Exception as exc:
        print(
            "⚠️ Arm C "
            f"draft claim extraction failed for {inputs.record.artifact_id}: {exc}. "
            "Continuing with the draft explanation and empty claims."
        )
        draft_claims_payload = {
            "artifact_id": inputs.record.artifact_id,
            "arm": "C",
            "input_condition": input_condition,
            "semantic_level": None,
            "claims": [],
            "extracted_variable_mentions": [],
            "claim_alignment_issues": [],
        }

    draft_output = _normalize_output(
        inputs=inputs,
        input_condition=input_condition,
        explanation_payload=draft_explanation_payload,
        claims_payload=draft_claims_payload,
        generation_stage="draft",
    )

    try:
        draft_validations = _run_with_retries(
            step_label=f"draft validation for {inputs.record.artifact_id}",
            operation=lambda: _validate_output(
                client=client,
                inputs=inputs,
                input_condition=input_condition,
                evidence_packet=evidence_packet,
                output=draft_output,
                validation_pass="draft",
            ),
        )
    except Exception as exc:
        print(
            "⚠️ Arm C "
            f"draft validation failed for {inputs.record.artifact_id}: {exc}. "
            "Continuing with the draft explanation without validation records."
        )
        draft_validations = []

    draft_hash = _draft_hash(
        draft_output.explanation_short,
        draft_output.explanation_full,
    )

    draft_needs_correction = any(
        record.recommended_action in {"edit", "drop"}
        or record.status in {"partially_supported", "contradicted", "unverifiable"}
        for record in draft_validations
    )
    if not draft_output.claims or not draft_validations or not draft_needs_correction:
        return _return_draft_output(
            draft_output=draft_output,
            draft_hash=draft_hash,
            draft_validations=draft_validations,
        )

    corrected_output: ExplanationOutput | None = None
    corrected_validations: list[ArmCValidationRecord] = []
    correction_evidence_packet = _build_correction_evidence_packet(
        evidence_packet,
        draft_validations,
    )
    try:
        corrected_payload = _run_with_retries(
            step_label=f"corrector generation for {inputs.record.artifact_id}",
            operation=lambda: client.correct_arm_c_json(
                build_arm_c_corrector_prompt(
                    artifact_id=inputs.record.artifact_id,
                    input_condition=input_condition,
                    evidence_packet=correction_evidence_packet,
                    draft_explanation_short=draft_output.explanation_short,
                    draft_explanation_full=draft_output.explanation_full,
                    draft_claims=[claim.to_dict() for claim in draft_output.claims],
                    validation_records=[record.to_dict() for record in draft_validations],
                )
            )
        )
        corrected_claims_payload = _run_with_retries(
            step_label=f"corrected claim extraction for {inputs.record.artifact_id}",
            operation=lambda: _extract_claims_payload(
                client=client,
                inputs=inputs,
                input_condition=input_condition,
                explanation_payload=corrected_payload,
                variable_catalog=variable_catalog,
            ),
        )
        corrected_output = _normalize_output(
            inputs=inputs,
            input_condition=input_condition,
            explanation_payload=corrected_payload,
            claims_payload=corrected_claims_payload,
            generation_stage="corrected",
            parent_draft_hash=draft_hash,
        )
        corrected_validations = _run_with_retries(
            step_label=f"corrected validation for {inputs.record.artifact_id}",
            operation=lambda: _validate_output(
                client=client,
                inputs=inputs,
                input_condition=input_condition,
                evidence_packet=correction_evidence_packet,
                output=corrected_output,
                validation_pass="corrected",
            ),
        )
    except Exception as exc:
        print(
            "⚠️ Arm C "
            f"corrected path failed for {inputs.record.artifact_id}: {exc}"
        )
        corrected_output = None
        corrected_validations = []

    if corrected_output is not None:
        iteration = CorrectionIteration(
            iteration_index=1,
            draft_explanation_short=draft_output.explanation_short,
            draft_explanation_full=draft_output.explanation_full,
            draft_claims=draft_output.claims,
            draft_validations=draft_validations,
            corrected_explanation_short=corrected_output.explanation_short,
            corrected_explanation_full=corrected_output.explanation_full,
            corrected_claims=corrected_output.claims,
            corrected_validations=corrected_validations,
            draft_alignment_issues=draft_output.claim_alignment_issues,
            corrected_alignment_issues=corrected_output.claim_alignment_issues,
        )
        if corrected_output.claims and corrected_validations:
            if _validation_quality(corrected_validations) < _validation_quality(draft_validations):
                trace = _build_trace(
                    iteration=iteration,
                    selected_generation_stage="corrected",
                )
                return ExplanationOutput(
                    artifact_id=corrected_output.artifact_id,
                    arm=corrected_output.arm,
                    input_condition=corrected_output.input_condition,
                    explanation_short=corrected_output.explanation_short,
                    explanation_full=corrected_output.explanation_full,
                    claims=corrected_output.claims,
                    semantic_level=corrected_output.semantic_level,
                    generation_stage="corrected",
                    correction_trace=trace,
                    parent_draft_hash=draft_hash,
                    claim_alignment_issues=corrected_output.claim_alignment_issues,
                    extracted_variable_mentions=corrected_output.extracted_variable_mentions,
                )
        trace = _build_trace(
            iteration=iteration,
            selected_generation_stage="draft",
        )
        return ExplanationOutput(
            artifact_id=draft_output.artifact_id,
            arm=draft_output.arm,
            input_condition=draft_output.input_condition,
            explanation_short=draft_output.explanation_short,
            explanation_full=draft_output.explanation_full,
            claims=draft_output.claims,
            semantic_level=draft_output.semantic_level,
            generation_stage="draft",
            correction_trace=trace,
            parent_draft_hash=draft_hash,
            claim_alignment_issues=draft_output.claim_alignment_issues,
            extracted_variable_mentions=draft_output.extracted_variable_mentions,
        )

    return _return_draft_output(
        draft_output=draft_output,
        draft_hash=draft_hash,
        draft_validations=draft_validations,
        corrected_output=corrected_output,
        corrected_validations=corrected_validations,
    )


run_arm_c_lite = run_arm_c_pipeline
