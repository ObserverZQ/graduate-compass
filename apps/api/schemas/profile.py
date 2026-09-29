"""Strict domain contracts for extracted and reviewed applicant profiles.

This module contains data models only. Normalization, persistence, API routing,
matching logic, and model calls belong in later implementation steps.
"""

import re
from datetime import datetime
# StrEnum keeps enum values JSON-compatible strings.
from enum import StrEnum
# Any is limited to raw pre-validation inputs. Literal locks version/status
# fields to exact wire values rather than accepting arbitrary strings.
from typing import Any, Literal
# UUID validates session identifiers before they reach persistence code.
from uuid import UUID

from pydantic import (
    # AliasChoices accepts the canonical snake_case key and the existing
    # frontend camelCase key during a compatibility window.
    AliasChoices,
    BaseModel,
    ConfigDict,
    # Field attaches bounds, collection limits, and safe default factories to
    # type annotations without implementing runtime business logic.
    Field,
    # field_validator normalizes one field before/after type validation;
    # model_validator enforces invariants involving multiple fields.
    field_validator,
    model_validator,
)


MAX_EXPERIENCE_ITEMS = 50
MAX_PUBLICATIONS = 50
MAX_PREFERENCE_LOCATIONS = 10
MAX_RESEARCH_INTERESTS = 20
MAX_PROFILE_TEXT_LENGTH = 5_000  # Underscores improve readability only.


def _empty_to_none(value: Any) -> Any:
    """Convert blank form and model strings to a single missing-value shape."""

    if isinstance(value, str) and not value.strip():
        return None
    return value


def _normalized_unique_text(values: Any, *, omitted: set[str] | None = None) -> list[str]:
    """Trim, remove blanks, and deduplicate text while preserving its order."""

    # A missing optional collection has the same canonical form as an empty
    # collection. This also makes LLM-produced null values safe to consume.
    if values is None:
        return []

    # Accept a comma-separated form from simple text inputs while keeping the
    # canonical model representation as a list of strings.
    if isinstance(values, str):
        values = values.split(",")

    # Reject dictionaries, numbers, and other iterables instead of silently
    # converting malformed payloads into surprising preference values.
    if not isinstance(values, list):
        raise ValueError("expected a list of text values")

    # Comparison uses case-insensitive keys, but output preserves the first
    # user-facing spelling so labels such as "USA" are not rewritten.
    omitted = omitted or set()
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        # Mixed-type lists usually indicate frontend or model-output drift and
        # should fail at the trust boundary rather than becoming text via str().
        if not isinstance(value, str):
            raise ValueError("each value must be text")

        # Collapse repeated internal whitespace as well as trimming both ends.
        text = " ".join(value.split())
        key = text.casefold()

        # Skip blanks, explicit no-preference labels supplied by the caller,
        # and later duplicates while retaining the first occurrence's order.
        if text and key not in omitted and key not in seen:
            normalized.append(text)
            seen.add(key)
    return normalized


class ProfileContract(BaseModel):
    """Reject undeclared fields at the applicant-profile trust boundary."""

    # Type annotations such as ``str | None`` mean the field may be missing;
    # they do not permit undeclared keys because extra="forbid" remains active.
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ReviewStatus(StrEnum):
    """Whether extracted facts have been confirmed by the applicant."""

    EXTRACTED = "extracted"
    REVIEWED = "reviewed"


class ProfileSource(StrEnum):
    """Origin of the latest profile representation."""

    RESUME_EXTRACTION = "resume_extraction"
    USER_REVIEW = "user_review"


class DegreeType(StrEnum):
    """Canonical degree families used by filtering and matching."""

    MASTERS = "masters"
    PHD = "phd"


class ClimatePreference(StrEnum):
    WARM = "warm"
    COLD = "cold"
    MILD = "mild"


class BudgetPreference(StrEnum):
    UNDER_20K = "under_20k"
    FROM_20K_TO_40K = "20k_to_40k"
    OVER_40K = "over_40k"


class CareerGoal(StrEnum):
    PHD_RESEARCH = "phd_research"
    INDUSTRY = "industry"
    UNDECIDED = "undecided"


def normalize_degree(value: str) -> DegreeType:
    """Map common degree spellings to a stable matching value."""

    compact = re.sub(r"[^a-z]", "", value.casefold())
    masters = {
        "ma",
        "master",
        "masters",
        "masterofarts",
        "masterofengineering",
        "masterofscience",
        "meng",
        "ms",
        "msc",
    }
    doctoral = {
        "doctorofphilosophy",
        "doctoral",
        "doctorate",
        "phd",
    }
    if compact in masters:
        return DegreeType.MASTERS
    if compact in doctoral:
        return DegreeType.PHD
    raise ValueError(f"unsupported target degree: {value!r}")


class ProfileProvenance(ProfileContract):
    """Minimal lineage metadata kept separate from applicant evidence."""

    source: ProfileSource
    review_status: ReviewStatus
    # Time the applicant confirmed the profile; absent before review.
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_source_and_status(self) -> "ProfileProvenance":
        expected_status = {
            ProfileSource.RESUME_EXTRACTION: ReviewStatus.EXTRACTED,
            ProfileSource.USER_REVIEW: ReviewStatus.REVIEWED,
        }[self.source]
        if self.review_status != expected_status:
            raise ValueError("profile source and review status are inconsistent")
        if self.review_status == ReviewStatus.EXTRACTED and self.reviewed_at is not None:
            raise ValueError("an extracted profile cannot have reviewed_at")
        return self


class WorkExperience(ProfileContract):
    company: str | None = Field(default=None, max_length=300)
    title: str | None = Field(default=None, max_length=300)
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    description: str | None = Field(
        default=None,
        max_length=MAX_PROFILE_TEXT_LENGTH,
    )

    _normalize_blank_text = field_validator(
        "company",
        "title",
        "start_date",
        "end_date",
        "description",
        mode="before",
    )(_empty_to_none)


class ResearchExperience(ProfileContract):
    institution: str | None = Field(default=None, max_length=300)
    title: str | None = Field(default=None, max_length=300)
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    description: str | None = Field(
        default=None,
        max_length=MAX_PROFILE_TEXT_LENGTH,
    )

    _normalize_blank_text = field_validator(
        "institution",
        "title",
        "start_date",
        "end_date",
        "description",
        mode="before",
    )(_empty_to_none)


class Publication(ProfileContract):
    title: str | None = Field(default=None, max_length=500)
    venue: str | None = Field(default=None, max_length=300)
    year: int | str | None = None
    authors: str | None = Field(default=None, max_length=1_000)

    _normalize_blank_text = field_validator(
        "title",
        "venue",
        "year",
        "authors",
        mode="before",
    )(_empty_to_none)

    @field_validator("year")
    @classmethod
    def normalize_year(cls, value: int | str | None) -> int | str | None:
        if isinstance(value, str) and value.isdigit():
            return int(value)
        if isinstance(value, str) and len(value) > 40:
            raise ValueError("publication year or status is too long")
        return value


class AcademicProfile(ProfileContract):
    """Academic facts used later for requirement assessment."""

    target_degrees: list[DegreeType] = Field(default_factory=list, max_length=10)
    gpa: float | None = Field(default=None, ge=0, le=100)
    # Denominator of the applicant's GPA scale, such as 4.0, 5.0, or 100.
    gpa_base: float | None = Field(default=None, gt=0, le=100)
    # Current field combines institution name and optional ranking description.
    gpa_ranking: str | None = Field(default=None, max_length=300)
    # TOEFL score on the newer six-point scale.
    toefl_scale_6: float | None = Field(default=None, ge=0, le=6)
    # TOEFL score on the legacy 120-point scale.
    toefl_scale_120: int | None = Field(default=None, ge=0, le=120)
    ielts: float | None = Field(default=None, ge=0, le=9)

    @field_validator("target_degrees", mode="before")
    @classmethod
    def normalize_target_degrees(cls, value: Any) -> list[DegreeType]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, list):
            raise ValueError("target_degrees must be a list")
        normalized = [normalize_degree(str(degree)) for degree in value]
        return list(dict.fromkeys(normalized))

    _normalize_blank_ranking = field_validator("gpa_ranking", mode="before")(
        _empty_to_none
    )

    @model_validator(mode="after")
    def validate_gpa_scale(self) -> "AcademicProfile":
        if self.gpa is not None and self.gpa_base is not None and self.gpa > self.gpa_base:
            raise ValueError("gpa cannot exceed gpa_base")
        return self


class ApplicantPreferences(ProfileContract):
    """Soft preferences that influence ranking but never eligibility."""

    locations: list[str] = Field(
        default_factory=list,
        max_length=MAX_PREFERENCE_LOCATIONS,
    )
    climate: ClimatePreference | None = None
    budget: BudgetPreference | None = None
    career_goal: CareerGoal | None = Field(
        default=None,
        validation_alias=AliasChoices("career_goal", "careerGoal"),
    )

    @field_validator("locations", mode="before")
    @classmethod
    def normalize_locations(cls, value: Any) -> list[str]:
        return _normalized_unique_text(value, omitted={"no preference"})

    @field_validator("climate", mode="before")
    @classmethod
    def normalize_climate(cls, value: Any) -> Any:
        if value is None:
            return None
        token = str(value).strip().casefold()
        return None if token in {"", "no preference"} else token

    @field_validator("budget", mode="before")
    @classmethod
    def normalize_budget(cls, value: Any) -> Any:
        if value is None:
            return None
        token = str(value).strip().casefold()
        return {
            "": None,
            "no limit": None,
            "< $20k / yr": BudgetPreference.UNDER_20K,
            "$20–40k / yr": BudgetPreference.FROM_20K_TO_40K,
            "$20-40k / yr": BudgetPreference.FROM_20K_TO_40K,
            "$40k+ / yr": BudgetPreference.OVER_40K,
        }.get(token, token)

    @field_validator("career_goal", mode="before")
    @classmethod
    def normalize_career_goal(cls, value: Any) -> Any:
        if value is None:
            return None
        token = str(value).strip().casefold()
        return {
            "": None,
            "phd / research": CareerGoal.PHD_RESEARCH,
            "industry job": CareerGoal.INDUSTRY,
            "not sure yet": CareerGoal.UNDECIDED,
        }.get(token, token)


class ApplicantProfileFields(AcademicProfile):
    """Applicant evidence shared by extraction and reviewed-profile models."""

    name: str | None = Field(default=None, max_length=200)
    research_interests: list[str] = Field(
        default_factory=list,
        max_length=MAX_RESEARCH_INTERESTS,
    )
    work_experiences: list[WorkExperience] = Field(
        default_factory=list,
        max_length=MAX_EXPERIENCE_ITEMS,
    )
    research_experiences: list[ResearchExperience] = Field(
        default_factory=list,
        max_length=MAX_EXPERIENCE_ITEMS,
    )
    publications: list[Publication] = Field(
        default_factory=list,
        max_length=MAX_PUBLICATIONS,
    )

    _normalize_blank_name = field_validator("name", mode="before")(_empty_to_none)

    @field_validator("research_interests", mode="before")
    @classmethod
    def normalize_research_interests(cls, value: Any) -> list[str]:
        return _normalized_unique_text(value)

    @field_validator(
        "work_experiences",
        "research_experiences",
        "publications",
        mode="before",
    )
    @classmethod
    def normalize_missing_collections(cls, value: Any) -> Any:
        return [] if value is None else value


class ExtractedApplicantProfile(ApplicantProfileFields):
    """Validated résumé extraction that still requires applicant review."""

    # Literal makes every v1 payload carry exactly the string "1".
    schema_version: Literal["1"] = "1"
    provenance: ProfileProvenance = Field(
        default_factory=lambda: ProfileProvenance(
            source=ProfileSource.RESUME_EXTRACTION,
            review_status=ReviewStatus.EXTRACTED,
        )
    )

    @model_validator(mode="after")
    def require_extraction_provenance(self) -> "ExtractedApplicantProfile":
        """Prevent reviewed data from masquerading as raw extraction output."""

        if self.provenance.source != ProfileSource.RESUME_EXTRACTION:
            raise ValueError("extracted profiles require resume-extraction provenance")
        return self


class ApplicantProfile(ApplicantProfileFields):
    """Canonical profile after applicant review and preference collection."""

    # Keep versioning on top-level documents rather than every nested object.
    schema_version: Literal["1"] = "1"
    session_id: UUID
    preferences: ApplicantPreferences = Field(default_factory=ApplicantPreferences)
    provenance: ProfileProvenance = Field(
        default_factory=lambda: ProfileProvenance(
            source=ProfileSource.USER_REVIEW,
            review_status=ReviewStatus.REVIEWED,
        )
    )

    @model_validator(mode="after")
    def require_reviewed_provenance(self) -> "ApplicantProfile":
        """Keep unreviewed LLM extraction outside the matching boundary."""

        if self.provenance.source != ProfileSource.USER_REVIEW:
            raise ValueError("applicant profiles require user-review provenance")
        return self


class AnalyzeResumeRequest(ProfileContract):
    """Existing analysis request shape, now represented as a strict contract."""

    session_id: UUID
    resume_raw_text: str = Field(min_length=1, max_length=200_000)


class ReviewedProfileResponse(ProfileContract):
    """Small acknowledgement returned after persisting a reviewed profile."""

    session_id: UUID
    status: Literal["ok"] = "ok"
