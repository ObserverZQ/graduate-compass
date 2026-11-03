"""The HTTP router delegates matching work to the streaming service.

Request validation and response headers stay here; orchestration, tool calls,
event construction, and SSE framing live in the matching service package.
"""

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from apps.api.schemas.match import ContractModel
from apps.api.services.matching.stream import deterministic_match_pipeline


router = APIRouter()


class MatchRequest(ContractModel):
    """Identify the reviewed anonymous profile used for one matching run."""

    session_id: UUID


@router.post("/stream")
async def match_stream(req: MatchRequest) -> StreamingResponse:
    """Stream accessible progress and explainable results for one profile."""

    return StreamingResponse(
        deterministic_match_pipeline(req.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
