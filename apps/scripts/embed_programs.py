"""
One-shot script: backfill embeddings for all programs where embedding IS NULL.
Uses Aliyun DashScope text-embedding-v4 (1536 dims, matches schema).
"""

import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI  # DashScope is OpenAI-compatible
from sqlalchemy import text

from apps.api.database import SessionLocal

load_dotenv()

EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIMS = 1536  # matches programs.embedding vector(1536)

# DashScope endpoints:
#   China (Beijing):     https://dashscope.aliyuncs.com/compatible-mode/v1
#   International (SG):  https://dashscope-intl.aliyuncs.com/compatible-mode/v1
# Use the China endpoint since you're in mainland China — lower latency, same model.
dashscope_client = AsyncOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def build_embedding_input(program: dict) -> str:
    pathway = (program.get("phd_pathway_detail") or "").strip()
    pathway_note = ""
    if "terminal_professional" in pathway:
        pathway_note = "Terminal professional master's degree."
    elif "phd_pipeline" in pathway or "research_oriented" in pathway:
        pathway_note = "Research-oriented program; common pathway to PhD."

    raw_areas = program.get("research_areas") or ""
    areas = ", ".join(a.strip() for a in raw_areas.split(",") if a.strip())

    parts = [
        f"{program['degree_type']} program: {program['name']}",
        f"Offered by the {program['department']} at {program['university']}.",
        f"Research focus: {areas}." if areas else "",
        pathway_note,
        program.get("description") or "",
    ]
    return "\n".join(p for p in parts if p)


async def main():
    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT id, name, degree_type, description, department,
                   university, research_areas, phd_pathway_detail
            FROM programs
            WHERE embedding IS NULL
        """))
        programs = [dict(r) for r in result.mappings().all()]

    if not programs:
        print("All programs already embedded. Nothing to do.")
        return

    print(f"Embedding {len(programs)} programs with {EMBEDDING_MODEL}...")
    inputs = [build_embedding_input(p) for p in programs]

    # DashScope's text-embedding-v4 has a per-request batch limit of 10 inputs.
    # text-embedding-v3 allowed 25 — check current docs if this changes.
    # For 23 programs this means 3 chunks.
    BATCH_SIZE = 10
    all_embeddings: list[list[float]] = []
    total_tokens = 0

    for i in range(0, len(inputs), BATCH_SIZE):
        chunk = inputs[i : i + BATCH_SIZE]
        response = await dashscope_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=chunk,
            dimensions=EMBEDDING_DIMS,  # only v3/v4 support this parameter
            encoding_format="float",
        )
        all_embeddings.extend(item.embedding for item in response.data)
        total_tokens += response.usage.total_tokens

    async with SessionLocal() as session:
        for program, emb in zip(programs, all_embeddings):
            emb_str = "[" + ",".join(f"{x:.7f}" for x in emb) + "]"
            await session.execute(text("""
                UPDATE programs
                SET embedding = (:emb)::vector
                WHERE id = :id
            """), {"emb": emb_str, "id": program["id"]})
        await session.commit()

    print(f"Done. {len(programs)} programs embedded.")
    print(f"Tokens used: {total_tokens:,}")


if __name__ == "__main__":
    asyncio.run(main())