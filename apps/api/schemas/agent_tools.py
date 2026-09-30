"""Validated contracts for the matching orchestrator's bounded tools.

This module defines data shapes only. Database access, retrieval, scoring,
ranking, orchestration, and model calls belong in their respective runtime
modules. Every contract inherits ``extra="forbid"`` from ``ContractModel`` so
unexpected fields fail validation instead of silently changing behavior.
"""

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field

from apps.api.schemas.match import (
    ContractModel,
    FactorStatus,
    ProgramMatchResult,
)
from apps.api.schemas.profile import ApplicantProfile


MAX_CANDIDATES = 30
MAX_RESULTS = 8
MAX_FILTER_VALUES = 10
MAX_EVIDENCE_ITEMS = 10


class EvidenceConfidence(StrEnum):
    """Confidence derived from coverage and source quality, not an LLM guess."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RetrievalEvidence(ContractModel):
    """One program field that contributed to semantic retrieval."""

    # Program column or document section from which this evidence was taken.
    source_field: str = Field(min_length=1, max_length=80)
    statement: str = Field(min_length=1, max_length=500)
    # Normalized retrieval similarity; absent when the retriever has no score.
    relevance_score: float | None = Field(default=None, ge=0, le=1)


class ProgramSummary(ContractModel):
    """Bounded public program data returned by ``search_programs``."""

    # Stable database identifier used to join later tool results.
    program_id: UUID
    name: str = Field(min_length=1, max_length=300)
    university: str = Field(min_length=1, max_length=300)
    country: str = Field(min_length=1, max_length=120)
    # Normalized degree label as published by the program, when available.
    degree_type: str | None = Field(default=None, max_length=80)
    # Normalized semantic retrieval score, independent of the final fit score.
    retrieval_score: float | None = Field(default=None, ge=0, le=1)
    # Source-backed reasons this program appeared in the retrieved candidates.
    retrieval_evidence: list[RetrievalEvidence] = Field(
        default_factory=list,
        max_length=MAX_EVIDENCE_ITEMS,
    )
    # Public destination retained through ranking for the final result card.
    official_website: str | None = Field(default=None, max_length=2_000)


class SearchProgramsInput(ContractModel):
    """Hard filters and semantic query for retrieving candidate programs."""

    query: str = Field(min_length=1, max_length=2_000)
    # Explicit degree constraints used for eligibility, not soft preferences.
    degree_filters: list[str] = Field(
        default_factory=list,
        max_length=MAX_FILTER_VALUES,
    )
    # Explicit country or region constraints used for eligibility.
    location_filters: list[str] = Field(
        default_factory=list,
        max_length=MAX_FILTER_VALUES,
    )
    limit: int = Field(default=MAX_CANDIDATES, ge=1, le=MAX_CANDIDATES)


class SearchProgramsOutput(ContractModel):
    """Candidate set retained after hard filtering and retrieval."""

    candidates: list[ProgramSummary] = Field(max_length=MAX_CANDIDATES)
    # Catalogue records inspected before hard constraints were applied.
    total_considered: int = Field(ge=0)
    # Records removed only because they violated an explicit hard constraint.
    excluded_by_hard_constraints: int = Field(ge=0)


class GetProgramDetailsInput(ContractModel):
    """Programs whose evidence is required by downstream tools."""

    # Stable IDs of retrieved candidates whose full evidence is required.
    program_ids: list[UUID] = Field(
        min_length=1,
        max_length=MAX_CANDIDATES,
    )


class ProgramDetails(ContractModel):
    """Program facts used for requirements, preferences, and explanation."""

    # Stable database identifier shared across all matching tool results.
    program_id: UUID
    name: str = Field(min_length=1, max_length=300)
    university: str = Field(min_length=1, max_length=300)
    country: str = Field(min_length=1, max_length=120)
    # Degree label published by the program, before any normalization.
    degree_type: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    # Published research topics used for relevance and preference comparison.
    research_areas: str | None = Field(default=None, max_length=5_000)
    # Published program length in months.
    duration_months: int | None = Field(default=None, ge=1)
    # Published annual tuition and mandatory fees in US dollars.
    annual_tuition_and_fees: int | None = Field(default=None, ge=0)
    # Estimated annual non-tuition living cost in US dollars.
    annual_living_expenses: int | None = Field(default=None, ge=0)
    # Published minimum grade-point average, without assuming a four-point scale.
    min_gpa: float | None = Field(default=None, ge=0)
    # Published minimum TOEFL score, normally on the 120-point scale.
    min_toefl: int | None = Field(default=None, ge=0)
    # Published minimum IELTS band score.
    min_ielts: float | None = Field(default=None, ge=0)
    # Whether the program explicitly publishes the GRE as required.
    gre_required: bool | None = None
    # Source data may contain a short climate description, not only a label.
    climate: str | None = Field(default=None, max_length=1_000)
    # Qualitative location and student-life evidence, not a numeric rating.
    living_experience: str | None = Field(default=None, max_length=5_000)
    # Existing catalogue indicator for employment outcomes; not a probability.
    job_placement_score: float | None = Field(default=None, ge=0)
    # Published information about preparation or progression toward a PhD.
    phd_pathway_detail: str | None = Field(default=None, max_length=5_000)
    # Canonical public program page used as the evidence destination.
    official_website: str | None = Field(default=None, max_length=2_000)


class GetProgramDetailsOutput(ContractModel):
    """Evidence-bearing details for a bounded candidate set."""

    programs: list[ProgramDetails] = Field(max_length=MAX_CANDIDATES)
    # Requested IDs that were absent, inaccessible, or no longer available.
    missing_program_ids: list[UUID] = Field(
        default_factory=list,
        max_length=MAX_CANDIDATES,
    )


class AssessRequirementsInput(ContractModel):
    """Reviewed applicant facts and programs to assess without filtering."""

    # The reviewed profile type prevents raw extraction output or a loose
    # dictionary from crossing into requirement assessment.
    applicant: ApplicantProfile
    programs: list[ProgramDetails] = Field(
        min_length=1,
        max_length=MAX_CANDIDATES,
    )


class RequirementAssessment(ContractModel):
    """Evidence-backed readiness summary; never an admission prediction."""

    # Candidate identifier that links this assessment to program evidence.
    program_id: UUID
    strengths: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_ITEMS)
    gaps: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE_ITEMS)
    # Missing or ambiguous evidence that prevents a confident comparison.
    uncertainties: list[str] = Field(
        default_factory=list,
        max_length=MAX_EVIDENCE_ITEMS,
    )
    # Confidence based on available published evidence, not admission odds.
    evidence_confidence: EvidenceConfidence


class AssessRequirementsOutput(ContractModel):
    """Requirement assessments for every supplied candidate."""

    assessments: list[RequirementAssessment] = Field(max_length=MAX_CANDIDATES)


class PreferenceImportance(StrEnum):
    """User-selected relative importance for a soft preference."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PreferenceCriterion(ContractModel):
    """One expressed soft preference; absence means no scoring effect."""

    key: str = Field(min_length=1, max_length=80)
    values: list[str] = Field(min_length=1, max_length=MAX_FILTER_VALUES)
    # Relative weight selected by the user for this soft preference.
    importance: PreferenceImportance = PreferenceImportance.MEDIUM


class CalculatePreferenceFitInput(ContractModel):
    """Expressed soft preferences and programs to score without filtering."""

    preferences: list[PreferenceCriterion] = Field(max_length=20)
    programs: list[ProgramDetails] = Field(
        min_length=1,
        max_length=MAX_CANDIDATES,
    )


class PreferenceComponent(ContractModel):
    """Auditable contribution of one expressed preference."""

    key: str = Field(min_length=1, max_length=80)
    importance: PreferenceImportance
    points: float = Field(ge=0)
    # Maximum weighted contribution configured for this preference.
    max_points: float = Field(gt=0)
    # Whether available evidence matches, conflicts, is neutral, or is unknown.
    status: FactorStatus
    evidence: str = Field(min_length=1, max_length=500)
    # Confidence that the program has enough data to assess this preference.
    data_confidence: EvidenceConfidence


class PreferenceFit(ContractModel):
    """Soft-preference alignment kept separate from eligibility."""

    # Candidate identifier that links preference output to other tool results.
    program_id: UUID
    # None means the user expressed no applicable preference; it is not zero.
    score: float | None = Field(default=None, ge=0, le=100)
    # Fraction of expressed preferences supported by usable program evidence.
    evidence_coverage: float = Field(ge=0, le=1)
    components: list[PreferenceComponent] = Field(
        default_factory=list,
        max_length=20,
    )
    # Expressed preferences that lacked enough program evidence to evaluate.
    uncertainties: list[str] = Field(
        default_factory=list,
        max_length=MAX_EVIDENCE_ITEMS,
    )


class CalculatePreferenceFitOutput(ContractModel):
    """Preference results for every candidate, including coverage."""

    # One soft-preference assessment per candidate program.
    fits: list[PreferenceFit] = Field(max_length=MAX_CANDIDATES)


class CandidateForRanking(ContractModel):
    """Validated deterministic inputs used by ``rank_programs``."""

    program: ProgramSummary
    requirements: RequirementAssessment
    # Soft-preference assessment; it never determines candidate eligibility.
    preference_fit: PreferenceFit
    # Academic, research, and career relevance normalized to a 0-100 scale.
    relevance_score: float = Field(ge=0, le=100)


class RankProgramsInput(ContractModel):
    """Candidate components to combine using a versioned score policy."""

    candidates: list[CandidateForRanking] = Field(
        min_length=1,
        max_length=MAX_CANDIDATES,
    )
    # Requested shortlist size, bounded by the public result contract.
    result_limit: int = Field(default=MAX_RESULTS, ge=1, le=MAX_RESULTS)
    # Version of the deterministic weights and tie-breaking policy.
    score_version: Literal["deterministic-v1"] = "deterministic-v1"


class RankProgramsOutput(ContractModel):
    """Deterministically ranked results using the public result contract."""

    # Version actually used to produce the returned ordering.
    score_version: Literal["deterministic-v1"] = "deterministic-v1"
    results: list[ProgramMatchResult] = Field(max_length=MAX_RESULTS)
