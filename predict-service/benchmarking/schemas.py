from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Literal

ArtifactType = str
InputCondition = Literal["table_only", "image_table", "image_table_summary", "image_only"]
ArmName = Literal["A", "B", "C", "D"]
SemanticLevel = Literal["L1", "L2L3", "L1L2L3"]
VerificationStatus = Literal["supported", "partially_supported", "contradicted", "unverifiable"]

SUPPORTED_ARTIFACT_TYPES: tuple[str, ...] = (
    "model_comparison/main",
    "incremental_feature_analysis/main",
    "feature_ranking/gra",
)
SUPPORTED_CONDITIONS: tuple[str, ...] = (
    "table_only",
    "image_table",
    "image_table_summary",
    "image_only",
)
SUPPORTED_ARMS: tuple[str, ...] = ("A", "B", "C", "D")
SUPPORTED_SEMANTIC_LEVELS: tuple[str, ...] = ("L1", "L2L3", "L1L2L3")
CANONICAL_CLAIM_TYPES: tuple[str, ...] = (
    "best_model",
    "metric_value",
    "ranking",
    "top_feature",
    "feature_subset_optimum",
    "plateau",
    "rank_score",
    "freeform",
)


def to_primitive(value: Any) -> Any:
    """Convert nested dataclasses and paths to JSON-safe builtins."""
    if is_dataclass(value):
        return {key: to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    if isinstance(value, tuple):
        return [to_primitive(item) for item in value]
    return value


@dataclass(frozen=True)
class EvidenceRef:
    source_file: str
    priority: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ManifestRecord:
    artifact_id: str
    artifact_type: str
    chart_type: str
    source_files: list[str]
    primary_entities: list[str]
    bundle_name: str
    chart_file: str | None = None
    summary_files: list[str] = field(default_factory=list)
    asset_key: str | None = None
    asset_title: str | None = None
    asset_family: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class GroundTruthFact:
    fact_id: str
    fact_type: str
    subject: str
    predicate: str
    object: Any = None
    value: Any = None
    unit: str | None = None
    evidence: list[EvidenceRef] = field(default_factory=list)
    importance: int = 1
    semantic_level: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class GoldArtifact:
    artifact_id: str
    artifact_type: str
    source_files: list[str]
    chart_type: str
    primary_entities: list[str]
    ground_truth_facts: list[GroundTruthFact]
    salient_facts: list[str]
    forbidden_inferences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ArtifactInputs:
    record: ManifestRecord
    bundle_dir: Path
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    json_payloads: dict[str, Any] = field(default_factory=dict)
    text_payloads: dict[str, str] = field(default_factory=dict)
    chart_files: list[str] = field(default_factory=list)
    asset_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_text: str
    claim_type: str
    span_category: str
    is_numeric: bool
    requires_grounding_from: str
    confidence: float
    source_variable_id: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object: Any = None
    metric: str | None = None
    value: float | int | str | None = None
    unit: str | None = None
    ordered_items: list[str] = field(default_factory=list)
    feature_count: int | None = None
    hedged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


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

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ClaimAlignmentIssue:
    issue_id: str
    issue_type: str
    message: str
    source_variable_id: str | None = None
    mention_id: str | None = None
    claim_id: str | None = None
    action: str = "warn"

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ExplanationOutput:
    artifact_id: str
    arm: str
    input_condition: str
    explanation_short: str
    explanation_full: str
    claims: list[Claim]
    semantic_level: str | None = None
    generation_stage: str | None = None
    correction_trace: "ArmCTrace | None" = None
    parent_draft_hash: str | None = None
    claim_alignment_issues: list[ClaimAlignmentIssue] = field(default_factory=list)
    extracted_variable_mentions: list[ExtractedVariableMention] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ClaimVerification:
    artifact_id: str
    arm: str
    input_condition: str
    claim_id: str
    claim_text: str
    status: str
    semantic_level: str | None = None
    matched_fact_ids: list[str] = field(default_factory=list)
    reason: str = ""
    numeric_delta: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ArtifactScore:
    artifact_id: str
    arm: str
    input_condition: str
    claim_count: int
    metrics: dict[str, float | None]
    semantic_level: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = to_primitive(self)
        flattened = {
            "artifact_id": payload["artifact_id"],
            "arm": payload["arm"],
            "input_condition": payload["input_condition"],
            "claim_count": payload["claim_count"],
            "semantic_level": payload.get("semantic_level"),
        }
        flattened.update(payload["metrics"])
        return flattened


@dataclass(frozen=True)
class ArmCValidationRecord:
    claim_id: str
    claim_text: str
    status: str
    recommended_action: str
    rationale: str = ""
    matched_fact_ids: list[str] = field(default_factory=list)
    grounded_fact_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class CorrectionIteration:
    iteration_index: int
    draft_explanation_short: str
    draft_explanation_full: str
    draft_claims: list[Claim]
    draft_validations: list[ArmCValidationRecord]
    corrected_explanation_short: str
    corrected_explanation_full: str
    corrected_claims: list[Claim]
    corrected_validations: list[ArmCValidationRecord]
    draft_alignment_issues: list[ClaimAlignmentIssue] = field(default_factory=list)
    corrected_alignment_issues: list[ClaimAlignmentIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True)
class ArmCTrace:
    mode: str
    iteration_count: int
    selected_generation_stage: str
    iterations: list[CorrectionIteration]
    decision_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)
