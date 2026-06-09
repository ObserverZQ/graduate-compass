from fastapi import APIRouter, UploadFile, File
from sqlalchemy import text
from apps.api.database import SessionLocal
from openai import OpenAI
import pdfplumber
import asyncio
import io
import json
import os
import uuid

router = APIRouter()

# Reuse the same DeepSeek client pattern from health.py.
# Module-level init so the client is created once on startup, not per request.
deepseek = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# Prompt asking DeepSeek to return a single JSON object with all resume fields.
# null is used for any field not found, so missing data never causes a KeyError.
_EXTRACTION_PROMPT = """\
Parse the resume text below and return a single JSON object with these exact keys.
Use null for any field not present in the resume.

Keys:
- name: string — applicant's full name
- gpa: number — GPA value (e.g. 3.8)
- gpa_base: number — GPA scale (4.0, 5.0, or 100.0); infer from context if not stated
- gpa_ranking: string — undergraduate school name or ranking text (e.g. "MIT", "Top 50 US university")
- toefl_scale_6: number — TOEFL iBT score (range 0-120); null if not found
- toefl_scale_120: integer — TOEFL PBT/legacy score (range 200-677); null if not found
- ielts: number — IELTS band score (range 0-9); null if not found
- target_degrees: array of strings — degrees the applicant mentions targeting, e.g. ["MS", "PhD"]
- work_experiences: array of objects with keys: company, title, start_date, end_date, description
- research_experiences: array of objects with keys: institution, title, start_date, end_date, description
- publications: array of objects with keys: title, venue, year, authors

Resume:
{resume_text}
"""


@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    # Step 1: Read all bytes from the multipart upload.
    # UploadFile.read() is awaited because FastAPI streams the request body.
    contents = await file.read()

    # Step 2: Extract plain text from the PDF.
    # pdfplumber preserves column layout better than pypdf, which matters for
    # two-column resume formats. Pages with no extractable text (e.g. scanned
    # images) return None, so we fall back to "" to avoid TypeErrors.
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        extracted_text = "\n".join(
            page.extract_text() or ""
            for page in pdf.pages
        )

    # Step 3: Generate a session ID.
    # This UUID is the anonymous identifier returned to the frontend and stored
    # in localStorage so subsequent API calls can look up this profile row.
    session_id = str(uuid.uuid4())

    # Step 4: Ask DeepSeek to extract all structured fields in one LLM call.
    # The DeepSeek client is synchronous (blocking HTTP), so we offload it to
    # a thread pool via run_in_executor to avoid stalling the async event loop.
    def _extract_fields() -> dict:
        response = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": _EXTRACTION_PROMPT.format(resume_text=extracted_text),
            }],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    loop = asyncio.get_event_loop()
    fields = await loop.run_in_executor(None, _extract_fields)

    # Step 5: Persist the full profile row.
    # JSONB columns (work/research/publications) are passed as JSON strings;
    # asyncpg handles the cast. The text[] column (target_degrees) accepts a
    # Python list directly. resume_file_url is intentionally omitted — it needs
    # a private Supabase Storage bucket with signed URLs (requires auth first).
    async with SessionLocal() as session:
        await session.execute(text("""
            INSERT INTO user_profiles (
                session_id,
                name,
                resume_raw_text,
                gpa,
                gpa_base,
                gpa_ranking,
                toefl_scale_6,
                toefl_scale_120,
                ielts,
                target_degrees,
                work_experiences,
                research_experiences,
                publications
            ) VALUES (
                :session_id,
                :name,
                :resume_raw_text,
                :gpa,
                :gpa_base,
                :gpa_ranking,
                :toefl_scale_6,
                :toefl_scale_120,
                :ielts,
                :target_degrees,
                :work_experiences,
                :research_experiences,
                :publications
            )
        """), {
            "session_id": session_id,
            "name": fields.get("name"),
            "resume_raw_text": extracted_text,
            "gpa": fields.get("gpa"),
            "gpa_base": fields.get("gpa_base"),
            "gpa_ranking": fields.get("gpa_ranking"),
            "toefl_scale_6": fields.get("toefl_scale_6"),
            "toefl_scale_120": fields.get("toefl_scale_120"),
            "ielts": fields.get("ielts"),
            "target_degrees": fields.get("target_degrees") or [],
            "work_experiences": json.dumps(
                fields.get("work_experiences") or []
            ),
            "research_experiences": json.dumps(
                fields.get("research_experiences") or []
            ),
            "publications": json.dumps(
                fields.get("publications") or []
            ),
        })
        await session.commit()

    return {
        "session_id": session_id,
        "extracted_text": extracted_text,
        **fields,
    }
