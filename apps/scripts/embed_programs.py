"""
One-shot script: backfill embeddings for all programs where embedding IS NULL.
Uses Aliyun DashScope text-embedding-v4 (1536 dims).

Usage:
    python -m apps.scripts.embed_programs
"""

import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())  # must run before apps.api.clients import

from openai import OpenAI  # DashScope is OpenAI-compatible
from apps.api.clients import supabase

EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIMS = 1536
BATCH_SIZE = 10  # DashScope text-embedding-v4 caps at 10 inputs per request

dashscope = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def build_embedding_input(program: dict) -> str:
    """Compose the text that defines a program's semantic identity.

    Includes only fields describing what the program IS — intellectual
    content, structure, target audience. Filters, subjective scores, and
    lifestyle fields are excluded; those belong in other pipeline stages.
    """
    # Program name with abbreviation in parens, so retrieval matches both
    # full names ("MS in Computer and Information Technology") and the
    # colloquial forms applicants actually use ("MCIT").
    name_line = f"{program['degree_type']} program: {program['name']}"
    abbrev = (program.get("abbreviation") or "").strip()
    if abbrev:
        name_line += f" ({abbrev})"

    pathway = (program.get("phd_pathway_detail") or "").strip()
    pathway_note = ""
    if "terminal_professional" in pathway:
        pathway_note = "Terminal professional master's degree."
    elif "phd_pipeline" in pathway or "research_oriented" in pathway:
        pathway_note = "Research-oriented program; common pathway to PhD."

    # If the program is switcher-friendly, include it as a semantic property
    # so user interest profiles like "I'm transitioning from economics to CS"
    # naturally retrieve these programs without requiring the explicit filter.
    # The boolean column still acts as a hard filter in Stage 1.
    switcher_note = ""
    if program.get("switcher_friendly"):
        switcher_note = (
            "Designed for career switchers — admits and curricularly supports "
            "applicants without a prior background in the field."
        )

    # Normalize research_areas: source CSV has inconsistent spacing.
    raw_areas = program.get("research_areas") or ""
    areas = ", ".join(a.strip() for a in raw_areas.split(",") if a.strip())

    parts = [
        name_line,
        f"Offered by the {program['department']} at {program['university']}.",
        f"Research focus: {areas}." if areas else "",
        pathway_note,
        switcher_note,
        program.get("description") or "",
    ]
    return "\n".join(p for p in parts if p)


def main():
    # Step 1: Pull programs missing an embedding.
    result = supabase.table("programs").select(
        "id,name,abbreviation,degree_type,description,department,university,"
        "research_areas,phd_pathway_detail,switcher_friendly"
    ).is_("embedding", "null").execute()
    programs = result.data

    if not programs:
        print("All programs already embedded. Nothing to do.")
        return

    print(f"Embedding {len(programs)} programs with {EMBEDDING_MODEL}...")
    inputs = [build_embedding_input(p) for p in programs]

    # Step 2: Send in batches (DashScope v4 caps at 10 inputs/request).
    all_embeddings: list[list[float]] = []
    total_tokens = 0
    for i in range(0, len(inputs), BATCH_SIZE):
        chunk = inputs[i : i + BATCH_SIZE]
        response = dashscope.embeddings.create(
            model=EMBEDDING_MODEL,
            input=chunk,
            dimensions=EMBEDDING_DIMS,
            encoding_format="float",
        )
        all_embeddings.extend(item.embedding for item in response.data)
        total_tokens += response.usage.total_tokens

    # Step 3: Write back. pgvector accepts '[f1,f2,...]' as text input.
    for program, emb in zip(programs, all_embeddings):
        emb_str = "[" + ",".join(f"{x:.7f}" for x in emb) + "]"
        supabase.table("programs").update({"embedding": emb_str}).eq("id", program["id"]).execute()

    print(f"Done. {len(programs)} programs embedded.")
    print(f"Tokens used: {total_tokens:,}")


if __name__ == "__main__":
    main()
