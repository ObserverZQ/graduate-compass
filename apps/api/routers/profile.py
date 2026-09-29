from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from apps.api.database import SessionLocal
from apps.api.clients import deepseek, supabase
from apps.api.prompts.resume_extraction import EXTRACTION_PROMPT
from apps.api.schemas.profile import (
    AnalyzeResumeRequest,
    ApplicantProfile,
    ExtractedApplicantProfile,
    ReviewedProfileResponse,
)
import pdfplumber
import asyncio
import io
import json
import time
import uuid
from typing import cast

router = APIRouter()


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
):
    # Step 1: Read all bytes from the multipart upload.
    # UploadFile.read() is awaited because FastAPI streams the request body.
    contents = await file.read()

    # Step 2: Reuse the session ID from a prior upload if the frontend sent one,
    # so re-uploading a resume updates the same user_profiles row instead of
    # creating a new one. Otherwise generate a fresh anonymous identifier.
    if not session_id:
        session_id = str(uuid.uuid4())

    # Step 3: Extract plain text from the PDF and upload the original PDF to
    # the public "resume_test" Storage bucket concurrently — neither depends
    # on the other, and both are blocking calls, so run them in parallel
    # threads to shave time off this request.
    def _extract_text() -> str:
        # pdfplumber preserves column layout better than pypdf, which matters
        # for two-column resume formats. Pages with no extractable text (e.g.
        # scanned images) return None, so we fall back to "" to avoid
        # TypeErrors.
        t0 = time.perf_counter()
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            text_out = "\n".join(page.extract_text() or "" for page in pdf.pages)
        print(f"[upload-resume] _extract_text took {time.perf_counter() - t0:.2f}s")
        return text_out

    def _upload_pdf() -> str:
        # upsert=true allows overwriting the file when re-uploading for the
        # same session_id.
        t0 = time.perf_counter()
        storage_path = f"{session_id}.pdf"
        supabase.storage.from_("resume_test").upload(
            path=storage_path,
            file=contents,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        url = supabase.storage.from_("resume_test").get_public_url(storage_path)
        print(f"[upload-resume] _upload_pdf took {time.perf_counter() - t0:.2f}s")
        return url

    t_gather = time.perf_counter()
    extracted_text, resume_file_url = await asyncio.gather(
        asyncio.to_thread(_extract_text),
        asyncio.to_thread(_upload_pdf),
    )
    print(f"[upload-resume] gather took {time.perf_counter() - t_gather:.2f}s")

    t_db = time.perf_counter()

    # Step 4: Persist the raw text + file URL only. Structured fields are
    # filled in later by /analyze-resume, so this request can return quickly.
    async with SessionLocal() as session:
        await session.execute(text("""
            INSERT INTO user_profiles (session_id, resume_raw_text, resume_file_url)
            VALUES (:session_id, :resume_raw_text, :resume_file_url)
            ON CONFLICT (session_id) DO UPDATE SET
                resume_raw_text = EXCLUDED.resume_raw_text,
                resume_file_url = EXCLUDED.resume_file_url,
                updated_at = now()
        """), {
            "session_id": session_id,
            "resume_raw_text": extracted_text,
            "resume_file_url": resume_file_url,
        })
        await session.commit()
    print(f"[upload-resume] db insert took {time.perf_counter() - t_db:.2f}s")

    return {
        "session_id": session_id,
        "extracted_text": extracted_text,
        "resume_file_url": resume_file_url,
    }


@router.post(
    "/analyze-resume",
    response_model=ExtractedApplicantProfile,
    # Keep the existing frontend wire shape while version/provenance remain
    # internal trust-boundary metadata.
    response_model_exclude={"schema_version", "provenance", "research_interests"},
)
async def analyze_resume(payload: AnalyzeResumeRequest):
    # Ask DeepSeek to extract all structured fields in one LLM call.
    # AsyncOpenAI lets us await the completion natively without blocking a
    # thread-pool worker.
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(resume_text=payload.resume_raw_text),
        }],
        response_format={"type": "json_object"},
    )
    raw_content = response.choices[0].message.content
    if raw_content is None:
        raise RuntimeError("DeepSeek response has no content")
    try:
        extracted = ExtractedApplicantProfile.model_validate_json(raw_content)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Resume extraction returned an invalid profile.",
        ) from exc
    fields = extracted.model_dump(
        mode="json",
        exclude={"schema_version", "provenance", "research_interests"},
    )

    # Fill in the structured fields on the row created by /upload-resume.
    async with SessionLocal() as session:
        result = cast(CursorResult, await session.execute(text("""
            UPDATE user_profiles SET
                name = :name,
                gpa = :gpa,
                gpa_base = :gpa_base,
                gpa_ranking = :gpa_ranking,
                toefl_scale_6 = :toefl_scale_6,
                toefl_scale_120 = :toefl_scale_120,
                ielts = :ielts,
                target_degrees = :target_degrees,
                work_experiences = :work_experiences,
                research_experiences = :research_experiences,
                publications = :publications,
                updated_at = now()
            WHERE session_id = :session_id
        """), {
            "session_id": str(payload.session_id),
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
        }))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="session not found; call /upload-resume first")
        await session.commit()

    return extracted


@router.post("/preferences", response_model=ReviewedProfileResponse)
async def save_preferences(payload: ApplicantProfile):
    # Persist the user's reviewed/edited resume fields plus their preferences.
    async with SessionLocal() as session:
        result = cast(CursorResult, await session.execute(text("""
            UPDATE user_profiles SET
                name = :name,
                gpa = :gpa,
                gpa_base = :gpa_base,
                gpa_ranking = :gpa_ranking,
                toefl_scale_6 = :toefl_scale_6,
                toefl_scale_120 = :toefl_scale_120,
                ielts = :ielts,
                target_degrees = :target_degrees,
                work_experiences = :work_experiences,
                research_experiences = :research_experiences,
                publications = :publications,
                preferences = :preferences,
                updated_at = now()
            WHERE session_id = :session_id
        """), {
            "session_id": str(payload.session_id),
            "name": payload.name,
            "gpa": payload.gpa,
            "gpa_base": payload.gpa_base,
            "gpa_ranking": payload.gpa_ranking,
            "toefl_scale_6": payload.toefl_scale_6,
            "toefl_scale_120": payload.toefl_scale_120,
            "ielts": payload.ielts,
            "target_degrees": [degree.value for degree in payload.target_degrees],
            "work_experiences": json.dumps(
                [work.model_dump(mode="json") for work in payload.work_experiences]
            ),
            "research_experiences": json.dumps(
                [research.model_dump(mode="json") for research in payload.research_experiences]
            ),
            "publications": json.dumps(
                [publication.model_dump(mode="json") for publication in payload.publications]
            ),
            "preferences": json.dumps(payload.preferences.model_dump(mode="json")),
        }))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="session not found; call /upload-resume first")
        await session.commit()

    return {"session_id": payload.session_id, "status": "ok"}
