from __future__ import annotations

import re
from typing import Any

from .schemas import Claim, ClaimAlignmentIssue, ExtractedVariableMention

NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
FEATURE_COUNT_PATTERN = re.compile(r"(\d+)\s+features?", re.IGNORECASE)
ORDERING_PATTERN = re.compile(r"([A-Za-z0-9_+\-/ ]+(?:\s*>\s*[A-Za-z0-9_+\-/ ]+)+)")


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _confidence(value: Any) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return 0.75


def _parse_ordered_items(text: str) -> list[str]:
    match = ORDERING_PATTERN.search(text.replace("->", ">"))
    if not match:
        return []
    return [item.strip().strip(".,;:") for item in match.group(1).split(">") if item.strip()]


def _parse_feature_count(text: str) -> int | None:
    match = FEATURE_COUNT_PATTERN.search(text)
    if not match:
        return None
    return int(match.group(1))


def _parse_numeric(text: str) -> float | None:
    values = NUMBER_PATTERN.findall(text)
    if not values:
        return None
    return _as_float(values[-1])


def _catalog_index(variable_catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for variable in variable_catalog:
        if not isinstance(variable, dict):
            continue
        source_variable_id = _clean_text(variable.get("source_variable_id"))
        if source_variable_id:
            index[source_variable_id] = dict(variable)
    return index


def _issue(
    issues: list[ClaimAlignmentIssue],
    *,
    issue_type: str,
    message: str,
    source_variable_id: str | None = None,
    mention_id: str | None = None,
    claim_id: str | None = None,
    action: str = "warn",
) -> None:
    issues.append(
        ClaimAlignmentIssue(
            issue_id=f"alignment-{len(issues) + 1}",
            issue_type=issue_type,
            message=message,
            source_variable_id=source_variable_id,
            mention_id=mention_id,
            claim_id=claim_id,
            action=action,
        )
    )


def normalize_variable_mentions(
    payload: dict[str, Any],
    *,
    artifact_id: str,
) -> list[ExtractedVariableMention]:
    raw_mentions = payload.get("mentions")
    if not isinstance(raw_mentions, list):
        raw_mentions = []

    mentions: list[ExtractedVariableMention] = []
    for index, raw in enumerate(raw_mentions, start=1):
        if not isinstance(raw, dict):
            continue
        source_variable_id = _clean_text(raw.get("source_variable_id"))
        evidence_span = _clean_text(raw.get("evidence_span") or raw.get("claim_text"))
        if not source_variable_id or not evidence_span:
            continue

        ordered_items = raw.get("stated_ordered_items")
        if not isinstance(ordered_items, list):
            ordered_items = raw.get("ordered_items")
        if not isinstance(ordered_items, list):
            ordered_items = _parse_ordered_items(evidence_span)
        normalized_ordered_items = [
            _clean_text(item).strip(".,;:")
            for item in ordered_items
            if _clean_text(item)
        ]

        feature_count = raw.get("stated_feature_count")
        if feature_count is None:
            feature_count = raw.get("feature_count")
        if feature_count is None:
            feature_count = _parse_feature_count(evidence_span)
        try:
            normalized_feature_count = int(feature_count) if feature_count is not None else None
        except (TypeError, ValueError):
            normalized_feature_count = None

        stated_value = raw.get("stated_value")
        if stated_value is None:
            stated_value = raw.get("value")

        mentions.append(
            ExtractedVariableMention(
                mention_id=_clean_text(raw.get("mention_id") or raw.get("claim_id") or f"{artifact_id}:mention:{index}"),
                source_variable_id=source_variable_id,
                evidence_span=evidence_span,
                stated_value=stated_value,
                stated_object=_clean_text(raw.get("stated_object") or raw.get("object") or raw.get("subject")) or None,
                stated_ordered_items=normalized_ordered_items,
                stated_feature_count=normalized_feature_count,
                confidence=_confidence(raw.get("confidence", 0.75)),
            )
        )
    return mentions


def claims_payload_to_variable_mentions(
    payload: dict[str, Any],
    *,
    artifact_id: str,
) -> list[ExtractedVariableMention]:
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        return []
    return normalize_variable_mentions(
        {
            "mentions": [
                {
                    "mention_id": claim.get("claim_id"),
                    "source_variable_id": claim.get("source_variable_id"),
                    "evidence_span": claim.get("claim_text"),
                    "stated_value": claim.get("value"),
                    "stated_object": claim.get("object") or claim.get("subject"),
                    "stated_ordered_items": claim.get("ordered_items"),
                    "stated_feature_count": claim.get("feature_count"),
                    "confidence": claim.get("confidence"),
                }
                for claim in raw_claims
                if isinstance(claim, dict)
            ]
        },
        artifact_id=artifact_id,
    )


def variable_mentions_to_payload(
    mentions: list[ExtractedVariableMention],
    *,
    artifact_id: str,
    arm: str,
    input_condition: str,
    semantic_level: str | None = None,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "arm": arm,
        "input_condition": input_condition,
        "semantic_level": semantic_level,
        "mentions": [mention.to_dict() for mention in mentions],
    }


def _value_kind(variable: dict[str, Any]) -> str:
    value_kind = _clean_text(variable.get("value_kind"))
    if value_kind:
        return value_kind
    fact_type = _clean_text(variable.get("fact_type"))
    if fact_type == "ranking":
        return "ordered_items"
    if fact_type in {"best_model", "top_feature"}:
        return "entity"
    if fact_type in {"feature_subset_optimum", "plateau"}:
        return "feature_count"
    return "numeric"


def _numeric_value_for_mention(
    mention: ExtractedVariableMention,
    variable: dict[str, Any],
    issues: list[ClaimAlignmentIssue],
) -> float | int | str | None:
    value = mention.stated_value
    numeric = _as_float(value)
    if numeric is None:
        numeric = _parse_numeric(mention.evidence_span)

    fact_type = _clean_text(variable.get("fact_type"))
    span = mention.evidence_span.lower()
    if fact_type == "rank_score" and numeric is not None and "rank" in span and "score" not in span:
        _issue(
            issues,
            issue_type="rank_position_not_score",
            message="The mention appears to state a rank position, not the rank score value.",
            source_variable_id=mention.source_variable_id,
            mention_id=mention.mention_id,
            action="drop",
        )
        return None

    if numeric is None:
        _issue(
            issues,
            issue_type="missing_value",
            message="Numeric variable mention did not include a parseable numeric value.",
            source_variable_id=mention.source_variable_id,
            mention_id=mention.mention_id,
        )
        return None
    return numeric


def build_claims_from_mentions(
    *,
    mentions: list[ExtractedVariableMention],
    variable_catalog: list[dict[str, Any]],
    artifact_id: str,
) -> tuple[list[Claim], list[ClaimAlignmentIssue]]:
    catalog = _catalog_index(variable_catalog)
    claims: list[Claim] = []
    issues: list[ClaimAlignmentIssue] = []

    for mention_index, mention in enumerate(mentions, start=1):
        variable = catalog.get(mention.source_variable_id)
        if variable is None:
            _issue(
                issues,
                issue_type="unknown_variable",
                message="Mention referenced a source_variable_id that is not in the variable catalog.",
                source_variable_id=mention.source_variable_id,
                mention_id=mention.mention_id,
                action="drop",
            )
            continue

        claim_type = _clean_text(variable.get("claim_type")) or _clean_text(variable.get("fact_type")) or "freeform"
        fact_type = _clean_text(variable.get("fact_type"))
        predicate = _clean_text(variable.get("predicate")) or None
        metric = _clean_text(variable.get("metric")) or None
        subject = _clean_text(variable.get("subject")) or None
        unit = _clean_text(variable.get("unit")) or None
        value_kind = _value_kind(variable)
        claim_id = f"{artifact_id}:claim:{mention_index}"

        value: float | int | str | None = None
        object_value: Any = None
        ordered_items: list[str] = []
        feature_count: int | None = None

        if value_kind == "numeric":
            value = _numeric_value_for_mention(mention, variable, issues)
            if any(
                issue.mention_id == mention.mention_id and issue.action == "drop"
                for issue in issues
            ):
                continue
        elif value_kind == "entity":
            object_value = mention.stated_object
            if object_value is None:
                _issue(
                    issues,
                    issue_type="missing_object",
                    message="Entity variable mention did not include a stated object.",
                    source_variable_id=mention.source_variable_id,
                    mention_id=mention.mention_id,
                )
        elif value_kind == "ordered_items":
            ordered_items = list(mention.stated_ordered_items)
            if not ordered_items:
                _issue(
                    issues,
                    issue_type="missing_ordered_items",
                    message="Ranking variable mention did not include ordered items.",
                    source_variable_id=mention.source_variable_id,
                    mention_id=mention.mention_id,
                )
        elif value_kind == "feature_count":
            feature_count = mention.stated_feature_count
            if feature_count is None and _as_float(mention.stated_value) is not None:
                feature_count = int(float(_as_float(mention.stated_value) or 0.0))
            if feature_count is None:
                _issue(
                    issues,
                    issue_type="missing_feature_count",
                    message="Feature-count variable mention did not include a feature count.",
                    source_variable_id=mention.source_variable_id,
                    mention_id=mention.mention_id,
                )

        claims.append(
            Claim(
                claim_id=claim_id,
                claim_text=mention.evidence_span,
                claim_type=claim_type,
                span_category="sentence",
                is_numeric=value_kind == "numeric" or value is not None,
                requires_grounding_from="table/json",
                confidence=mention.confidence,
                source_variable_id=mention.source_variable_id,
                subject=subject,
                predicate=predicate,
                object=object_value,
                metric=metric,
                value=value,
                unit=unit,
                ordered_items=ordered_items,
                feature_count=feature_count,
                hedged=False,
            )
        )

        if claim_type and fact_type:
            expected_claim_type = _clean_text(variable.get("claim_type"))
            if expected_claim_type and claim_type != expected_claim_type:
                _issue(
                    issues,
                    issue_type="claim_type_repaired",
                    message="Claim type was repaired from the variable catalog.",
                    source_variable_id=mention.source_variable_id,
                    mention_id=mention.mention_id,
                    claim_id=claim_id,
                )

    return claims, issues


def alignment_metrics(
    issues: list[ClaimAlignmentIssue],
    *,
    claim_count: int,
    mention_count: int | None = None,
) -> dict[str, float]:
    denominator = max(1, mention_count if mention_count is not None else claim_count + len(issues))
    missing_slot_issue_types = {
        "missing_value",
        "missing_object",
        "missing_ordered_items",
        "missing_feature_count",
    }
    alignment_errors = [
        issue
        for issue in issues
        if issue.issue_type not in missing_slot_issue_types
    ]
    return {
        "claim_alignment_error_rate": len(alignment_errors) / denominator,
        "missing_value_rate": sum(1 for issue in issues if issue.issue_type == "missing_value") / denominator,
        "unknown_variable_rate": sum(1 for issue in issues if issue.issue_type == "unknown_variable") / denominator,
        "extraction_drop_rate": sum(1 for issue in issues if issue.action == "drop") / denominator,
    }
