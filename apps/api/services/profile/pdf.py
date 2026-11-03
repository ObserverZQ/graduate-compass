"""PDF helpers prepare uploaded résumé content for profile extraction.

The profile router calls these helpers; storage and SQL remain in other files.
"""

import io

import pdfplumber

from apps.api.clients import supabase


def extract_pdf_text(contents: bytes) -> str:
    """Read text from all pages, treating image-only pages as empty text."""

    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def upload_pdf(session_id: str, contents: bytes) -> str:
    """Save the original PDF and return the existing public storage URL."""

    storage_path = f"{session_id}.pdf"
    bucket = supabase.storage.from_("resume_test")
    bucket.upload(
        path=storage_path,
        file=contents,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    return bucket.get_public_url(storage_path)
