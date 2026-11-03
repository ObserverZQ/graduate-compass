"""The matching workflow reads like the applicant's journey through the tools.

It loads a reviewed profile, finds programs, compares requirements and
preferences, then hands explicit results to recommendations.py for ranking.
The router and SSE adapter do not know the matching rules.
"""

import logging
import time
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from apps.api.schemas.agent_tools import (
    MAX_CANDIDATES, MAX_RESULTS, AssessRequirementsInput,
    CalculatePreferenceFitInput, GetProgramDetailsInput, SearchProgramsInput,
)
from apps.api.schemas.match import (
    FiltersAppliedEvent, MatchErrorCode, MatchEvent, MatchStage,
    ProfileLoadedEvent, RunStartedEvent, WarningCode, WarningEvent,
)
from apps.api.schemas.profile import ApplicantProfile
from apps.api.services.profile.profile_save_load import (
    ProfileNotFoundError, ProfileNotReviewedError, load_reviewed_profile,
)
from apps.api.services.matching.event_writer import EventWriter, report_progress
from apps.api.services.matching.get_program_data import get_program_details
from apps.api.services.matching.preferences import (
    calculate_preference_fit, preference_criteria_from_profile,
)
from apps.api.services.matching.requirements import assess_requirements
from apps.api.services.matching.retrieval import search_programs
from apps.api.services.matching.recommendations import emit_results


logger = logging.getLogger(__name__)
SCORE_VERSION = "deterministic-v1"


async def iter_match_events(session_id: UUID) -> AsyncIterator[MatchEvent]:
    """Run the matching steps in order and end with results or one safe error."""

    writer = EventWriter()
    yield RunStartedEvent(
        run_id=writer.run_id, sequence=writer.next(),
        message="Starting your personalized program review.",
        score_version=SCORE_VERSION, result_limit=MAX_RESULTS,
        explanation_mode="deterministic",
    )
    try:
        # The profile is already confirmed by the applicant; raw PDF text is
        # intentionally absent from this matching boundary.
        started = time.perf_counter()
        yield writer.started(MatchStage.PROFILE, "Loading the profile and preferences you reviewed.")
        profile = await load_reviewed_profile(session_id)
        criteria = preference_criteria_from_profile(profile)
        academic = profile.gpa is not None and profile.gpa_base is not None
        language = any(value is not None for value in (
            profile.toefl_scale_6, profile.toefl_scale_120, profile.ielts,
        ))
        yield ProfileLoadedEvent(
            run_id=writer.run_id, sequence=writer.next(),
            message="Your profile is ready. Missing information becomes uncertainty.",
            preference_count=len(criteria), has_academic_evidence=academic,
            has_language_evidence=language,
            experience_item_count=len(profile.work_experiences) + len(profile.research_experiences),
        )
        if not academic or not language:
            missing = []
            if not academic:
                missing.append("a comparable GPA")
            if not language:
                missing.append("a language-test score")
            yield WarningEvent(
                run_id=writer.run_id, sequence=writer.next(),
                stage=MatchStage.PROFILE, code=WarningCode.MISSING_PROFILE_DATA,
                message=f"Your profile lacks {' and '.join(missing)}. Affected comparisons are uncertain.",
            )
        yield writer.finished(MatchStage.PROFILE, "Finished preparing your reviewed profile.", started)

        started = time.perf_counter()
        yield writer.started(MatchStage.DISCOVERY, "Finding programs related to your requested degree and profile.")
        search = await search_programs(SearchProgramsInput(
            query=_search_query(profile),
            degree_filters=[degree.value for degree in profile.target_degrees],
            location_filters=[],  # Location is a preference, so it cannot remove programs.
            limit=MAX_CANDIDATES,
        ))
        yield writer.finished(
            MatchStage.DISCOVERY,
            f"Found {search.total_considered} programs to evaluate.",
            started, search.total_considered,
        )

        started = time.perf_counter()
        yield writer.started(
            MatchStage.ELIGIBILITY,
            "Checking required degrees. Preferences affect fit but never remove a program.",
        )
        count = len(search.candidates)
        yield FiltersAppliedEvent(
            run_id=writer.run_id, sequence=writer.next(),
            message=f"{count} of {search.total_considered} programs meet your degree filters.",
            program_count=search.total_considered, eligible_count=count,
            excluded_count=search.excluded_by_hard_constraints,
        )
        yield writer.finished(MatchStage.ELIGIBILITY, f"{count} programs remain.", started, count)
        if not count:
            yield writer.error(
                MatchErrorCode.NO_ELIGIBLE_PROGRAMS,
                "No programs match your required degree. Try widening it.", False,
            )
            return

        started = time.perf_counter()
        yield writer.started(MatchStage.REQUIREMENTS, "Comparing your evidence with published requirements.")
        details = await get_program_details(GetProgramDetailsInput(
            program_ids=[candidate.program_id for candidate in search.candidates],
        ))
        if details.missing_program_ids:
            yield WarningEvent(
                run_id=writer.run_id, sequence=writer.next(),
                stage=MatchStage.REQUIREMENTS, code=WarningCode.MISSING_PROGRAM_DATA,
                message=f"Skipped {len(details.missing_program_ids)} programs with unavailable details.",
            )
        if not details.programs:
            yield writer.error(
                MatchErrorCode.NO_ELIGIBLE_PROGRAMS,
                "No programs have enough published information to compare.", False,
            )
            return
        assessments = []
        for index, program in enumerate(details.programs, 1):
            assessments.extend(assess_requirements(AssessRequirementsInput(
                applicant=profile, programs=[program],
            )).assessments)
            if report_progress(index, len(details.programs)):
                yield writer.progress(
                    MatchStage.REQUIREMENTS,
                    f"Reviewed requirements for {index} of {len(details.programs)} programs.",
                    index, len(details.programs),
                )
        yield writer.finished(MatchStage.REQUIREMENTS, "Identified strengths, gaps, and uncertainties.", started, len(assessments))

        started = time.perf_counter()
        yield writer.started(
            MatchStage.PREFERENCES,
            "Comparing your preferences. They affect fit but never remove programs.",
        )
        fits = []
        for index, program in enumerate(details.programs, 1):
            fits.extend(calculate_preference_fit(CalculatePreferenceFitInput(
                preferences=criteria, programs=[program],
            )).fits)
            if report_progress(index, len(details.programs)):
                yield writer.progress(
                    MatchStage.PREFERENCES,
                    f"Compared preferences for {index} of {len(details.programs)} programs.",
                    index, len(details.programs),
                )
        yield writer.finished(MatchStage.PREFERENCES, "Finished comparing preferences.", started, len(fits))

        async for event in emit_results(writer, search.candidates, details.programs, assessments, fits):
            yield event
    except ProfileNotFoundError:
        yield writer.error(MatchErrorCode.PROFILE_NOT_FOUND, "We could not find this profile. Upload your resume again.", False)
    except ProfileNotReviewedError:
        yield writer.error(MatchErrorCode.PROFILE_NOT_REVIEWED, "Review and save your profile before requesting matches.", False)
    except SQLAlchemyError:
        logger.exception("Database failure during matching run %s", writer.run_id)
        yield writer.error(MatchErrorCode.DATABASE_UNAVAILABLE, "Program data is temporarily unavailable. Please try again.", True)
    except Exception:
        logger.exception("Unexpected failure during matching run %s", writer.run_id)
        yield writer.error(MatchErrorCode.MATCHING_FAILED, "We could not finish matching. Please try again.", True)


def _search_query(profile: ApplicantProfile) -> str:
    """Use reviewed interests and experience as bounded search text."""

    parts = [degree.value for degree in profile.target_degrees]
    parts.extend(profile.research_interests)
    for experience in profile.research_experiences + profile.work_experiences:
        parts.extend(value for value in (experience.title, experience.description) if value)
    return (" ".join(parts).strip() or "graduate study")[:2000]
