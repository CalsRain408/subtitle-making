from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    original_filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    segment_count: int | None = None
    error: str | None = None

    def mark_running(self) -> "JobRecord":
        return replace(
            self,
            status=JobStatus.RUNNING,
            updated_at=datetime.now(UTC),
            error=None,
        )

    def mark_failed(self, error: str) -> "JobRecord":
        return replace(
            self,
            status=JobStatus.FAILED,
            updated_at=datetime.now(UTC),
            error=error,
        )

    def mark_succeeded(self, segment_count: int) -> "JobRecord":
        return replace(
            self,
            status=JobStatus.SUCCEEDED,
            updated_at=datetime.now(UTC),
            segment_count=segment_count,
            error=None,
        )
