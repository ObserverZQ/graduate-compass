"""Program SQL loads the public catalogue used by matching tools.

retrieval.py asks for brief program rows; the workflow asks for full details
after filtering. This file owns database access, not scoring decisions.
"""

from uuid import UUID
from typing import Any

from sqlalchemy import bindparam, text

from apps.api.database import SessionLocal
from apps.api.schemas.agent_tools import (
    MAX_CANDIDATES, GetProgramDetailsInput, GetProgramDetailsOutput,
    ProgramDetails,
)


async def load_program_summaries() -> list[dict[str, Any]]:
    """Read a bounded, stable snapshot of public program search fields."""

    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT id AS program_id, name, university, country, degree_type,
                   department, description, research_areas, official_website
            FROM programs ORDER BY university ASC, name ASC, id ASC
            LIMIT :catalogue_limit
        """), {"catalogue_limit": MAX_CANDIDATES})
        return [dict(row) for row in result.mappings().all()]


async def get_program_details(
    payload: GetProgramDetailsInput,
) -> GetProgramDetailsOutput:
    """Load detailed evidence for candidate IDs and preserve requested order."""

    # Expanding bound parameters safely create one placeholder per UUID.
    statement = text("""
        SELECT id AS program_id, name, university, country, degree_type,
               department, description, research_areas, duration_months,
               annual_tuition_and_fees, annual_living_expenses, min_gpa,
               min_toefl, min_ielts, gre_required, climate, living_experience,
               job_placement_score, phd_pathway_detail, official_website
        FROM programs WHERE id IN :program_ids
    """).bindparams(bindparam("program_ids", expanding=True))
    async with SessionLocal() as session:
        result = await session.execute(
            statement, {"program_ids": payload.program_ids}
        )
        rows = result.mappings().all()

    by_id: dict[UUID, ProgramDetails] = {
        row["program_id"]: ProgramDetails.model_validate(dict(row)) for row in rows
    }
    return GetProgramDetailsOutput(
        programs=[by_id[key] for key in payload.program_ids if key in by_id],
        missing_program_ids=[key for key in payload.program_ids if key not in by_id],
    )
