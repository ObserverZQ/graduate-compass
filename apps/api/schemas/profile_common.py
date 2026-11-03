"""Shared profile validators, enum values, and size limits.

profile.py imports these definitions so its models use the same normalization.
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
