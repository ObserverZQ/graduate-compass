"""Public deterministic handlers for the matching agent's bounded tools."""

from apps.api.services.matching.data import (
    ProfileNotFoundError,
    ProfileNotReviewedError,
    get_program_details,
    load_reviewed_profile,
    search_programs,
)
from apps.api.services.matching.preferences import (
    calculate_preference_fit,
    preference_criteria_from_profile,
)
from apps.api.services.matching.ranking import rank_programs
from apps.api.services.matching.requirements import assess_requirements

__all__ = [
    "ProfileNotFoundError",
    "ProfileNotReviewedError",
    "assess_requirements",
    "calculate_preference_fit",
    "get_program_details",
    "load_reviewed_profile",
    "preference_criteria_from_profile",
    "rank_programs",
    "search_programs",
]
