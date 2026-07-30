import gzip
import os
import subprocess
import sys
import tarfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "job_logs"
CSV_FILE = BASE_DIR / "LogsHillstoneDaily.csv"
LOG_DIR.mkdir(parents=True, exist_ok=True)

JobName = Literal["export_hillstone", "insert_log"]
JobState = Literal["queued", "running", "succeeded", "failed"]

SCRIPTS: Dict[JobName, Path] = {
    "export_hillstone": BASE_DIR / "Job_export_hillstone.py",
    "insert_log": BASE_DIR / "insert_log.py",
}


class Job(BaseModel):
    job_id: str
    job_name: JobName
    state: JobState
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    log_file: str


app = FastAPI(
    title="Hillstone Job API",
    version="1.0.0",
    description="Run Hillstone export and PostgreSQL insert jobs.",
)

jobs: Dict[str, Job] = {}
active_jobs: Dict[JobName, str] = {}
jobs_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hillstone-job")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_job(job_id: str, job_name: JobName) -> None:
    script_path = SCRIPTS[job_name]
    log_path = LOG_DIR / f"{job_id}_{job_name}.log"

    with jobs_lock:
        job = jobs[job_id]
        job.state = "running"
        job.started_at = utc_now()

    exit_code = -1
    try:
        child_environment = os.environ.copy()
        child_environment["PYTHONIOENCODING"] = "utf-8"

        with log_path.open("w", encoding="utf-8") as log_stream:
            process = subprocess.run(
                [sys.executable, "-u", str(script_path)],
                cwd=str(BASE_DIR),
                env=child_environment,
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        exit_code = process.returncode
    except Exception as error:
        with log_path.open("a", encoding="utf-8") as log_stream:
            log_stream.write(f"\nAPI job runner error: {error}\n")
    finally:
        with jobs_lock:
            job = jobs[job_id]
            job.exit_code = exit_code
            job.state = "succeeded" if exit_code == 0 else "failed"
            job.finished_at = utc_now()
            active_jobs.pop(job_name, None)


def create_job(job_name: JobName) -> Job:
    script_path = SCRIPTS[job_name]
    if not script_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Script not found: {script_path.name}",
        )

    with jobs_lock:
        if active_jobs:
            running_job_name, running_job_id = next(iter(active_jobs.items()))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Another job is already queued or running",
                    "job_name": running_job_name,
                    "job_id": running_job_id,
                },
            )

        job_id = uuid4().hex
        log_path = LOG_DIR / f"{job_id}_{job_name}.log"
        job = Job(
            job_id=job_id,
            job_name=job_name,
            state="queued",
            created_at=utc_now(),
            log_file=log_path.name,
        )
        jobs[job_id] = job
        active_jobs[job_name] = job_id

    executor.submit(run_job, job_id, job_name)
    return job


def stream_csv_file(archive_member_name: Optional[str] = None):
    if archive_member_name:
        with tarfile.open(CSV_FILE, "r:*") as archive:
            member_stream = archive.extractfile(archive_member_name)
            if member_stream is None:
                raise RuntimeError(
                    f"Cannot read {archive_member_name} from TAR archive"
                )

            with member_stream:
                while True:
                    chunk = member_stream.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
        return

    with CSV_FILE.open("rb") as source_stream:
        is_gzip = source_stream.read(2) == b"\x1f\x8b"

    open_file = gzip.open if is_gzip else open
    with open_file(CSV_FILE, "rb") as csv_stream:
        while True:
            chunk = csv_stream.read(1024 * 1024)
            if not chunk:
                break
            yield chunk


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/files/logs-hillstone.csv",
    response_class=StreamingResponse,
    tags=["files"],
)
def download_logs_hillstone_csv() -> StreamingResponse:
    with jobs_lock:
        export_job_id = active_jobs.get("export_hillstone")

    if export_job_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "The CSV export is still running",
                "job_id": export_job_id,
            },
        )

    if not CSV_FILE.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LogsHillstoneDaily.csv not found",
        )

    archive_member_name = None
    if tarfile.is_tarfile(CSV_FILE):
        with tarfile.open(CSV_FILE, "r:*") as archive:
            csv_members = [
                member
                for member in archive.getmembers()
                if member.isfile() and member.name.lower().endswith(".csv")
            ]

        if not csv_members:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No CSV file found inside the TAR archive",
            )
        archive_member_name = csv_members[0].name

    return StreamingResponse(
        stream_csv_file(archive_member_name),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="LogsHillstoneDaily.csv"'
            ),
            "Cache-Control": "no-store",
        },
    )


@app.post(
    "/jobs/export-hillstone",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def start_export_hillstone() -> Job:
    return create_job("export_hillstone")


@app.post(
    "/jobs/insert-log",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def start_insert_log() -> Job:
    return create_job("insert_log")


@app.get(
    "/jobs",
    response_model=List[Job],
    tags=["jobs"],
)
def list_jobs() -> List[Job]:
    with jobs_lock:
        return list(jobs.values())


@app.get(
    "/jobs/{job_id}",
    response_model=Job,
    tags=["jobs"],
)
def get_job(job_id: str) -> Job:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        return job


@app.get(
    "/jobs/{job_id}/log",
    response_class=FileResponse,
    tags=["jobs"],
)
def download_job_log(job_id: str) -> FileResponse:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        log_path = LOG_DIR / job.log_file

    if not log_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job log is not available yet",
        )

    return FileResponse(
        path=log_path,
        media_type="text/plain; charset=utf-8",
        filename=log_path.name,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=12010,
    )
