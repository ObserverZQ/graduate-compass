"""Event helpers give the workflow readable progress and ordered SSE messages.

The workflow creates typed events here; stream.py sends them to the browser.
"""

import time
from uuid import UUID, uuid4

from apps.api.schemas.match import (
    ErrorEvent,
    MatchErrorCode,
    MatchStage,
    StageCompletedEvent,
    StageProgressEvent,
    StageStartedEvent,
)


class EventWriter:
    """Assign one run ID and consecutive numbers to events from a single run."""

    def __init__(self) -> None:
        """Start a fresh event sequence for each matching request."""

        self.run_id: UUID = uuid4()
        self.sequence = 0

    def next(self) -> int:
        """Return the next number so clients can detect missed events."""

        self.sequence += 1
        return self.sequence

    def started(self, stage: MatchStage, message: str) -> StageStartedEvent:
        """Tell the browser which part of matching began."""

        return StageStartedEvent(
            run_id=self.run_id, sequence=self.next(), stage=stage, message=message
        )

    def finished(
        self, stage: MatchStage, message: str, started_at: float,
        count: int | None = None,
    ) -> StageCompletedEvent:
        """Report a completed stage and its measured duration."""

        return StageCompletedEvent(
            run_id=self.run_id,
            sequence=self.next(),
            stage=stage,
            message=message,
            count=count,
            duration_ms=max(0, round((time.perf_counter() - started_at) * 1000)),
        )

    def progress(
        self, stage: MatchStage, message: str, processed: int, total: int,
    ) -> StageProgressEvent:
        """Report work actually completed out of a known total."""

        return StageProgressEvent(
            run_id=self.run_id, sequence=self.next(), stage=stage,
            message=message, processed=processed, total=total,
        )

    def error(
        self, code: MatchErrorCode, message: str, retryable: bool,
    ) -> ErrorEvent:
        """End a run with a safe message suitable for the browser."""

        return ErrorEvent(
            run_id=self.run_id, sequence=self.next(), code=code,
            message=message, retryable=retryable,
        )


def report_progress(processed: int, total: int) -> bool:
    """Keep updates useful while always reporting the first and final item."""

    return processed == 1 or processed == total or processed % 4 == 0
