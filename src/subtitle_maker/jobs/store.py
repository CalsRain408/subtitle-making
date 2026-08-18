import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from subtitle_maker.jobs.models import JobRecord, JobStatus


class JobNotFoundError(KeyError):
    pass


class FileJobStore:
    """A small durable-on-disk store suitable for the single-process V1."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def create(self, original_filename: str) -> JobRecord:
        now = datetime.now(UTC)
        record = JobRecord(
            id=str(uuid4()),
            original_filename=original_filename,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        self.job_dir(record.id).mkdir(parents=True, exist_ok=False)
        self.save(record)
        return record

    def get(self, job_id: str) -> JobRecord:
        path = self.job_dir(job_id) / "job.json"
        with self._lock:
            if not path.is_file():
                raise JobNotFoundError(job_id)
            payload = json.loads(path.read_text(encoding="utf-8"))
        return JobRecord(
            id=payload["id"],
            original_filename=payload["original_filename"],
            status=JobStatus(payload["status"]),
            created_at=datetime.fromisoformat(payload["created_at"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
            segment_count=payload.get("segment_count"),
            error=payload.get("error"),
        )

    def save(self, record: JobRecord) -> None:
        path = self.job_dir(record.id) / "job.json"
        payload = {
            "id": record.id,
            "original_filename": record.original_filename,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "segment_count": record.segment_count,
            "error": record.error,
        }
        temporary = path.with_suffix(".json.tmp")
        with self._lock:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(path)

    def job_dir(self, job_id: str) -> Path:
        try:
            normalized = str(UUID(job_id))
        except ValueError as exc:
            raise JobNotFoundError(job_id) from exc
        return self.root / normalized

    def input_path(self, job_id: str, suffix: str) -> Path:
        safe_suffix = suffix.lower() if suffix and len(suffix) <= 10 else ".video"
        if not safe_suffix.startswith(".") or not safe_suffix[1:].isalnum():
            safe_suffix = ".video"
        return self.job_dir(job_id) / f"input{safe_suffix}"

    def output_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "subtitles.bilingual.srt"

    def video_output_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "video.bilingual.mp4"
