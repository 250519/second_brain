"""FastAPI application factory for the Second Brain API."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import graph, ingest, query, search, wiki


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Ensure wiki directories exist before serving requests."""
    from ..wiki import ensure_dirs
    ensure_dirs()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Second Brain API",
        description=(
            "Personal knowledge wiki powered by Claude. "
            "Ingest sources, query your wiki, and analyze your knowledge graph."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global error handler ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {exc}"},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(ingest.router,  prefix="/api/v1/ingest",  tags=["Ingest"])
    app.include_router(query.router,   prefix="/api/v1/query",   tags=["Query"])
    app.include_router(wiki.router,    prefix="/api/v1/wiki",    tags=["Wiki"])
    app.include_router(graph.router,   prefix="/api/v1/graph",   tags=["Graph"])
    app.include_router(search.router,  prefix="/api/v1/search",  tags=["Search"])

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Service health check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
