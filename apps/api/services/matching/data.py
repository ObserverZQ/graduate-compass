"""Supabase-backed profile and program access for matching tools."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text

from apps.api.database import SessionLocal
from apps.api.schemas.agent_tools import (
    MAX_CANDIDATES,
    GetProgramDetailsInput,
    GetProgramDetailsOutput,
    ProgramDetails,
    ProgramSummary,
    RetrievalEvidence,
    SearchProgramsInput,
    SearchProgramsOutput,
)
from apps.api.schemas.profile import ApplicantProfile


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_QUERY_STOP_WORDS = {"and", "for", "from", "program", "the", "with"}
_US_ALIASES = {"america", "united states", "united states of america", "us", "usa"}


class ProfileNotFoundError(LookupError):
    """The requested anonymous applicant session does not exist."""


class ProfileNotReviewedError(ValueError):
    """The profile exists, but the applicant has not submitted its review."""


async def load_reviewed_profile(session_id: UUID) -> ApplicantProfile:
    """Load only reviewed profile fields and validate the matching boundary.

    Raw résumé text and the uploaded file URL are deliberately excluded from
    the query so they cannot accidentally enter tool inputs, model context, or
    logs. A NULL preferences value means the review endpoint never completed;
    an empty JSON object is valid because all preferences may be skipped.
    """

    async with SessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    session_id,
                    name,
                    target_degrees,
                    gpa,
                    gpa_base,
                    gpa_ranking,
                    toefl_scale_6,
                    toefl_scale_120,
                    ielts,
                    work_experiences,
                    research_experiences,
                    publications,
                    preferences
                FROM user_profiles
                WHERE session_id = :session_id
                LIMIT 1
                """
            ),
            {"session_id": str(session_id)},
        )
        row = result.mappings().one_or_none()

    if row is None:
        raise ProfileNotFoundError(f"profile session {session_id} was not found")
    if row["preferences"] is None:
        raise ProfileNotReviewedError("profile review must be completed before matching")
    return ApplicantProfile.model_validate(dict(row))


async def search_programs(payload: SearchProgramsInput) -> SearchProgramsOutput:
    """Apply explicit hard filters and rank the bounded catalogue by relevance.

    The current 24-record catalogue is small enough to load once. Relevance is
    a transparent lexical fallback over public fields; replacing this helper
    with pgvector retrieval later will not change the agent-facing contract.
    Soft applicant preferences must never be passed as these hard filters.
    """

    async with SessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    id AS program_id,
                    name,
                    university,
                    country,
                    degree_type,
                    department,
                    description,
                    research_areas,
                    official_website
                FROM programs
                ORDER BY university ASC, name ASC, id ASC
                LIMIT :catalogue_limit
                """
            ),
            {"catalogue_limit": MAX_CANDIDATES},
        )
        rows = [dict(row) for row in result.mappings().all()]

    candidates: list[ProgramSummary] = []
    excluded = 0
    for row in rows:
        if not _passes_hard_filters(
            row,
            degree_filters=payload.degree_filters,
            location_filters=payload.location_filters,
        ):
            excluded += 1
            continue

        relevance_score, evidence = _lexical_relevance(payload.query, row)
        candidates.append(
            ProgramSummary(
                program_id=row["program_id"],
                name=row["name"],
                university=row["university"],
                country=row["country"],
                degree_type=row["degree_type"],
                retrieval_score=relevance_score,
                retrieval_evidence=evidence,
                official_website=row["official_website"],
            )
        )

    # Public fields provide deterministic tie-breakers when relevance scores
    # are equal, avoiding database-order changes between otherwise identical runs.
    candidates.sort(
        key=lambda candidate: (
            -(candidate.retrieval_score or 0),
            candidate.university.casefold(),
            candidate.name.casefold(),
            str(candidate.program_id),
        )
    )
    return SearchProgramsOutput(
        candidates=candidates[: payload.limit],
        total_considered=len(rows),
        excluded_by_hard_constraints=excluded,
    )


async def get_program_details(
    payload: GetProgramDetailsInput,
) -> GetProgramDetailsOutput:
    """Load evidence-bearing fields for a bounded set of candidate IDs."""

    # Expanding parameters create one safely-bound placeholder per UUID. This
    # avoids constructing SQL from IDs while keeping the query bounded to the
    # candidates selected by search_programs.
    statement = text(
        """
        SELECT
            id AS program_id,
            name,
            university,
            country,
            degree_type,
            department,
            description,
            research_areas,
            duration_months,
            annual_tuition_and_fees,
            annual_living_expenses,
            min_gpa,
            min_toefl,
            min_ielts,
            gre_required,
            climate,
            living_experience,
            job_placement_score,
            phd_pathway_detail,
            official_website
        FROM programs
        WHERE id IN :program_ids
        """
    ).bindparams(bindparam("program_ids", expanding=True))

    async with SessionLocal() as session:
        result = await session.execute(
            statement,
            {"program_ids": payload.program_ids},
        )
        rows = result.mappings().all()

    by_id = {
        row["program_id"]: ProgramDetails.model_validate(dict(row)) for row in rows
    }
    # Preserve the search result order rather than relying on an unspecified IN
    # query order; the same order then flows through assessment and ranking.
    programs = [by_id[program_id] for program_id in payload.program_ids if program_id in by_id]
    missing = [program_id for program_id in payload.program_ids if program_id not in by_id]
    return GetProgramDetailsOutput(
        programs=programs,
        missing_program_ids=missing,
    )


def _passes_hard_filters(
    row: dict[str, Any],
    *,
    degree_filters: list[str],
    location_filters: list[str],
) -> bool:
    if degree_filters:
        program_degree = _degree_family(row.get("degree_type"))
        accepted_degrees = {_degree_family(value) for value in degree_filters}
        accepted_degrees.discard(None)
        # Exclude only a definite mismatch. Unknown published degree data stays
        # eligible and should later appear as an uncertainty.
        if program_degree is not None and program_degree not in accepted_degrees:
            return False

    if location_filters:
        country = _canonical_location(row["country"])
        accepted_locations = {
            _canonical_location(location) for location in location_filters
        }
        if country not in accepted_locations:
            return False
    return True


def _lexical_relevance(
    query: str,
    row: dict[str, Any],
) -> tuple[float, list[RetrievalEvidence]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0, []

    evidence: list[RetrievalEvidence] = []
    all_matches: set[str] = set()
    for field in ("name", "department", "description", "research_areas"):
        statement = row.get(field)
        if not statement:
            continue
        matches = query_tokens & _tokens(str(statement))
        if not matches:
            continue
        all_matches.update(matches)
        field_score = len(matches) / len(query_tokens)
        evidence.append(
            RetrievalEvidence(
                source_field=field,
                statement=str(statement)[:500],
                relevance_score=min(1.0, field_score),
            )
        )

    relevance_score = len(all_matches) / len(query_tokens)
    return min(1.0, relevance_score), evidence[:10]


def _degree_family(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^a-z]", "", value.casefold())
    if compact in {
        "ma",
        "master",
        "masters",
        "masterofarts",
        "masterofengineering",
        "masterofscience",
        "meng",
        "ms",
        "msc",
    }:
        return "masters"
    if compact in {"doctorate", "doctoral", "doctorofphilosophy", "phd"}:
        return "phd"
    return compact or None


def _canonical_location(value: str) -> str:
    normalized = " ".join(value.casefold().split())
    return "united states" if normalized in _US_ALIASES else normalized


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(value.casefold())
        if len(token) >= 3 and token not in _QUERY_STOP_WORDS
    }
