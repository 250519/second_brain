# FastAPI Backend Reference

## Table of Contents
1. [api/main.py](#apimainpy)
2. [api/models.py](#apimodelspy)
3. [api/jobs.py](#apijobspy)
4. [api/routers/ingest.py](#apiroutersingestpy)
5. [api/routers/query.py](#apiroutersquerypy)
6. [api/routers/wiki.py](#apirouterswikipy)
7. [api/routers/graph.py](#apiroutersgraphpy)
8. [backend/server.py](#backendserverpy)
9. [CLI serve command](#cli-serve-command)

---

## api/main.py

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import graph, ingest, query, wiki


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from ..wiki import ensure_dirs
    ensure_dirs()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Second Brain API",
        description="Personal knowledge wiki powered by Claude.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Ingest"])
    app.include_router(query.router,  prefix="/api/v1/query",  tags=["Query"])
    app.include_router(wiki.router,   prefix="/api/v1/wiki",   tags=["Wiki"])
    app.include_router(graph.router,  prefix="/api/v1/graph",  tags=["Graph"])

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

---

## api/models.py

```python
from typing import Literal
from pydantic import BaseModel, field_validator


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

class QueryRequest(BaseModel):
    question: str
    file_back: bool = True

class QueryResponse(BaseModel):
    answer: str

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

class LintResponse(BaseModel):
    report: str

class GraphResponse(BaseModel):
    report: str
```

---

## api/jobs.py

```python
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


job_store = JobStore()
```

---

## api/routers/ingest.py

```python
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from ...agents import compiler
from ...reader import read_source
from ...wiki import read_index
from ..jobs import job_store
from ..models import IngestBatchRequest, IngestResult, IngestTextRequest, IngestURLRequest, JobStatus

router = APIRouter()
_ALLOWED = {".txt", ".md", ".pdf"}


def _run_ingest_url(job_id: str, url: str, source_name: str | None) -> None:
    """Fetch URL + compile — both happen in the background thread."""
    job_store.set_running(job_id)
    try:
        content, name = read_source(url)
        final_name = source_name or name
        pages = compiler.ingest(content, final_name, read_index())
        job_store.set_done(job_id, IngestResult(
            source_name=final_name, pages_written=pages, count=len(pages)
        ))
    except Exception as exc:
        job_store.set_failed(job_id, str(exc))


def _run_ingest(job_id: str, content: str, source_name: str) -> None:
    job_store.set_running(job_id)
    try:
        pages = compiler.ingest(content, source_name, read_index())
        job_store.set_done(job_id, IngestResult(
            source_name=source_name, pages_written=pages, count=len(pages)
        ))
    except Exception as exc:
        job_store.set_failed(job_id, str(exc))


@router.post("/url", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
def ingest_url(body: IngestURLRequest, background_tasks: BackgroundTasks) -> JobStatus:
    """Ingest a URL. Returns job_id immediately — poll GET /jobs/{id} for result."""
    job_id = job_store.create()
    background_tasks.add_task(_run_ingest_url, job_id, body.url, body.source_name)
    return job_store.get(job_id)  # type: ignore[return-value]


@router.post("/text", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
def ingest_text(body: IngestTextRequest, background_tasks: BackgroundTasks) -> JobStatus:
    """Ingest raw text. Returns job_id immediately."""
    job_id = job_store.create()
    background_tasks.add_task(_run_ingest, job_id, body.content, body.source_name)
    return job_store.get(job_id)  # type: ignore[return-value]


@router.post("/file", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def ingest_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> JobStatus:
    """Upload a .txt, .md, or .pdf file. Returns job_id immediately."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED:
        raise HTTPException(status_code=415, detail=f"Unsupported type '{suffix}'. Allowed: {sorted(_ALLOWED)}")

    raw_bytes = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    try:
        content, _ = read_source(str(tmp_path))
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    job_id = job_store.create()
    background_tasks.add_task(_run_ingest, job_id, content, file.filename or "uploaded-file")
    return job_store.get(job_id)  # type: ignore[return-value]


@router.post("/batch", response_model=list[JobStatus], status_code=status.HTTP_202_ACCEPTED)
def ingest_batch(body: IngestBatchRequest, background_tasks: BackgroundTasks) -> list[JobStatus]:
    """Ingest multiple URLs — one background job per URL."""
    jobs: list[JobStatus] = []
    for url in body.urls:
        url = url.strip().rstrip(")>.,\n")
        job_id = job_store.create()
        background_tasks.add_task(_run_ingest_url, job_id, url, None)
        jobs.append(job_store.get(job_id))  # type: ignore[arg-type]
    return jobs


@router.get("/jobs", response_model=list[JobStatus])
def list_jobs() -> list[JobStatus]:
    return job_store.all_jobs()


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job
```

---

## api/routers/query.py

```python
from fastapi import APIRouter, HTTPException, status
from ...agents import query as query_agent
from ..models import QueryRequest, QueryResponse

router = APIRouter()

@router.post("", response_model=QueryResponse)
def query(body: QueryRequest) -> QueryResponse:
    """Answer a question. Non-trivial answers auto-filed back if file_back=True."""
    try:
        answer = query_agent.answer(body.question, file_back=body.file_back)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return QueryResponse(answer=answer)
```

---

## api/routers/wiki.py

```python
from fastapi import APIRouter, HTTPException, status
from ...agents import review
from ...config import IDEAS_FILE, RAW_DIR, WIKI_DIR
from ...wiki import read_all_pages, read_index
from ..models import LintResponse, WikiIndexResponse, WikiPage, WikiStatusResponse

router = APIRouter()

@router.get("/status", response_model=WikiStatusResponse)
def wiki_status() -> WikiStatusResponse:
    pages = read_all_pages()
    by_type: dict[str, int] = {}
    for path in pages:
        t = path.split("/")[0]
        by_type[t] = by_type.get(t, 0) + 1
    raw_files = [f for f in RAW_DIR.glob("*") if f.name != ".gitkeep"] if RAW_DIR.exists() else []
    ideas_count = sum(1 for l in IDEAS_FILE.read_text().splitlines() if l.startswith("- ")) if IDEAS_FILE.exists() else 0
    return WikiStatusResponse(total_pages=len(pages), by_type=by_type, raw_sources=len(raw_files), ideas_count=ideas_count)

@router.get("/index", response_model=WikiIndexResponse)
def wiki_index() -> WikiIndexResponse:
    return WikiIndexResponse(index=read_index())

@router.get("/pages", response_model=list[str])
def list_pages() -> list[str]:
    return sorted(read_all_pages().keys())

@router.get("/pages/{page_type}/{slug}", response_model=WikiPage)
def get_page(page_type: str, slug: str) -> WikiPage:
    path = WIKI_DIR / page_type / f"{slug}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Page not found: {page_type}/{slug}.md")
    return WikiPage(path=f"{page_type}/{slug}.md", content=path.read_text())

@router.get("/ideas")
def get_ideas() -> dict[str, list[str]]:
    if not IDEAS_FILE.exists():
        return {"ideas": []}
    return {"ideas": [l[2:] for l in IDEAS_FILE.read_text().splitlines() if l.startswith("- ")]}

@router.post("/lint", response_model=LintResponse)
def lint() -> LintResponse:
    try:
        return LintResponse(report=review.lint())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

---

## api/routers/graph.py

```python
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from ...graph import analyze, visualize
from ..models import GraphResponse

router = APIRouter()

@router.post("/analyze", response_model=GraphResponse)
def graph_analyze() -> GraphResponse:
    try:
        return GraphResponse(report=analyze())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/data")
def graph_data() -> JSONResponse:
    """Return graph as JSON nodes + edges for custom visualizations."""
    import networkx as nx
    from ...graph import _load_existing_triples, ensure_graph_dirs, TRIPLE_RE
    ensure_graph_dirs()
    existing = _load_existing_triples()
    if not existing:
        raise HTTPException(status_code=404, detail="Ontology is empty.")
    G: nx.DiGraph = nx.DiGraph()
    for triple in existing:
        m = TRIPLE_RE.match(triple)
        if m:
            G.add_edge(m.group("a"), m.group("b"), relation=m.group("rel"))
    centrality = nx.betweenness_centrality(G)
    nodes = [{"id": n, "centrality": round(centrality.get(n, 0), 4), "degree": G.degree(n)} for n in G.nodes()]
    edges = [{"source": u, "target": v, "relation": d.get("relation", "")} for u, v, d in G.edges(data=True)]
    return JSONResponse({"nodes": nodes, "edges": edges})

@router.get("/view")
def graph_view() -> FileResponse:
    """Serve interactive pyvis HTML visualization."""
    try:
        path = visualize()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return FileResponse(str(path), media_type="text/html")
```

---

## backend/server.py

```python
import argparse
import uvicorn

def main() -> None:
    parser = argparse.ArgumentParser(description="Second Brain API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    print(f"Starting API → http://{args.host}:{args.port}")
    print(f"  Swagger UI: http://localhost:{args.port}/docs")
    uvicorn.run("second_brain.api.main:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
```

---

## CLI serve command

Add to `cli.py`:

```python
@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True, type=int)
@click.option("--reload", is_flag=True, default=False, help="Auto-reload (dev only).")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI API server."""
    import uvicorn
    click.echo(f"Starting API on http://{host}:{port}  (docs: /docs)")
    uvicorn.run("<package>.api.main:app", host=host, port=port, reload=reload)
```
