"""Preference scoring aggregates individual comparisons without filtering.

preference_rules.py compares each criterion; this module applies importance
weights and returns evidence coverage for the matching workflow.
"""

from apps.api.schemas.agent_tools import (
    CalculatePreferenceFitInput,
    CalculatePreferenceFitOutput,
    EvidenceConfidence,
    PreferenceComponent,
    PreferenceCriterion,
    PreferenceFit,
    PreferenceImportance,
)
from apps.api.schemas.profile import ApplicantProfile, CareerGoal
from apps.api.services.matching.preference_rules import _assess_criterion


_IMPORTANCE_POINTS = {
    PreferenceImportance.LOW: 1.0,
    PreferenceImportance.MEDIUM: 2.0,
    PreferenceImportance.HIGH: 3.0,
}
def preference_criteria_from_profile(
    profile: ApplicantProfile,
) -> list[PreferenceCriterion]:
    """Adapt canonical profile preferences to the agent tool's generic input.

    The current UI does not collect importance, so each expressed preference
    receives the documented medium default. This adapter can later accept user
    weights without changing ``calculate_preference_fit``.
    """

    criteria: list[PreferenceCriterion] = []
    if profile.preferences.locations:
        criteria.append(
            PreferenceCriterion(
                key="locations",
                values=profile.preferences.locations,
            )
        )
    if profile.preferences.climate is not None:
        criteria.append(
            PreferenceCriterion(
                key="climate",
                values=[profile.preferences.climate.value],
            )
        )
    if profile.preferences.budget is not None:
        criteria.append(
            PreferenceCriterion(
                key="budget",
                values=[profile.preferences.budget.value],
            )
        )
    if (
        profile.preferences.career_goal is not None
        and profile.preferences.career_goal != CareerGoal.UNDECIDED
    ):
        criteria.append(
            PreferenceCriterion(
                key="career_goal",
                values=[profile.preferences.career_goal.value],
            )
        )
    if profile.research_interests:
        criteria.append(
            PreferenceCriterion(
                key="research_interests",
                values=profile.research_interests,
            )
        )
    return criteria


def calculate_preference_fit(
    payload: CalculatePreferenceFitInput,
) -> CalculatePreferenceFitOutput:
    """Score expressed preferences without excluding candidate programs."""

    fits: list[PreferenceFit] = []
    for program in payload.programs:
        components: list[PreferenceComponent] = []
        uncertainties: list[str] = []
        available_points = 0.0
        earned_points = 0.0
        usable_count = 0

        for criterion in payload.preferences:
            assessment = _assess_criterion(criterion, program)
            max_points = _IMPORTANCE_POINTS[criterion.importance]
            points = max_points * max(0.0, min(1.0, assessment.ratio))
            components.append(
                PreferenceComponent(
                    key=criterion.key,
                    importance=criterion.importance,
                    points=round(points, 3),
                    max_points=max_points,
                    status=assessment.status,
                    evidence=assessment.evidence,
                    data_confidence=(
                        EvidenceConfidence.HIGH
                        if assessment.usable
                        else EvidenceConfidence.LOW
                    ),
                )
            )

            if assessment.usable:
                usable_count += 1
                available_points += max_points
                earned_points += points
            else:
                uncertainties.append(assessment.evidence)

        # Unknown program data is excluded from the denominator. The separate
        # coverage value prevents a high score based on one field from looking
        # as well-supported as a score covering every expressed preference.
        score = (
            round(100 * earned_points / available_points, 2)
            if available_points
            else None
        )
        coverage = (
            usable_count / len(payload.preferences) if payload.preferences else 0
        )
        fits.append(
            PreferenceFit(
                program_id=program.program_id,
                score=score,
                evidence_coverage=coverage,
                components=components,
                uncertainties=uncertainties,
            )
        )

    return CalculatePreferenceFitOutput(fits=fits)
