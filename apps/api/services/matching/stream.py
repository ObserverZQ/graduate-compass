"""Streaming adapts workflow events to the SSE wire format.

The router exposes this generator, workflow.py supplies typed events, and
keep-alive comments protect slow connections without fabricating UX progress.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from uuid import UUID

from apps.api.schemas.match import EventName, MatchEvent
from apps.api.services.matching.workflow import iter_match_events


KEEP_ALIVE_SECONDS = 15.0
KEEP_ALIVE_COMMENT = ": keep-alive\n\n"


async def deterministic_match_pipeline(session_id: UUID) -> AsyncIterator[str]:
    """Frame validated events and send transport-only heartbeat comments."""

    events = iter_match_events(session_id)
    pending: asyncio.Task[MatchEvent] | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(events))
            done, _ = await asyncio.wait({pending}, timeout=KEEP_ALIVE_SECONDS)
            if not done:
                yield KEEP_ALIVE_COMMENT
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                pending = None
                break
            pending = None
            yield format_match_event(event)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending
        await events.aclose()


def format_match_event(event: MatchEvent) -> str:
    """Frame one validated matching event according to the SSE protocol."""

    event_name = EventName(event.type).value
    return f"event: {event_name}\ndata: {event.model_dump_json()}\n\n"
