"""Pydantic request/response schemas for the Second Brain API."""

from typing import Literal

from pydantic import BaseModel, field_validator


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestURLRequest(BaseModel):
    url: str
    source_name: str | None = None


class IngestTextRequest(BaseModel):
    content: str
    source_name: str


class IngestBatchRequest(BaseModel):
    urls: list[str]

    @field_validator("urls")
    @classmethod
    def non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls must not be empty")
        return v


class IngestResult(BaseModel):
    source_name: str
    pages_written: list[str]
    count: int


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "failed"]
    result: IngestResult | None = None
    error: str | None = None


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    file_back: bool = True


class QueryResponse(BaseModel):
    answer: str


# ── Wiki ──────────────────────────────────────────────────────────────────────

class WikiPage(BaseModel):
    path: str
    content: str


class WikiStatusResponse(BaseModel):
    total_pages: int
    by_type: dict[str, int]
    raw_sources: int
    ideas_count: int


class WikiIndexResponse(BaseModel):
    index: str


# ── Lint ──────────────────────────────────────────────────────────────────────

class LintResponse(BaseModel):
    report: str


# ── Graph ─────────────────────────────────────────────────────────────────────

class GraphResponse(BaseModel):
    report: str
