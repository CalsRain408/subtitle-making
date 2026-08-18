import shutil
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from subtitle_maker.api.schemas import JobResponse
from subtitle_maker.bootstrap import build_pipeline
from subtitle_maker.config import Settings
from subtitle_maker.jobs.models import JobStatus
from subtitle_maker.jobs.runner import JobRunner
from subtitle_maker.jobs.store import FileJobStore, JobNotFoundError

settings = Settings()
store = FileJobStore(settings.data_dir / "jobs")
runner = JobRunner(store=store, pipeline_factory=lambda: build_pipeline(settings))
web_dir = Path(__file__).resolve().parents[1] / "web" / "static"

app = FastAPI(
    title="Subtitle Maker API",
    version="0.1.0",
    description="Generate bilingual English-Chinese SRT subtitles from uploaded videos.",
)
app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(web_dir / "index.html", media_type="text/html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    background_tasks: BackgroundTasks,
    video: Annotated[UploadFile, File()],
) -> JobResponse:
    filename = Path(video.filename or "upload.video").name
    record = store.create(filename)
    destination = store.input_path(record.id, Path(filename).suffix)
    try:
        with destination.open("wb") as output:
            shutil.copyfileobj(video.file, output)
    except Exception as exc:
        store.save(record.mark_failed("Unable to save uploaded video"))
        raise HTTPException(status_code=500, detail="Unable to save uploaded video") from exc
    finally:
        await video.close()

    if destination.stat().st_size == 0:
        store.save(record.mark_failed("Uploaded video is empty"))
        raise HTTPException(status_code=400, detail="Uploaded video is empty")

    background_tasks.add_task(runner.run, record.id, destination)
    return JobResponse.from_record(record)


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    try:
        return JobResponse.from_record(store.get(job_id))
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.get("/v1/jobs/{job_id}/subtitles")
def download_subtitles(job_id: str) -> FileResponse:
    try:
        record = store.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    if record.status is not JobStatus.SUCCEEDED:
        raise HTTPException(status_code=409, detail=f"Job is {record.status.value}")
    output = store.output_path(job_id)
    if not output.is_file():
        raise HTTPException(status_code=500, detail="Subtitle output is missing")
    return FileResponse(
        output,
        media_type="application/x-subrip; charset=utf-8",
        filename=f"{Path(record.original_filename).stem}.bilingual.srt",
    )
