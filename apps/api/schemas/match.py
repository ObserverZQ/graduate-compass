"""Contracts for deterministic program matching and its SSE stream.

This module is intentionally limited to validated data shapes shared by the
matching domain logic, the HTTP streaming router, and backend tests. Keeping
contracts separate lets those layers evolve without duplicating the public
wire format. Database queries, scoring rules, SSE orchestration, and model
calls do not belong here.
"""

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Reject contract drift instead of silently discarding unknown fields."""

    model_config = ConfigDict(extra="forbid")


# These enum values are part of the versioned API contract. Renaming one is a
# breaking frontend change even when the corresponding Python name is unused.
class EventName(StrEnum):
    """Canonical SSE names used when framing events for the client."""

    RUN_STARTED = "run_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    PROFILE_LOADED = "profile_loaded"
    FILTERS_APPLIED = "filters_applied"
    CANDIDATE_SCORED = "candidate_scored"
    EXPLANATION_STARTED = "explanation_started"
    CANDIDATE_EXPLAINED = "candidate_explained"
    WARNING = "warning"
    COMPLETE = "complete"
    ERROR = "error"


class MatchStage(StrEnum):
    """Coarse pipeline stages used to group the more specific SSE events."""

    PROFILE = "profile"
    ELIGIBILITY = "eligibility"
    SCORING = "scoring"
    RANKING = "ranking"
    EXPLANATION = "explanation"


# Score vocabulary stays independent of display copy so the frontend can use
# stable keys while labels and explanations remain user-friendly.
class FactorKey(StrEnum):
    """Stable identifiers for the independently explainable score factors."""

    ACADEMIC = "academic"
    PROFESSIONAL = "professional"
    LANGUAGE = "language"
    LOCATION = "location"
    BUDGET = "budget"
    CLIMATE = "climate"
    CAREER = "career"
    INTEREST = "interest"


class FactorStatus(StrEnum):
    """How the available evidence affects one compatibility factor."""

    MATCH = "match"
    GAP = "gap"
    UNCERTAIN = "uncertain"
    NEUTRAL = "neutral"


class WarningCode(StrEnum):
    """Nonfatal conditions that may reduce result coverage or confidence."""

    MISSING_PROFILE_DATA = "missing_profile_data"
    MISSING_PROGRAM_DATA = "missing_program_data"
    FEWER_THAN_SIX_RESULTS = "fewer_than_six_results"


class MatchErrorCode(StrEnum):
    """Stable machine-readable failures that terminate a matching stream."""

    PROFILE_NOT_FOUND = "profile_not_found"
    PROFILE_NOT_REVIEWED = "profile_not_reviewed"
    NO_ELIGIBLE_PROGRAMS = "no_eligible_programs"
    DATABASE_UNAVAILABLE = "database_unavailable"
    MATCHING_FAILED = "matching_failed"


# Result contracts expose both a concise recommendation and its full scoring
# evidence. This lets simple and detailed UIs consume the same response.
class ScoreFactor(ContractModel):
    """One auditable contribution to a program's deterministic fit score."""

    key: FactorKey
    label: str
    points: float = Field(ge=0)
    max_points: float = Field(gt=0)
    status: FactorStatus
    evidence: str


class ProgramMatchResult(ContractModel):
    """Explainable ranked result returned to the matching experience."""

    rank: int = Field(ge=1, le=6)
    program_id: UUID
    name: str
    university: str
    country: str
    degree_type: str | None = None
    # This measures profile/preference compatibility and must never be
    # presented as an admission probability.
    fit_score: int = Field(ge=0, le=100)
    score_version: str
    why_match: str
    # Prominent evidence supports a concise UI, while factors retain the full
    # auditable score breakdown.
    supporting_evidence: list[str]
    factors: list[ScoreFactor]
    strengths: list[str]
    gaps: list[str]
    uncertainties: list[str]
    next_action: str
    # Seeded URLs may be imperfect; one invalid URL should not abort the
    # entire stream. Link validation can happen independently at ingestion.
    official_website: str | None = None


# SSE contracts use a shared run ID and monotonic sequence while each concrete
# model fixes its own `type` with Literal. The combination supports correlation
# and prevents one event shape from masquerading as another.
class EventBase(ContractModel):
    """Fields carried by every event emitted during one matching run."""

    # Version the wire contract independently from the scoring algorithm so
    # clients can evolve safely when event payload shapes change.
    schema_version: Literal["1"] = "1"
    # A run ID correlates events without including resume or preference data.
    run_id: UUID
    # Monotonic sequence numbers let clients detect missing or reordered events.
    sequence: int = Field(ge=1)


class RunStartedEvent(EventBase):
    """Announces the deterministic configuration for a new matching run."""

    type: Literal["run_started"] = "run_started"
    score_version: str
    result_limit: int = Field(default=6, ge=1, le=6)
    explanation_mode: Literal["deterministic", "ai"] = "deterministic"


class StageStartedEvent(EventBase):
    """Signals that a coarse pipeline stage has begun."""

    type: Literal["stage_started"] = "stage_started"
    stage: MatchStage
    message: str


class StageCompletedEvent(EventBase):
    """Signals successful completion of a coarse pipeline stage."""

    type: Literal["stage_completed"] = "stage_completed"
    stage: MatchStage
    message: str
    count: int | None = Field(default=None, ge=0)
    # Optional timing supports observability without making it part of the
    # deterministic ranking inputs or requiring exact timing assertions.
    duration_ms: int | None = Field(default=None, ge=0)


class ProfileLoadedEvent(EventBase):
    """Reports privacy-safe profile coverage after reviewed data is loaded."""

    type: Literal["profile_loaded"] = "profile_loaded"
    message: str
    preference_count: int = Field(ge=0)
    has_academic_evidence: bool
    has_language_evidence: bool
    experience_item_count: int = Field(ge=0)


class FiltersAppliedEvent(EventBase):
    """Summarizes deterministic eligibility filtering without profile details."""

    type: Literal["filters_applied"] = "filters_applied"
    message: str
    program_count: int = Field(ge=0)
    eligible_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)


class CandidateScoredEvent(EventBase):
    """Reports incremental scoring progress for one public program record."""

    type: Literal["candidate_scored"] = "candidate_scored"
    message: str
    program_id: UUID
    program_name: str
    processed: int = Field(ge=1)
    total: int = Field(ge=1)
    fit_score: int = Field(ge=0, le=100)


class ExplanationStartedEvent(EventBase):
    """Announces explanation mode before emitting the shortlisted results."""

    type: Literal["explanation_started"] = "explanation_started"
    message: str
    candidate_count: int = Field(ge=1, le=6)
    mode: Literal["deterministic", "ai"] = "deterministic"


class CandidateExplainedEvent(EventBase):
    """Streams one complete result so the UI can render it incrementally."""

    type: Literal["candidate_explained"] = "candidate_explained"
    message: str
    result: ProgramMatchResult


class WarningEvent(EventBase):
    """Communicates a recoverable limitation without terminating the run."""

    type: Literal["warning"] = "warning"
    stage: MatchStage | None = None
    code: WarningCode
    message: str
    program_id: UUID | None = None


class CompleteEvent(EventBase):
    """Provides the authoritative final result set for a successful run."""

    type: Literal["complete"] = "complete"
    score_version: str
    # The terminal event repeats incrementally streamed results so clients can
    # recover a complete snapshot even if they ignored intermediate events.
    results: list[ProgramMatchResult] = Field(min_length=1, max_length=6)
    disclaimer: str


class ErrorEvent(EventBase):
    """Terminates a stream with a safe error suitable for direct UI display."""

    type: Literal["error"] = "error"
    code: MatchErrorCode
    message: str
    retryable: bool


# This union is the single validation entry point for unknown event payloads.
# Discriminating on `type` selects the intended model and rejects mismatches.
MatchEvent = Annotated[
    RunStartedEvent
    | StageStartedEvent
    | StageCompletedEvent
    | ProfileLoadedEvent
    | FiltersAppliedEvent
    | CandidateScoredEvent
    | ExplanationStartedEvent
    | CandidateExplainedEvent
    | WarningEvent
    | CompleteEvent
    | ErrorEvent,
    Field(discriminator="type"),
]
