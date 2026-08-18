from collections.abc import Callable
from pathlib import Path

from subtitle_maker.jobs.store import FileJobStore
from subtitle_maker.pipeline.service import SubtitlePipeline


class JobRunner:
    def __init__(
        self,
        store: FileJobStore,
        pipeline_factory: Callable[[], SubtitlePipeline],
    ) -> None:
        self.store = store
        self.pipeline_factory = pipeline_factory

    def run(self, job_id: str, video_path: Path) -> None:
        record = self.store.get(job_id)
        self.store.save(record.mark_running())
        try:
            result = self.pipeline_factory().process(
                video_path=video_path,
                output_path=self.store.output_path(job_id),
                work_dir=self.store.job_dir(job_id) / "work",
            )
        except Exception as exc:
            failed = self.store.get(job_id).mark_failed(str(exc)[:2000])
            self.store.save(failed)
            return

        succeeded = self.store.get(job_id).mark_succeeded(result.segment_count)
        self.store.save(succeeded)
