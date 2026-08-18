from datetime import datetime

from pydantic import BaseModel

from subtitle_maker.jobs.models import JobRecord, JobStatus


class JobResponse(BaseModel):
    id: str
    filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    segment_count: int | None = None
    error: str | None = None
    status_url: str
    download_url: str | None = None
    video_download_url: str | None = None

    @classmethod
    def from_record(cls, record: JobRecord) -> "JobResponse":
        download = (
            f"/v1/jobs/{record.id}/subtitles"
            if record.status is JobStatus.SUCCEEDED
            else None
        )
        return cls(
            id=record.id,
            filename=record.original_filename,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            segment_count=record.segment_count,
            error=record.error,
            status_url=f"/v1/jobs/{record.id}",
            download_url=download,
            video_download_url=(
                f"/v1/jobs/{record.id}/video"
                if record.status is JobStatus.SUCCEEDED
                else None
            ),
        )
