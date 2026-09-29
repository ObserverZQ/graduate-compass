"""Contract tests for extracted and user-reviewed applicant profiles."""

import unittest
from uuid import UUID

from pydantic import ValidationError

from apps.api.schemas.profile import (
    AnalyzeResumeRequest,
    ApplicantProfile,
    BudgetPreference,
    CareerGoal,
    ClimatePreference,
    DegreeType,
    ExtractedApplicantProfile,
    ReviewStatus,
)


SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")


class ApplicantProfileContractTests(unittest.TestCase):
    def test_reviewed_profile_normalizes_existing_frontend_values(self) -> None:
        profile = ApplicantProfile.model_validate(
            {
                "session_id": str(SESSION_ID),
                "name": "  Synthetic Applicant  ",
                "gpa": 3.8,
                "gpa_base": 4,
                "target_degrees": ["MSc", "Ph.D."],
                "work_experiences": [],
                "research_experiences": [],
                "publications": [],
                "preferences": {
                    "locations": ["USA", "USA", "Canada"],
                    "climate": "Warm",
                    "budget": "$20–40k / yr",
                    "careerGoal": "Industry job",
                },
            }
        )

        self.assertEqual(profile.name, "Synthetic Applicant")
        self.assertEqual(
            profile.target_degrees,
            [DegreeType.MASTERS, DegreeType.PHD],
        )
        self.assertEqual(profile.preferences.locations, ["USA", "Canada"])
        self.assertEqual(profile.preferences.climate, ClimatePreference.WARM)
        self.assertEqual(
            profile.preferences.budget,
            BudgetPreference.FROM_20K_TO_40K,
        )
        self.assertEqual(profile.preferences.career_goal, CareerGoal.INDUSTRY)
        self.assertEqual(
            profile.provenance.review_status,
            ReviewStatus.REVIEWED,
        )

    def test_partial_extraction_normalizes_missing_collections_and_blanks(self) -> None:
        profile = ExtractedApplicantProfile.model_validate(
            {
                "name": "  ",
                "target_degrees": None,
                "work_experiences": None,
                "research_experiences": None,
                "publications": None,
            }
        )

        self.assertIsNone(profile.name)
        self.assertEqual(profile.target_degrees, [])
        self.assertEqual(profile.work_experiences, [])
        self.assertEqual(profile.research_experiences, [])
        self.assertEqual(profile.publications, [])
        self.assertEqual(
            profile.provenance.review_status,
            ReviewStatus.EXTRACTED,
        )

    def test_extracted_and_reviewed_provenance_cannot_cross_boundaries(self) -> None:
        extracted = ExtractedApplicantProfile()

        with self.assertRaises(ValidationError):
            ApplicantProfile.model_validate(
                {
                    **extracted.model_dump(mode="json"),
                    "session_id": str(SESSION_ID),
                }
            )

        with self.assertRaises(ValidationError):
            ExtractedApplicantProfile.model_validate(
                {
                    "provenance": {
                        "source": "user_review",
                        "review_status": "reviewed",
                    }
                }
            )

    def test_invalid_academic_score_ranges_are_rejected(self) -> None:
        invalid_profiles = (
            {"gpa": 4.5, "gpa_base": 4},
            {"toefl_scale_6": 6.1},
            {"toefl_scale_120": 121},
            {"ielts": 9.1},
        )

        for payload in invalid_profiles:
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    ExtractedApplicantProfile.model_validate(payload)

    def test_unknown_profile_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ExtractedApplicantProfile.model_validate(
                {
                    "name": "Synthetic Applicant",
                    "admission_probability": 0.9,
                }
            )

    def test_no_preference_values_are_canonicalized(self) -> None:
        profile = ApplicantProfile.model_validate(
            {
                "session_id": str(SESSION_ID),
                "preferences": {
                    "locations": ["No preference"],
                    "climate": "No preference",
                    "budget": "No limit",
                    "careerGoal": "Not sure yet",
                },
            }
        )

        self.assertEqual(profile.preferences.locations, [])
        self.assertIsNone(profile.preferences.climate)
        self.assertIsNone(profile.preferences.budget)
        self.assertEqual(profile.preferences.career_goal, CareerGoal.UNDECIDED)

    def test_analyze_request_validates_session_and_resume_text(self) -> None:
        request = AnalyzeResumeRequest(
            session_id=SESSION_ID,
            resume_raw_text="Synthetic resume text",
        )

        self.assertEqual(request.session_id, SESSION_ID)

        with self.assertRaises(ValidationError):
            AnalyzeResumeRequest.model_validate(
                {
                    "session_id": "not-a-uuid",
                    "resume_raw_text": "",
                }
            )


if __name__ == "__main__":
    unittest.main()
