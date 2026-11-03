"""Preference rules compare one stated preference with one program.

preferences.py owns aggregate scores; these helpers own individual comparisons.
"""

import re
from dataclasses import dataclass

from apps.api.schemas.agent_tools import PreferenceCriterion, ProgramDetails
from apps.api.schemas.match import FactorStatus


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_TOKEN_STOP_WORDS = {"and", "for", "from", "into", "the", "with"}
_US_ALIASES = {"america", "united states", "united states of america", "us", "usa"}


@dataclass(frozen=True)
class _CriterionAssessment:
    """One preference comparison before its importance changes the score."""

    status: FactorStatus
    ratio: float
    evidence: str
    usable: bool


def _assess_criterion(
    criterion: PreferenceCriterion,
    program: ProgramDetails,
) -> _CriterionAssessment:
    """Route a stated preference to the comparison for that field."""

    key = criterion.key.casefold().replace("-", "_").replace(" ", "_")
    if key in {"location", "locations"}:
        return _assess_location(criterion, program)
    if key == "climate":
        return _assess_climate(criterion, program)
    if key == "budget":
        return _assess_budget(criterion, program)
    if key in {"career", "career_goal"}:
        return _assess_career(criterion, program)
    if key in {"interest", "interests", "research_interest", "research_interests"}:
        return _assess_interests(criterion, program)
    return _CriterionAssessment(
        status=FactorStatus.UNCERTAIN,
        ratio=0,
        evidence=f"Preference criterion {criterion.key!r} is not supported yet.",
        usable=False,
    )


def _assess_location(
    criterion: PreferenceCriterion,
    program: ProgramDetails,
) -> _CriterionAssessment:
    """Compare preferred countries with the program's published country."""

    preferred = {_canonical_location(value) for value in criterion.values}
    matches = _canonical_location(program.country) in preferred
    return _known_result(
        matches,
        (
            f"The program location {program.country} matches a stated preference."
            if matches
            else f"The program location {program.country} differs from the stated preferences."
        ),
    )


def _assess_climate(
    criterion: PreferenceCriterion,
    program: ProgramDetails,
) -> _CriterionAssessment:
    """Compare climate wording, or mark missing climate as uncertain."""

    if not program.climate:
        return _unknown("The program record does not include climate information.")
    preferred = {value.casefold().strip() for value in criterion.values}
    matches = any(value in program.climate.casefold() for value in preferred)
    return _known_result(
        matches,
        (
            f"The published climate ({program.climate}) matches the stated preference."
            if matches
            else f"The published climate ({program.climate}) differs from the stated preference."
        ),
    )


def _assess_budget(
    criterion: PreferenceCriterion,
    program: ProgramDetails,
) -> _CriterionAssessment:
    """Compare published annual tuition with the applicant's budget band."""

    if program.annual_tuition_and_fees is None:
        return _unknown(
            "The program does not publish annual tuition and mandatory fees."
        )

    budget_text = " ".join(criterion.values).casefold()
    if "under_20k" in budget_text or "< $20k" in budget_text:
        maximum: int | None = 20_000
    elif "20k_to_40k" in budget_text or "20-40k" in budget_text or "20–40k" in budget_text:
        maximum = 40_000
    elif "over_40k" in budget_text or "40k+" in budget_text or "no limit" in budget_text:
        maximum = None
    else:
        return _unknown("The stated budget could not be interpreted safely.")

    matches = maximum is None or program.annual_tuition_and_fees <= maximum
    evidence = (
        f"Published annual tuition and fees are ${program.annual_tuition_and_fees:,}, "
        + ("within the stated budget." if matches else f"above the ${maximum:,} budget.")
    )
    return _known_result(matches, evidence)


def _assess_career(
    criterion: PreferenceCriterion,
    program: ProgramDetails,
) -> _CriterionAssessment:
    """Use published PhD or employment data for the stated career goal."""

    goals = {value.casefold().strip() for value in criterion.values}
    if goals & {"phd_research", "phd / research"}:
        if not program.phd_pathway_detail:
            return _unknown(
                "The program does not publish evidence about preparation for PhD study."
            )
        return _known_result(
            True,
            "The program publishes a pathway or preparation details for PhD study.",
        )

    if goals & {"industry", "industry job"}:
        if program.job_placement_score is None:
            return _unknown(
                "The program record does not include an employment-outcomes score."
            )
        # Seed sources use different numeric scales. Detect the likely scale
        # before converting the value into a bounded 0-1 preference ratio.
        raw_score = program.job_placement_score
        denominator = 1 if raw_score <= 1 else 10 if raw_score <= 10 else 100
        ratio = max(0.0, min(1.0, raw_score / denominator))
        status = (
            FactorStatus.MATCH
            if ratio >= 0.7
            else FactorStatus.NEUTRAL
            if ratio >= 0.4
            else FactorStatus.GAP
        )
        return _CriterionAssessment(
            status=status,
            ratio=ratio,
            evidence="The employment-outcomes score was normalized for comparison.",
            usable=True,
        )

    return _unknown("The stated career goal could not be interpreted safely.")


def _assess_interests(
    criterion: PreferenceCriterion,
    program: ProgramDetails,
) -> _CriterionAssessment:
    """Measure shared research words in published program topics."""

    if not program.research_areas:
        return _unknown("The program does not publish research-area evidence.")
    applicant_tokens = _tokens(" ".join(criterion.values))
    program_tokens = _tokens(program.research_areas)
    overlap = applicant_tokens & program_tokens
    ratio = len(overlap) / max(1, min(3, len(applicant_tokens)))
    matches = bool(overlap)
    return _CriterionAssessment(
        status=FactorStatus.MATCH if matches else FactorStatus.GAP,
        ratio=min(1.0, ratio) if matches else 0,
        evidence=(
            f"Shared research terms include {', '.join(sorted(overlap)[:3])}."
            if matches
            else "No direct research-term overlap was found in the published areas."
        ),
        usable=True,
    )


def _known_result(matches: bool, evidence: str) -> _CriterionAssessment:
    """Represent a supported yes/no comparison with its evidence."""

    return _CriterionAssessment(
        status=FactorStatus.MATCH if matches else FactorStatus.GAP,
        ratio=1.0 if matches else 0.0,
        evidence=evidence,
        usable=True,
    )


def _unknown(evidence: str) -> _CriterionAssessment:
    """Represent a preference whose evidence is unavailable or unclear."""

    return _CriterionAssessment(
        status=FactorStatus.UNCERTAIN,
        ratio=0,
        evidence=evidence,
        usable=False,
    )


def _canonical_location(value: str) -> str:
    """Treat common US names as the same location."""

    normalized = " ".join(value.casefold().split())
    return "united states" if normalized in _US_ALIASES else normalized


def _tokens(value: str) -> set[str]:
    """Extract useful words for research-interest comparison."""

    return {
        token
        for token in _TOKEN_PATTERN.findall(value.casefold())
        if len(token) >= 3 and token not in _TOKEN_STOP_WORDS
    }
