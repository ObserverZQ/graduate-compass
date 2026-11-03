"""Profile SQL reads and writes the applicant's extraction and review state.

The profile router uses these functions for upload, extraction, and review;
the matching workflow reads only the reviewed fields from this same boundary.
"""

import json
from uuid import UUID

from sqlalchemy import text

from apps.api.database import SessionLocal
from apps.api.schemas.profile import ApplicantProfile, ExtractedApplicantProfile


class ProfileNotFoundError(LookupError):
    """No applicant row exists for the supplied anonymous session ID."""


class ProfileNotReviewedError(ValueError):
    """The applicant has not saved the reviewed profile and preferences."""


async def save_uploaded_resume(
    session_id: UUID, resume_text: str, file_url: str,
) -> None:
    """Create or update the anonymous row after the PDF is processed."""

    # A replacement PDF invalidates the previous review. Matching must wait
    # until the applicant confirms the new extraction and preferences.
    async with SessionLocal() as session:
        await session.execute(text("""
            INSERT INTO user_profiles (session_id, resume_raw_text, resume_file_url)
            VALUES (:session_id, :resume_raw_text, :resume_file_url)
            ON CONFLICT (session_id) DO UPDATE SET
                resume_raw_text = EXCLUDED.resume_raw_text,
                resume_file_url = EXCLUDED.resume_file_url,
                preferences = NULL,
                updated_at = now()
        """), {
            "session_id": str(session_id),
            "resume_raw_text": resume_text,
            "resume_file_url": file_url,
        })
        await session.commit()


async def load_resume_text(session_id: UUID) -> str:
    """Load the stored PDF text server-side for the extraction request."""

    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT resume_raw_text FROM user_profiles
            WHERE session_id = :session_id LIMIT 1
        """), {"session_id": str(session_id)})
        row = result.mappings().one_or_none()
    if row is None:
        raise ProfileNotFoundError("profile session was not found")
    if not row["resume_raw_text"]:
        raise ValueError("the uploaded PDF contained no readable text")
    return row["resume_raw_text"]


async def save_extracted_profile(
    session_id: UUID, extracted: ExtractedApplicantProfile,
) -> None:
    """Store model-extracted fields before the applicant edits them."""

    # Re-extraction also invalidates an earlier review for this session.
    fields = extracted.model_dump(
        mode="json", exclude={"schema_version", "provenance", "research_interests"},
    )
    async with SessionLocal() as session:
        result = await session.execute(text("""
            UPDATE user_profiles SET
                name = :name, gpa = :gpa, gpa_base = :gpa_base,
                gpa_ranking = :gpa_ranking, toefl_scale_6 = :toefl_scale_6,
                toefl_scale_120 = :toefl_scale_120, ielts = :ielts,
                target_degrees = :target_degrees,
                work_experiences = :work_experiences,
                research_experiences = :research_experiences,
                publications = :publications, preferences = NULL,
                updated_at = now()
            WHERE session_id = :session_id
        """), {
            "session_id": str(session_id),
            "name": fields.get("name"),
            "gpa": fields.get("gpa"),
            "gpa_base": fields.get("gpa_base"),
            "gpa_ranking": fields.get("gpa_ranking"),
            "toefl_scale_6": fields.get("toefl_scale_6"),
            "toefl_scale_120": fields.get("toefl_scale_120"),
            "ielts": fields.get("ielts"),
            "target_degrees": fields.get("target_degrees") or [],
            "work_experiences": json.dumps(fields.get("work_experiences") or []),
            "research_experiences": json.dumps(fields.get("research_experiences") or []),
            "publications": json.dumps(fields.get("publications") or []),
        })
        if result.rowcount == 0:
            raise ProfileNotFoundError("profile session was not found")
        await session.commit()


async def save_reviewed_profile(profile: ApplicantProfile) -> None:
    """Persist the applicant's corrections and preferences as the final source."""

    async with SessionLocal() as session:
        result = await session.execute(text("""
            UPDATE user_profiles SET
                name = :name, gpa = :gpa, gpa_base = :gpa_base,
                gpa_ranking = :gpa_ranking, toefl_scale_6 = :toefl_scale_6,
                toefl_scale_120 = :toefl_scale_120, ielts = :ielts,
                target_degrees = :target_degrees,
                work_experiences = :work_experiences,
                research_experiences = :research_experiences,
                publications = :publications, preferences = :preferences,
                updated_at = now()
            WHERE session_id = :session_id
        """), {
            "session_id": str(profile.session_id),
            "name": profile.name,
            "gpa": profile.gpa,
            "gpa_base": profile.gpa_base,
            "gpa_ranking": profile.gpa_ranking,
            "toefl_scale_6": profile.toefl_scale_6,
            "toefl_scale_120": profile.toefl_scale_120,
            "ielts": profile.ielts,
            "target_degrees": [degree.value for degree in profile.target_degrees],
            "work_experiences": json.dumps([
                work.model_dump(mode="json") for work in profile.work_experiences
            ]),
            "research_experiences": json.dumps([
                research.model_dump(mode="json") for research in profile.research_experiences
            ]),
            "publications": json.dumps([
                publication.model_dump(mode="json") for publication in profile.publications
            ]),
            "preferences": json.dumps(profile.preferences.model_dump(mode="json")),
        })
        if result.rowcount == 0:
            raise ProfileNotFoundError("profile session was not found")
        await session.commit()


async def load_reviewed_profile(session_id: UUID) -> ApplicantProfile:
    """Load only confirmed fields, excluding raw PDF text and file URL."""

    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT session_id, name, target_degrees, gpa, gpa_base, gpa_ranking,
                   toefl_scale_6, toefl_scale_120, ielts, work_experiences,
                   research_experiences, publications, preferences
            FROM user_profiles WHERE session_id = :session_id LIMIT 1
        """), {"session_id": str(session_id)})
        row = result.mappings().one_or_none()
    if row is None:
        raise ProfileNotFoundError("profile session was not found")
    if row["preferences"] is None:
        raise ProfileNotReviewedError("review must be completed before matching")
    return ApplicantProfile.model_validate(dict(row))
