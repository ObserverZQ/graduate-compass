from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio, json

router = APIRouter()

class MatchRequest(BaseModel):
    session_id: str

async def match_pipeline(session_id: str):
    # Stage 1: Hard filter (deterministic, no LLM)
    yield sse("stage", {"id": 1, "label": "Filtering programs by your hard requirements"})
    candidates = await hard_filter(session_id)  # GPA/TOEFL/degree_type/preferences
    yield sse("stage_done", {"id": 1, "count": len(candidates)})

    # Stage 2: Synthesize research interest profile (1 LLM call)
    yield sse("stage", {"id": 2, "label": "Reading your resume and preferences to understand your profile"})
    interest_profile = await synthesize_interests(session_id)
    yield sse("stage_done", {"id": 2, "summary": interest_profile})

    # Stage 3: Vector retrieval (pgvector, no LLM)
    yield sse("stage", {"id": 3, "label": "Finding programs aligned with your inclination"})
    interest_embedding = await embed(interest_profile)
    top_candidates = await pgvector_topk(candidates, interest_embedding, k=15)
    yield sse("stage_done", {"id": 3, "count": len(top_candidates)})

    # Stage 4: Per-program reasoning (parallel LLM calls)
    # yield sse("stage", {"id": 4, "label": "Analyzing fit for each program"})
    # reasoning_tasks = [reason_about_program(p, session_id) for p in top_candidates]
    # for completed in asyncio.as_completed(reasoning_tasks):
    #     program_analysis = await completed
    #     yield sse("program_analyzed", program_analysis)  # streams as each finishes!

    # # Stage 5: Final ranking + synthesis
    # yield sse("stage", {"id": 5, "label": "Ranking your top matches"})
    # final_ranking = await synthesize_ranking(top_candidates)
    # yield sse("complete", final_ranking)

@router.post("/stream")
async def match_stream(req: MatchRequest):
    return StreamingResponse(
        match_pipeline(req.session_id),
        media_type="text/event-stream",
    )

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"