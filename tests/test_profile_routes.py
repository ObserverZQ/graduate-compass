"""Route tests check the profile services are called in the intended order.

All PDF, model, and database boundaries are mocked; no personal résumé is used.
"""

import io
import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/graduate_compass_test",
)

from fastapi import UploadFile

from apps.api.routers import profile as profile_router
from apps.api.schemas.profile import AnalyzeResumeRequest, ExtractedApplicantProfile


SESSION_ID = UUID("00000000-0000-0000-0000-000000000100")


class ProfileRouteTests(unittest.IsolatedAsyncioTestCase):
    """Verify upload and extraction use server-side profile storage."""

    async def test_upload_returns_extracted_fields_for_review(self) -> None:
        """One upload stores the PDF, extracts fields, and returns only review data."""

        file = UploadFile(file=io.BytesIO(b"%PDF-synthetic"), filename="resume.pdf")
        file.headers = {"content-type": "application/pdf"}
        save = AsyncMock()
        extracted = ExtractedApplicantProfile(name="Synthetic Applicant")
        extract = AsyncMock(return_value=extracted)
        save_extracted = AsyncMock()
        with (
            patch.object(profile_router, "extract_pdf_text", return_value="Synthetic text"),
            patch.object(profile_router, "upload_pdf", return_value="https://example.test/resume.pdf"),
            patch.object(profile_router, "save_uploaded_resume", save),
            patch.object(profile_router, "extract_profile", extract),
            patch.object(profile_router, "save_extracted_profile", save_extracted),
        ):
            result = await profile_router.upload_resume(file, SESSION_ID)

        self.assertEqual(result.session_id, SESSION_ID)
        self.assertEqual(result.extracted_profile.name, "Synthetic Applicant")
        self.assertNotIn("extracted_text", result.model_dump())
        self.assertNotIn("provenance", result.model_dump()["extracted_profile"])
        save.assert_awaited_once_with(
            SESSION_ID, "Synthetic text", "https://example.test/resume.pdf"
        )
        extract.assert_awaited_once_with("Synthetic text")
        save_extracted.assert_awaited_once_with(SESSION_ID, extracted)

    async def test_analysis_loads_text_by_session_id(self) -> None:
        """Extraction reads stored text instead of accepting text from browser."""

        extracted = ExtractedApplicantProfile(name="Synthetic Applicant")
        load = AsyncMock(return_value="Synthetic resume text")
        extract = AsyncMock(return_value=extracted)
        save = AsyncMock()
        with (
            patch.object(profile_router, "load_resume_text", load),
            patch.object(profile_router, "extract_profile", extract),
            patch.object(profile_router, "save_extracted_profile", save),
        ):
            result = await profile_router.analyze_resume(
                AnalyzeResumeRequest(session_id=SESSION_ID)
            )

        self.assertEqual(result.name, "Synthetic Applicant")
        load.assert_awaited_once_with(SESSION_ID)
        extract.assert_awaited_once_with("Synthetic resume text")
        save.assert_awaited_once_with(SESSION_ID, extracted)


if __name__ == "__main__":
    unittest.main()
