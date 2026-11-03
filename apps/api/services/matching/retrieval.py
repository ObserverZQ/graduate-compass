"""Retrieval applies explicit hard filters and transparent lexical relevance.

get_program_data.py supplies public rows. The matching workflow uses these
results before requirement and preference comparison; embeddings are not used.
"""

import re
from typing import Any

from apps.api.schemas.agent_tools import (
    ProgramSummary, RetrievalEvidence, SearchProgramsInput,
    SearchProgramsOutput,
)
from apps.api.services.matching.get_program_data import load_program_summaries


_TOKENS = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {"and", "for", "from", "program", "the", "with"}
_US_ALIASES = {"america", "united states", "united states of america", "us", "usa"}


async def search_programs(payload: SearchProgramsInput) -> SearchProgramsOutput:
    """Filter definite degree/location mismatches, then order by text overlap."""

    rows = await load_program_summaries()
    candidates: list[ProgramSummary] = []
    excluded = 0
    for row in rows:
        if not _passes_hard_filters(
            row, payload.degree_filters, payload.location_filters
        ):
            excluded += 1
            continue
        score, evidence = _lexical_relevance(payload.query, row)
        candidates.append(ProgramSummary(
            program_id=row["program_id"], name=row["name"],
            university=row["university"], country=row["country"],
            degree_type=row["degree_type"], retrieval_score=score,
            retrieval_evidence=evidence, official_website=row["official_website"],
        ))
    candidates.sort(key=lambda item: (
        -(item.retrieval_score or 0), item.university.casefold(),
        item.name.casefold(), str(item.program_id),
    ))
    return SearchProgramsOutput(
        candidates=candidates[:payload.limit], total_considered=len(rows),
        excluded_by_hard_constraints=excluded,
    )


def _passes_hard_filters(
    row: dict[str, Any], degree_filters: list[str], location_filters: list[str],
) -> bool:
    """Exclude only a definite mismatch against explicitly required fields."""

    if degree_filters:
        degree = _degree_family(row.get("degree_type"))
        accepted = {_degree_family(value) for value in degree_filters}
        accepted.discard(None)
        if degree is not None and degree not in accepted:
            return False
    if location_filters:
        accepted_locations = {_location(value) for value in location_filters}
        if _location(row["country"]) not in accepted_locations:
            return False
    return True


def _lexical_relevance(
    query: str, row: dict[str, Any],
) -> tuple[float, list[RetrievalEvidence]]:
    """Score shared words and keep the public fields that supplied evidence."""

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
        evidence.append(RetrievalEvidence(
            source_field=field, statement=str(statement)[:500],
            relevance_score=min(1.0, len(matches) / len(query_tokens)),
        ))
    return min(1.0, len(all_matches) / len(query_tokens)), evidence[:10]


def _degree_family(value: str | None) -> str | None:
    """Normalize common published degree spellings for hard filtering."""

    if not value:
        return None
    compact = re.sub(r"[^a-z]", "", value.casefold())
    if compact in {
        "ma", "master", "masters", "masterofarts", "masterofengineering",
        "masterofscience", "meng", "ms", "msc",
    }:
        return "masters"
    if compact in {"doctorate", "doctoral", "doctorofphilosophy", "phd"}:
        return "phd"
    return compact or None


def _location(value: str) -> str:
    """Treat common US spellings as the same country during comparison."""

    normalized = " ".join(value.casefold().split())
    return "united states" if normalized in _US_ALIASES else normalized


def _tokens(value: str) -> set[str]:
    """Extract meaningful comparison words from text."""

    return {
        token for token in _TOKENS.findall(value.casefold())
        if len(token) >= 3 and token not in _STOP_WORDS
    }
