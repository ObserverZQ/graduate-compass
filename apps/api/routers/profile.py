from fastapi import APIRouter, UploadFile, File, Form
from sqlalchemy import text
from apps.api.database import SessionLocal
from openai import OpenAI
from supabase import create_client, Client
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

# Module-level Supabase client for Storage uploads (resume PDFs).
supabase_client: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
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
- toefl_scale_6: number — TOEFL's latest iBT score (range 0-6); null if not found
- toefl_scale_120: integer — TOEFL (range 0-120); null if not found
- ielts: number — IELTS band score (range 0-9); null if not found
- target_degrees: array of strings — degrees the applicant mentions targeting, e.g. ["MS", "PhD"]
- work_experiences: array of objects with keys: company, title, start_date, end_date, description
- research_experiences: array of objects with keys: institution, title, start_date, end_date, description
- publications: array of objects with keys: title, venue, year, authors

Resume:
{resume_text}
"""


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
):
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

    # Step 3: Reuse the session ID from a prior upload if the frontend sent one,
    # so re-uploading a resume updates the same user_profiles row instead of
    # creating a new one. Otherwise generate a fresh anonymous identifier.
    if not session_id:
        session_id = str(uuid.uuid4())

    # Step 3b: Upload the original PDF to the public "resume_test" Storage bucket
    # and record its public URL so the frontend can render it directly.
    # upsert=true allows overwriting the file when re-uploading for the same
    # session_id.
    storage_path = f"{session_id}.pdf"
    supabase_client.storage.from_("resume_test").upload(
        path=storage_path,
        file=contents,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    resume_file_url = supabase_client.storage.from_("resume_test").get_public_url(storage_path)

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
        raw_content = response.choices[0].message.content
        if raw_content is None:
          raise RuntimeError("DeepSeek response has no content")

        return json.loads(raw_content)

    loop = asyncio.get_event_loop()
    fields = await loop.run_in_executor(None, _extract_fields)

    # Step 5: Persist the full profile row.
    # JSONB columns (work/research/publications) are passed as JSON strings;
    # asyncpg handles the cast. The text[] column (target_degrees) accepts a
    # Python list directly. ON CONFLICT (session_id) lets a re-upload from the
    # same session overwrite the existing row instead of creating a new one.
    async with SessionLocal() as session:
        await session.execute(text("""
            INSERT INTO user_profiles (
                session_id,
                name,
                resume_raw_text,
                resume_file_url,
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
                :resume_file_url,
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
            ON CONFLICT (session_id) DO UPDATE SET
                name = EXCLUDED.name,
                resume_raw_text = EXCLUDED.resume_raw_text,
                resume_file_url = EXCLUDED.resume_file_url,
                gpa = EXCLUDED.gpa,
                gpa_base = EXCLUDED.gpa_base,
                gpa_ranking = EXCLUDED.gpa_ranking,
                toefl_scale_6 = EXCLUDED.toefl_scale_6,
                toefl_scale_120 = EXCLUDED.toefl_scale_120,
                ielts = EXCLUDED.ielts,
                target_degrees = EXCLUDED.target_degrees,
                work_experiences = EXCLUDED.work_experiences,
                research_experiences = EXCLUDED.research_experiences,
                publications = EXCLUDED.publications,
                updated_at = now()
        """), {
            "session_id": session_id,
            "name": fields.get("name"),
            "resume_raw_text": extracted_text,
            "resume_file_url": resume_file_url,
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
        "resume_file_url": resume_file_url,
        **fields,
    }
