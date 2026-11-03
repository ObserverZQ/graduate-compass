"""Recommendations turn assessed programs into ranked, explained results.

workflow.py passes explicit tool outputs here; this module joins them by ID,
uses the existing ranking tool, and emits final events for the SSE adapter.
"""

import time
from collections.abc import AsyncIterator

from apps.api.schemas.agent_tools import (
    MAX_RESULTS, CandidateForRanking, PreferenceFit, ProgramDetails,
    ProgramSummary, RankProgramsInput, RequirementAssessment,
)
from apps.api.schemas.match import (
    CandidateExplainedEvent, CandidateScoredEvent, CompleteEvent,
    ExplanationStartedEvent, MatchEvent, MatchStage, WarningCode, WarningEvent,
)
from apps.api.services.matching.event_writer import EventWriter
from apps.api.services.matching.ranking import rank_programs


async def emit_results(
    writer: EventWriter,
    summaries: list[ProgramSummary],
    details: list[ProgramDetails],
    assessments: list[RequirementAssessment],
    fits: list[PreferenceFit],
) -> AsyncIterator[MatchEvent]:
    """Join candidates by ID, rank them, and stream the final result cards."""

    started = time.perf_counter()
    yield writer.started(MatchStage.RANKING, "Combining evidence into transparent fit scores.")
    requirement_by_id = {item.program_id: item for item in assessments}
    preference_by_id = {item.program_id: item for item in fits}
    detailed_ids = {item.program_id for item in details}
    candidates = [
        CandidateForRanking(
            program=summary,
            requirements=requirement_by_id[summary.program_id],
            preference_fit=preference_by_id[summary.program_id],
            relevance_score=100 * (summary.retrieval_score or 0),
        )
        for summary in summaries
        if summary.program_id in detailed_ids
        and summary.program_id in requirement_by_id
        and summary.program_id in preference_by_id
    ]
    if not candidates:
        raise ValueError("no candidate had all required ranking inputs")
    ranking = rank_programs(RankProgramsInput(
        candidates=candidates, result_limit=MAX_RESULTS,
        score_version="deterministic-v1",
    ))
    count = len(ranking.results)
    for index, result in enumerate(ranking.results, 1):
        yield CandidateScoredEvent(
            run_id=writer.run_id, sequence=writer.next(),
            message=f"Scored {result.name} ({index} of {count}).",
            program_id=result.program_id, program_name=result.name,
            processed=index, total=count, fit_score=result.fit_score,
        )
    yield writer.finished(MatchStage.RANKING, f"Selected the strongest {count} matches.", started, count)
    if count < MAX_RESULTS:
        yield WarningEvent(
            run_id=writer.run_id, sequence=writer.next(),
            stage=MatchStage.RANKING, code=WarningCode.FEWER_THAN_EIGHT_RESULTS,
            message=f"Only {count} programs could be fully evaluated, so we are showing all of them.",
        )

    started = time.perf_counter()
    yield writer.started(
        MatchStage.EXPLANATION,
        "Preparing strengths, gaps, uncertainties, and a next step for each match.",
    )
    yield ExplanationStartedEvent(
        run_id=writer.run_id, sequence=writer.next(),
        message="Preparing evidence-backed explanations for your matches.",
        candidate_count=count, mode="deterministic",
    )
    for result in ranking.results:
        yield CandidateExplainedEvent(
            run_id=writer.run_id, sequence=writer.next(),
            message=f"Prepared an explanation for {result.name}.", result=result,
        )
    yield writer.finished(MatchStage.EXPLANATION, "Finished preparing explanations.", started, count)
    yield CompleteEvent(
        run_id=writer.run_id, sequence=writer.next(),
        message="Your matches are ready.", score_version=ranking.score_version,
        results=ranking.results,
        disclaimer=(
            "Fit scores compare available profile, preference, and program evidence. "
            "They are not admission probabilities; verify requirements on official websites."
        ),
    )
