"""Ingest router — URL, text, file upload, and batch ingestion.

All ingest operations are asynchronous: they return a job_id immediately
and run the heavy compilation in a background thread. Poll
GET /api/v1/ingest/jobs/{job_id} for the result.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from ...agents import compiler
from ...reader import read_source
from ...wiki import read_index
from ..jobs import job_store
from ..models import IngestBatchRequest, IngestResult, IngestTextRequest, IngestURLRequest, JobStatus

router = APIRouter()

_ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


# ── Background worker ─────────────────────────────────────────────────────────

def _run_ingest(job_id: str, content: str, source_name: str) -> None:
    """Worker executed in a background thread for every ingest variant."""
    job_store.set_running(job_id)
    try:
        pages = compiler.ingest(content, source_name, read_index())
        job_store.set_done(
            job_id,
            IngestResult(source_name=source_name, pages_written=pages, count=len(pages)),
        )
    except Exception as exc:
        job_store.set_failed(job_id, str(exc))


def _run_ingest_url(job_id: str, url: str, source_name: str | None) -> None:
    """Fetch URL content then ingest — both steps happen in background."""
    job_store.set_running(job_id)
    try:
        content, name = read_source(url)
        final_name = source_name or name
        pages = compiler.ingest(content, final_name, read_index())
        job_store.set_done(
            job_id,
            IngestResult(source_name=final_name, pages_written=pages, count=len(pages)),
        )
    except Exception as exc:
        job_store.set_failed(job_id, str(exc))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/url", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
def ingest_url(body: IngestURLRequest, background_tasks: BackgroundTasks) -> JobStatus:
    """
    Ingest a URL (article, YouTube video, or documentation page).

    Returns a job immediately. Poll `GET /jobs/{job_id}` to check progress.
    """
    job_id = job_store.create()
    background_tasks.add_task(_run_ingest_url, job_id, body.url, body.source_name)
    return job_store.get(job_id)  # type: ignore[return-value]


@router.post("/text", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
def ingest_text(body: IngestTextRequest, background_tasks: BackgroundTasks) -> JobStatus:
    """
    Ingest raw text content directly (e.g. copied notes or transcripts).

    Returns a job immediately. Poll `GET /jobs/{job_id}` to check progress.
    """
    job_id = job_store.create()
    background_tasks.add_task(_run_ingest, job_id, body.content, body.source_name)
    return job_store.get(job_id)  # type: ignore[return-value]


@router.post("/file", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> JobStatus:
    """
    Ingest an uploaded file (.txt, .md, or .pdf).

    Returns a job immediately. Poll `GET /jobs/{job_id}` to check progress.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    raw_bytes = await file.read()
    source_name = file.filename or "uploaded-file"

    # Write to a temp file so read_source's PDF/text parsers can handle it
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    try:
        content, _ = read_source(str(tmp_path))
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    job_id = job_store.create()
    background_tasks.add_task(_run_ingest, job_id, content, source_name)
    return job_store.get(job_id)  # type: ignore[return-value]


@router.post("/batch", response_model=list[JobStatus], status_code=status.HTTP_202_ACCEPTED)
def ingest_batch(body: IngestBatchRequest, background_tasks: BackgroundTasks) -> list[JobStatus]:
    """
    Ingest multiple URLs in parallel — one background job per URL.

    Returns a list of job statuses. Poll each `GET /jobs/{job_id}` individually.
    """
    jobs: list[JobStatus] = []
    for url in body.urls:
        url = url.strip().rstrip(")>.,\n")
        job_id = job_store.create()
        background_tasks.add_task(_run_ingest_url, job_id, url, None)
        jobs.append(job_store.get(job_id))  # type: ignore[arg-type]
    return jobs


@router.get("/jobs", response_model=list[JobStatus])
def list_jobs() -> list[JobStatus]:
    """Return all ingest jobs (pending, running, done, failed)."""
    return job_store.all_jobs()


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    """Poll the status of a specific ingest job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job
