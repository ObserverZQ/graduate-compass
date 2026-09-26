"""Contract tests for deterministic matching and its bounded tools."""

import unittest
from uuid import UUID

from pydantic import ValidationError

from apps.api.schemas.agent_tools import (
    MAX_CANDIDATES,
    MAX_RESULTS,
    CalculatePreferenceFitOutput,
    CandidateForRanking,
    EvidenceConfidence,
    PreferenceFit,
    RankProgramsInput,
    RankProgramsOutput,
    RequirementAssessment,
    SearchProgramsInput,
    ProgramSummary,
)
from apps.api.schemas.match import ProgramMatchResult


PROGRAM_ID = UUID("00000000-0000-0000-0000-000000000001")


def valid_match_result(**overrides: object) -> dict[str, object]:
    """Return the smallest valid public result, with optional test overrides."""

    result: dict[str, object] = {
        "rank": 1,
        "program_id": PROGRAM_ID,
        "name": "MS in Synthetic Systems",
        "university": "Synthetic University",
        "country": "Exampleland",
        "degree_type": "MS",
        "fit_score": 80,
        "score_version": "deterministic-v1",
        "why_match": "The program aligns with the supplied profile evidence.",
        "supporting_evidence": [],
        "factors": [],
        "strengths": [],
        "gaps": [],
        "uncertainties": [],
        "next_action": "Review the official program requirements.",
        "official_website": "https://example.edu/program",
    }
    result.update(overrides)
    return result


class MatchingContractTests(unittest.TestCase):
    def test_invalid_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SearchProgramsInput(
                query="distributed systems",
                unexpected_filter="should fail",  # type: ignore[call-arg]
            )

    def test_candidate_and_result_limits_are_enforced(self) -> None:
        with self.assertRaises(ValidationError):
            SearchProgramsInput(
                query="distributed systems",
                limit=MAX_CANDIDATES + 1,
            )

        requirement = RequirementAssessment(
            program_id=PROGRAM_ID,
            evidence_confidence=EvidenceConfidence.HIGH,
        )
        preference = PreferenceFit(
            program_id=PROGRAM_ID,
            score=None,
            evidence_coverage=0,
        )
        candidate = CandidateForRanking(
            program=ProgramSummary(
                program_id=PROGRAM_ID,
                name="MS in Synthetic Systems",
                university="Synthetic University",
                country="Exampleland",
            ),
            requirements=requirement,
            preference_fit=preference,
            relevance_score=80,
        )
        with self.assertRaises(ValidationError):
            RankProgramsInput(
                candidates=[candidate],
                result_limit=MAX_RESULTS + 1,
        )

        with self.assertRaises(ValidationError):
            ProgramMatchResult.model_validate(
                valid_match_result(rank=MAX_RESULTS + 1)
            )

        valid_results = [
            ProgramMatchResult.model_validate(
                valid_match_result(rank=min(index + 1, MAX_RESULTS))
            )
            for index in range(MAX_RESULTS + 1)
        ]
        with self.assertRaises(ValidationError):
            RankProgramsOutput(results=valid_results)

    def test_fit_score_must_stay_between_zero_and_one_hundred(self) -> None:
        for invalid_score in (-1, 101):
            with self.subTest(fit_score=invalid_score):
                with self.assertRaises(ValidationError):
                    ProgramMatchResult.model_validate(
                        valid_match_result(fit_score=invalid_score)
                    )

    def test_missing_evidence_can_be_represented_as_uncertainty(self) -> None:
        requirement = RequirementAssessment(
            program_id=PROGRAM_ID,
            uncertainties=["The program does not publish a minimum GPA."],
            evidence_confidence=EvidenceConfidence.LOW,
        )
        preference = PreferenceFit(
            program_id=PROGRAM_ID,
            score=None,
            evidence_coverage=0,
            uncertainties=["The program does not publish climate information."],
        )
        output = CalculatePreferenceFitOutput(fits=[preference])

        self.assertEqual(requirement.strengths, [])
        self.assertEqual(requirement.gaps, [])
        self.assertEqual(len(requirement.uncertainties), 1)
        self.assertIsNone(output.fits[0].score)
        self.assertEqual(output.fits[0].evidence_coverage, 0)

    def test_output_contract_rejects_admission_probability(self) -> None:
        with self.assertRaises(ValidationError):
            ProgramMatchResult.model_validate(
                valid_match_result(admission_probability=0.8)
            )


if __name__ == "__main__":
    unittest.main()
