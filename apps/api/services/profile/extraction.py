"""Extraction turns stored résumé text into fields for applicant review.

The profile router supplies text loaded by profile_save_load.py; this service
calls DeepSeek once and validates the returned fields before they are saved.
"""

from pydantic import ValidationError

from apps.api.clients import deepseek
from apps.api.prompts.resume_extraction import EXTRACTION_PROMPT
from apps.api.schemas.profile import ExtractedApplicantProfile


class InvalidExtractionError(ValueError):
    """The model returned fields that do not match the profile contract."""


async def extract_profile(resume_text: str) -> ExtractedApplicantProfile:
    """Ask the model for structured fields and reject malformed responses."""

    response = await deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(resume_text=resume_text),
        }],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if content is None:
        raise InvalidExtractionError("extraction returned no content")
    try:
        return ExtractedApplicantProfile.model_validate_json(content)
    except ValidationError as exc:
        raise InvalidExtractionError("extraction returned invalid fields") from exc
