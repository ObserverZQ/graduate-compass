"""Profile HTTP routes coordinate upload, extraction, and applicant review.

The router validates requests; profile services handle PDF parsing, model calls,
and PostgreSQL. Existing route URLs remain stable for the frontend.
"""

import asyncio
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from apps.api.schemas.profile import (
    AnalyzeResumeRequest, ApplicantProfile, ExtractedApplicantProfile,
    ReviewedProfileResponse, UploadResumeResponse,
)
from apps.api.services.profile.extraction import (
    InvalidExtractionError, extract_profile,
)
from apps.api.services.profile.pdf import extract_pdf_text, upload_pdf
from apps.api.services.profile.profile_save_load import (
    ProfileNotFoundError, load_resume_text, save_extracted_profile,
    save_reviewed_profile, save_uploaded_resume,
)


router = APIRouter()


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: UUID | None = Form(None),
) -> UploadResumeResponse:
    """Store a PDF, extract fields with the LLM, and return them for review."""

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Upload a PDF resume.")
    contents = await file.read()
    profile_session = session_id or uuid4()
    # PDF parsing and Supabase Storage use synchronous libraries, so run both
    # independently without blocking the API event loop.
    extracted_text, file_url = await asyncio.gather(
        asyncio.to_thread(extract_pdf_text, contents),
        asyncio.to_thread(upload_pdf, str(profile_session), contents),
    )
    await save_uploaded_resume(profile_session, extracted_text, file_url)
    if not extracted_text.strip():
        raise HTTPException(status_code=422, detail="The PDF contains no readable text.")
    try:
        extracted = await extract_profile(extracted_text)
    except InvalidExtractionError as exc:
        raise HTTPException(
            status_code=502, detail="Resume extraction returned an invalid profile."
        ) from exc
    await save_extracted_profile(profile_session, extracted)
    return UploadResumeResponse(
        session_id=profile_session, extracted_profile=extracted
    )


@router.post(
    "/analyze-resume",
    response_model=ExtractedApplicantProfile,
    response_model_exclude={"schema_version", "provenance", "research_interests"},
)
async def analyze_resume(payload: AnalyzeResumeRequest) -> ExtractedApplicantProfile:
    """Extract editable fields from text already stored for this session."""

    try:
        resume_text = await load_resume_text(payload.session_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Upload a resume first.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="The PDF contains no readable text.") from exc

    try:
        extracted = await extract_profile(resume_text)
    except InvalidExtractionError as exc:
        raise HTTPException(
            status_code=502, detail="Resume extraction returned an invalid profile."
        ) from exc
    try:
        await save_extracted_profile(payload.session_id, extracted)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc
    return extracted


@router.post("/preferences", response_model=ReviewedProfileResponse)
async def save_preferences(payload: ApplicantProfile) -> ReviewedProfileResponse:
    """Save the applicant's final corrections and matching preferences."""

    try:
        await save_reviewed_profile(payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc
    return ReviewedProfileResponse(session_id=payload.session_id)
