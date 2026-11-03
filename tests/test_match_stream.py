"""Tests coordinate mocked database calls with the real pipeline and SSE adapter.

Database-facing pipeline calls are replaced with fixtures while
the workflow, ranking, event sequencing, and transport framing remain real.
"""

import json
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

# Importing the API creates an async engine but does not connect. This fallback
# keeps contract tests independent from a developer's private environment.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/graduate_compass_test",
)

from apps.api.schemas.agent_tools import (
    GetProgramDetailsOutput,
    ProgramDetails,
    ProgramSummary,
    RetrievalEvidence,
    SearchProgramsOutput,
)
from apps.api.schemas.profile import ApplicantProfile
from apps.api.services.matching import stream, workflow
from apps.api.services.matching import ProfileNotReviewedError


SESSION_ID = UUID("00000000-0000-0000-0000-000000000100")
PROGRAM_IDS = (
    UUID("00000000-0000-0000-0000-000000000201"),
    UUID("00000000-0000-0000-0000-000000000202"),
)


def reviewed_profile() -> ApplicantProfile:
    """Build a reviewed synthetic applicant without using a personal résumé."""
    return ApplicantProfile.model_validate(
        {
            "session_id": SESSION_ID,
            "target_degrees": ["masters"],
            "gpa": 3.8,
            "gpa_base": 4.0,
            "toefl_scale_120": 110,
            "research_interests": ["distributed systems"],
            "work_experiences": [
                {
                    "title": "Frontend Engineer",
                    "description": "Built reliable web applications.",
                }
            ],
            "preferences": {
                "locations": ["United States"],
                "career_goal": "industry",
            },
        }
    )


def program_summaries() -> list[ProgramSummary]:
    """Build public search results used by the pipeline test."""
    return [
        ProgramSummary(
            program_id=program_id,
            name=f"MS in Computer Science {index}",
            university=f"Synthetic University {index}",
            country="United States",
            degree_type="MS",
            retrieval_score=0.9 - index / 10,
            retrieval_evidence=[
                RetrievalEvidence(
                    source_field="research_areas",
                    statement="Distributed systems and reliable software.",
                    relevance_score=0.8,
                )
            ],
            official_website=f"https://example.edu/program-{index}",
        )
        for index, program_id in enumerate(PROGRAM_IDS, start=1)
    ]


def program_details() -> list[ProgramDetails]:
    """Provide published facts for the same synthetic program IDs."""
    return [
        ProgramDetails(
            program_id=summary.program_id,
            name=summary.name,
            university=summary.university,
            country=summary.country,
            degree_type=summary.degree_type,
            research_areas="Distributed systems and reliable software.",
            min_gpa=3.0,
            min_toefl=100,
            job_placement_score=8.0,
            official_website=summary.official_website,
        )
        for summary in program_summaries()
    ]


def parse_events(chunks: list[str]) -> list[tuple[str, dict[str, object]]]:
    """Decode SSE frames so tests can inspect event names and payloads."""
    parsed = []
    for chunk in chunks:
        if chunk.startswith(":"):
            continue
        lines = chunk.strip().splitlines()
        parsed.append(
            (
                lines[0].removeprefix("event: "),
                json.loads(lines[1].removeprefix("data: ")),
            )
        )
    return parsed


class MatchingStreamTests(unittest.IsolatedAsyncioTestCase):
    """Check successful and terminal-error streams without database writes."""

    async def test_success_stream_is_ordered_and_explainable(self) -> None:
        """Check event ordering, results, and non-excluding location preference."""
        summaries = program_summaries()
        load_profile = AsyncMock(return_value=reviewed_profile())
        search = AsyncMock(
            return_value=SearchProgramsOutput(
                candidates=summaries,
                total_considered=2,
                excluded_by_hard_constraints=0,
            )
        )
        get_details = AsyncMock(
            return_value=GetProgramDetailsOutput(programs=program_details())
        )

        with (
            patch.object(workflow, "load_reviewed_profile", load_profile),
            patch.object(workflow, "search_programs", search),
            patch.object(workflow, "get_program_details", get_details),
        ):
            chunks = [
                chunk
                async for chunk in stream.deterministic_match_pipeline(SESSION_ID)
            ]

        events = parse_events(chunks)
        event_names = [name for name, _ in events]
        payloads = [payload for _, payload in events]

        self.assertEqual(event_names[0], "run_started")
        self.assertEqual(event_names[-1], "complete")
        self.assertIn("profile_loaded", event_names)
        self.assertIn("filters_applied", event_names)
        self.assertIn("stage_progress", event_names)
        self.assertEqual(event_names.count("candidate_scored"), 2)
        self.assertEqual(event_names.count("candidate_explained"), 2)
        self.assertTrue(
            any(
                payload.get("code") == "fewer_than_eight_results"
                for payload in payloads
            )
        )
        self.assertEqual(
            [payload["sequence"] for payload in payloads],
            list(range(1, len(payloads) + 1)),
        )
        self.assertEqual(len({payload["run_id"] for payload in payloads}), 1)
        self.assertEqual(payloads[-1]["message"], "Your matches are ready.")
        self.assertEqual(len(payloads[-1]["results"]), 2)

        search_input = search.await_args.args[0]
        self.assertEqual(search_input.degree_filters, ["masters"])
        self.assertEqual(search_input.location_filters, [])

    async def test_no_candidates_ends_with_no_eligible_programs(self) -> None:
        """Stop before detail lookup when degree filtering removes all programs."""
        with (
            patch.object(
                workflow,
                "load_reviewed_profile",
                AsyncMock(return_value=reviewed_profile()),
            ),
            patch.object(
                workflow,
                "search_programs",
                AsyncMock(
                    return_value=SearchProgramsOutput(
                        candidates=[],
                        total_considered=24,
                        excluded_by_hard_constraints=24,
                    )
                ),
            ),
            patch.object(
                workflow,
                "get_program_details",
                AsyncMock(),
            ) as get_details,
        ):
            chunks = [
                chunk
                async for chunk in stream.deterministic_match_pipeline(SESSION_ID)
            ]

        events = parse_events(chunks)
        self.assertEqual(events[-1][0], "error")
        self.assertEqual(events[-1][1]["code"], "no_eligible_programs")
        get_details.assert_not_awaited()

    async def test_unreviewed_profile_returns_safe_terminal_error(self) -> None:
        """Ask for profile review without leaking internal failure details."""
        with patch.object(
            workflow,
            "load_reviewed_profile",
            AsyncMock(side_effect=ProfileNotReviewedError()),
        ):
            chunks = [
                chunk
                async for chunk in stream.deterministic_match_pipeline(SESSION_ID)
            ]

        events = parse_events(chunks)
        self.assertEqual(events[-1][0], "error")
        self.assertEqual(events[-1][1]["code"], "profile_not_reviewed")
        self.assertFalse(events[-1][1]["retryable"])


if __name__ == "__main__":
    unittest.main()
