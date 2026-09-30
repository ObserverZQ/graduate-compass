"""Stable deterministic ranking tool for previously assessed candidates."""

from apps.api.schemas.agent_tools import (
    CandidateForRanking,
    RankProgramsInput,
    RankProgramsOutput,
)
from apps.api.schemas.match import (
    FactorKey,
    FactorStatus,
    ProgramMatchResult,
    ScoreFactor,
)


RELEVANCE_WEIGHT = 40.0
REQUIREMENTS_WEIGHT = 35.0
PREFERENCE_WEIGHT = 25.0


def rank_programs(payload: RankProgramsInput) -> RankProgramsOutput:
    """Combine bounded components and apply reproducible tie-breaking.

    Tool results are linked by program ID before any arithmetic. This prevents
    an orchestration bug from attaching one program's evidence to another
    program's public result.
    """

    results = [_rankable_result(candidate, payload.score_version) for candidate in payload.candidates]
    results.sort(
        key=lambda result: (
            -result.fit_score,
            result.university.casefold(),
            result.name.casefold(),
            str(result.program_id),
        )
    )
    ranked = [
        result.model_copy(update={"rank": rank})
        for rank, result in enumerate(results[: payload.result_limit], start=1)
    ]
    return RankProgramsOutput(
        score_version=payload.score_version,
        results=ranked,
    )


def _rankable_result(
    candidate: CandidateForRanking,
    score_version: str,
) -> ProgramMatchResult:
    program_id = candidate.program.program_id
    if candidate.requirements.program_id != program_id:
        raise ValueError("requirement assessment program_id does not match candidate")
    if candidate.preference_fit.program_id != program_id:
        raise ValueError("preference fit program_id does not match candidate")

    requirement_score = _requirement_score(candidate)
    preference_score = (
        candidate.preference_fit.score
        if candidate.preference_fit.score is not None
        else 50.0
    )
    relevance_points = RELEVANCE_WEIGHT * candidate.relevance_score / 100
    requirement_points = REQUIREMENTS_WEIGHT * requirement_score / 100
    preference_points = PREFERENCE_WEIGHT * preference_score / 100
    fit_score = round(relevance_points + requirement_points + preference_points)

    factors = [
        ScoreFactor(
            key=FactorKey.INTEREST,
            label="Retrieval relevance",
            points=relevance_points,
            max_points=RELEVANCE_WEIGHT,
            status=_score_status(candidate.relevance_score),
            evidence=(
                candidate.program.retrieval_evidence[0].statement
                if candidate.program.retrieval_evidence
                else "No direct retrieval evidence was available."
            ),
        ),
        ScoreFactor(
            key=FactorKey.ACADEMIC,
            label="Published requirement readiness",
            points=requirement_points,
            max_points=REQUIREMENTS_WEIGHT,
            status=_requirement_status(candidate),
            evidence=(
                f"{len(candidate.requirements.strengths)} strength(s), "
                f"{len(candidate.requirements.gaps)} gap(s), and "
                f"{len(candidate.requirements.uncertainties)} uncertainty item(s)."
            ),
        ),
        ScoreFactor(
            key=FactorKey.CAREER,
            label="Soft-preference alignment",
            points=preference_points,
            max_points=PREFERENCE_WEIGHT,
            status=(
                FactorStatus.NEUTRAL
                if candidate.preference_fit.score is None
                else _score_status(candidate.preference_fit.score)
            ),
            evidence=(
                "No applicable preference was expressed."
                if candidate.preference_fit.score is None
                else f"Preference evidence coverage is "
                f"{candidate.preference_fit.evidence_coverage:.0%}."
            ),
        ),
    ]

    preference_strengths = [
        component.evidence
        for component in candidate.preference_fit.components
        if component.status == FactorStatus.MATCH
    ]
    preference_gaps = [
        component.evidence
        for component in candidate.preference_fit.components
        if component.status == FactorStatus.GAP
    ]
    strengths = candidate.requirements.strengths + preference_strengths
    gaps = candidate.requirements.gaps + preference_gaps
    uncertainties = (
        candidate.requirements.uncertainties
        + candidate.preference_fit.uncertainties
    )

    supporting_evidence = (
        strengths
        + [evidence.statement for evidence in candidate.program.retrieval_evidence]
        + uncertainties
    )[:3]
    if strengths:
        why_match = f"Strongest available evidence: {strengths[0]}"
    elif candidate.program.retrieval_evidence:
        why_match = "The program was retained by relevant published programme evidence."
    else:
        why_match = "Published evidence is limited; review the uncertainties before deciding."

    if gaps:
        next_action = f"Confirm this gap on the official program page: {gaps[0]}"
    elif uncertainties:
        next_action = f"Verify this missing information: {uncertainties[0]}"
    else:
        next_action = "Review the official curriculum and application requirements."

    return ProgramMatchResult(
        # Temporary rank is replaced after sorting and applying result_limit.
        rank=1,
        program_id=program_id,
        name=candidate.program.name,
        university=candidate.program.university,
        country=candidate.program.country,
        degree_type=candidate.program.degree_type,
        fit_score=max(0, min(100, fit_score)),
        score_version=score_version,
        why_match=why_match,
        supporting_evidence=supporting_evidence,
        factors=factors,
        strengths=strengths,
        gaps=gaps,
        uncertainties=uncertainties,
        next_action=next_action,
        official_website=candidate.program.official_website,
    )


def _requirement_score(candidate: CandidateForRanking) -> float:
    strengths = len(candidate.requirements.strengths)
    gaps = len(candidate.requirements.gaps)
    known = strengths + gaps
    # Unknown evidence is neutral rather than a failure; its visibility is
    # preserved through the uncertainty list and evidence-confidence field.
    return 100 * strengths / known if known else 50.0


def _requirement_status(candidate: CandidateForRanking) -> FactorStatus:
    if candidate.requirements.strengths and not candidate.requirements.gaps:
        return FactorStatus.MATCH
    if candidate.requirements.gaps and not candidate.requirements.strengths:
        return FactorStatus.GAP
    if not candidate.requirements.strengths and not candidate.requirements.gaps:
        return FactorStatus.UNCERTAIN
    return FactorStatus.NEUTRAL


def _score_status(score: float) -> FactorStatus:
    if score >= 70:
        return FactorStatus.MATCH
    if score >= 40:
        return FactorStatus.NEUTRAL
    return FactorStatus.GAP
