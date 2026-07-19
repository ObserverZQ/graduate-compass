from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio, json
from uuid import UUID

from apps.api.schemas.match import EventName, MatchEvent

router = APIRouter()

class MatchRequest(BaseModel):
    session_id: UUID # validate the session_id to avoid error in database
'''ERROR HANDLING
{
  "type": "error",
  "code": "PROFILE_NOT_REVIEWED",
  "message": "Complete profile review before requesting matches.",
  "retryable": false
}
'''
'''
SSE STAGES:
- run_started
- stage_started or stage_completed
- profile_loaded
- filters_applied
- candidate_scored
- explanation_started
- candidate_explained
- warning
- complete
- error
'''
# Historical prototype retained for development comparison. The active route
# uses deterministic_match_pipeline below; this sketch is not executed.
# TODO: match function, 5 stages, working in progress
async def match_pipeline(session_id: str):
    # Stage 1: Hard filter (deterministic, no LLM)
    # yield sse("stage", {"id": 1, "label": "Filtering programs by your hard requirements"})
    # candidates = await hard_filter(session_id)  # GPA/TOEFL/degree_type/preferences
    # yield sse("stage_done", {"id": 1, "count": len(candidates)})

    # Stage 2: Synthesize research interest profile (1 LLM call)
    # yield sse("stage", {"id": 2, "label": "Reading your resume and preferences to understand your profile"})
    # interest_profile = await synthesize_interests(session_id)
    # yield sse("stage_done", {"id": 2, "summary": interest_profile})

    # Stage 3: Vector retrieval (pgvector, no LLM)
    # yield sse("stage", {"id": 3, "label": "Finding programs aligned with your inclination"})
    # interest_embedding = await embed(interest_profile)
    # top_candidates = await pgvector_topk(candidates, interest_embedding, k=15)
    # yield sse("stage_done", {"id": 3, "count": len(top_candidates)})

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

    if False:
        yield None
    # todo return complete or error
    # PROFILE_NOT_REVIEWED if preference is null


async def deterministic_match_pipeline(session_id: UUID):
    """Orchestrate deterministic matching and emit validated SSE events.

    Data loading, scoring, and terminal behavior will be added through the
    separately reviewed implementation patches. Keeping a distinct name makes
    it unambiguous that the route does not execute the historical prototype.
    """
    if False:
        yield ""


def format_match_event(event: MatchEvent) -> str:
    """Frame one validated matching event according to the SSE protocol."""
    event_name = EventName(event.type).value
    return f"event: {event_name}\ndata: {event.model_dump_json()}\n\n"


@router.post("/stream")
async def match_stream(req: MatchRequest):
    return StreamingResponse(
        deterministic_match_pipeline(req.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
