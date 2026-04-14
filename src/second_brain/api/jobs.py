"""In-memory job store for tracking background ingest tasks."""

import uuid
from threading import Lock

from .models import IngestResult, JobStatus


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._lock = Lock()

    def create(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = JobStatus(job_id=job_id, status="pending")
        return job_id

    def get(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)

    def set_running(self, job_id: str) -> None:
        with self._lock:
            if job := self._jobs.get(job_id):
                job.status = "running"

    def set_done(self, job_id: str, result: IngestResult) -> None:
        with self._lock:
            if job := self._jobs.get(job_id):
                job.status = "done"
                job.result = result

    def set_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            if job := self._jobs.get(job_id):
                job.status = "failed"
                job.error = error

    def all_jobs(self) -> list[JobStatus]:
        return list(self._jobs.values())


# Singleton shared across the process
job_store = JobStore()
