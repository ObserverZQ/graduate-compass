from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from apps.api.database import SessionLocal
from openai import AsyncOpenAI
from supabase import create_client, Client
import pdfplumber
import asyncio
import io
import json
import os
import time
import uuid
from typing import cast

router = APIRouter()

# Reuse the same DeepSeek client pattern from health.py.
# Module-level init so the client is created once on startup, not per request.
# AsyncOpenAI lets the analyze-resume endpoint await the completion natively
# instead of blocking a thread-pool worker for the ~10s call.
deepseek = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# Module-level Supabase client for Storage uploads (resume PDFs).
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if SUPABASE_URL is None:
    raise RuntimeError("SUPABASE_URL environment variable is not set")
if SUPABASE_SERVICE_ROLE_KEY is None:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Prompt asking DeepSeek to return a single JSON object with all resume fields.
# null is used for any field not found, so missing data never causes a KeyError.
_EXTRACTION_PROMPT = """\
Parse the resume text below and return a single JSON object with these exact keys.
Use null for any field not present in the resume.
Keep all free-text descriptions concise (1-2 sentences). Do not copy full
bullet-point lists from the resume verbatim.

Keys:
- name: string — applicant's full name
- gpa: number — GPA value (e.g. 3.8)
- gpa_base: number — GPA scale (4.0, 5.0, or 100.0); infer from context if not stated
- gpa_ranking: string — undergraduate school name or ranking text (e.g. "MIT", "Top 50 US university")
- toefl_scale_6: number — TOEFL's latest iBT score (range 0-6); null if not found
- toefl_scale_120: integer — TOEFL (range 0-120); null if not found
- ielts: number — IELTS band score (range 0-9); null if not found
- target_degrees: array of strings — degrees the applicant mentions targeting, e.g. ["MS", "PhD"]
- work_experiences: array of objects with keys: company, title, start_date, end_date, description
  - description: a brief 1-2 sentence summary of the role's key responsibility/impact
- research_experiences: array of objects with keys: institution, title, start_date, end_date, description
  - description: a brief 1-2 sentence summary of the research focus/contribution
- publications: array of objects with keys: title, venue, year, authors

Resume:
{resume_text}
"""


class WorkExperience(BaseModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class ResearchExperience(BaseModel):
    institution: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class Publication(BaseModel):
    title: str | None = None
    venue: str | None = None
    year: str | int | None = None
    authors: str | None = None


class AnalyzeResumeRequest(BaseModel):
    session_id: str
    resume_raw_text: str


class SubmitProfileRequest(BaseModel):
    session_id: str
    name: str | None = None
    gpa: float | None = None
    gpa_base: float | None = None
    gpa_ranking: str | None = None
    toefl_scale_6: float | None = None
    toefl_scale_120: int | None = None
    ielts: float | None = None
    target_degrees: list[str] = []
    work_experiences: list[WorkExperience] = []
    research_experiences: list[ResearchExperience] = []
    publications: list[Publication] = []
    preferences: dict[str, str | list[str]] = {}


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
        supabase_client.storage.from_("resume_test").upload(
            path=storage_path,
            file=contents,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        url = supabase_client.storage.from_("resume_test").get_public_url(storage_path)
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


@router.post("/analyze-resume")
async def analyze_resume(payload: AnalyzeResumeRequest):
    # Ask DeepSeek to extract all structured fields in one LLM call.
    # AsyncOpenAI lets us await the completion natively without blocking a
    # thread-pool worker.
    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{
            "role": "user",
            "content": _EXTRACTION_PROMPT.format(resume_text=payload.resume_raw_text),
        }],
        response_format={"type": "json_object"},
    )
    raw_content = response.choices[0].message.content
    if raw_content is None:
        raise RuntimeError("DeepSeek response has no content")
    fields = json.loads(raw_content)

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
            "session_id": payload.session_id,
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

    return {
        "name": fields.get("name"),
        "gpa": fields.get("gpa"),
        "gpa_base": fields.get("gpa_base"),
        "gpa_ranking": fields.get("gpa_ranking"),
        "toefl_scale_6": fields.get("toefl_scale_6"),
        "toefl_scale_120": fields.get("toefl_scale_120"),
        "ielts": fields.get("ielts"),
        "target_degrees": fields.get("target_degrees") or [],
        "work_experiences": fields.get("work_experiences") or [],
        "research_experiences": fields.get("research_experiences") or [],
        "publications": fields.get("publications") or [],
    }


@router.post("/preferences")
async def save_preferences(payload: SubmitProfileRequest):
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
            "session_id": payload.session_id,
            "name": payload.name,
            "gpa": payload.gpa,
            "gpa_base": payload.gpa_base,
            "gpa_ranking": payload.gpa_ranking,
            "toefl_scale_6": payload.toefl_scale_6,
            "toefl_scale_120": payload.toefl_scale_120,
            "ielts": payload.ielts,
            "target_degrees": payload.target_degrees,
            "work_experiences": json.dumps([w.model_dump() for w in payload.work_experiences]),
            "research_experiences": json.dumps([r.model_dump() for r in payload.research_experiences]),
            "publications": json.dumps([p.model_dump() for p in payload.publications]),
            "preferences": json.dumps(payload.preferences),
        }))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="session not found; call /upload-resume first")
        await session.commit()

    return {"session_id": payload.session_id, "status": "ok"}
