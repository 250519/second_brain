"""Wiki router — status, index, page browsing, and lint."""

from fastapi import APIRouter, HTTPException, status

from ...agents import review
from ...config import IDEAS_FILE, RAW_DIR, WIKI_DIR
from ...wiki import read_all_pages, read_index
from ..models import LintResponse, WikiIndexResponse, WikiPage, WikiStatusResponse

router = APIRouter()


@router.get("/status", response_model=WikiStatusResponse)
def wiki_status() -> WikiStatusResponse:
    """Return wiki statistics: page counts by type, raw sources, and ideas count."""
    pages = read_all_pages()

    by_type: dict[str, int] = {}
    for path in pages:
        t = path.split("/")[0]
        by_type[t] = by_type.get(t, 0) + 1

    raw_files = (
        [f for f in RAW_DIR.glob("*") if f.name != ".gitkeep"] if RAW_DIR.exists() else []
    )
    ideas_count = 0
    if IDEAS_FILE.exists():
        ideas_count = sum(1 for line in IDEAS_FILE.read_text().splitlines() if line.startswith("- "))

    return WikiStatusResponse(
        total_pages=len(pages),
        by_type=by_type,
        raw_sources=len(raw_files),
        ideas_count=ideas_count,
    )


@router.get("/index", response_model=WikiIndexResponse)
def wiki_index() -> WikiIndexResponse:
    """Return the full wiki index (catalog of all pages)."""
    return WikiIndexResponse(index=read_index())


@router.get("/pages", response_model=list[str])
def list_pages() -> list[str]:
    """List all wiki page paths (relative to wiki root)."""
    return sorted(read_all_pages().keys())


@router.get("/pages/{page_type}/{slug}", response_model=WikiPage)
def get_page(page_type: str, slug: str) -> WikiPage:
    """
    Return the content of a specific wiki page.

    `page_type` is one of: summary, concept, connection, insight, qa, lint.
    `slug` is the filename without the .md extension.
    """
    path = WIKI_DIR / page_type / f"{slug}.md"
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page not found: {page_type}/{slug}.md",
        )
    return WikiPage(path=f"{page_type}/{slug}.md", content=path.read_text())


@router.get("/ideas")
def get_ideas() -> dict[str, list[str]]:
    """Return all research ideas and questions generated during ingestion."""
    if not IDEAS_FILE.exists():
        return {"ideas": []}
    ideas = [line[2:] for line in IDEAS_FILE.read_text().splitlines() if line.startswith("- ")]
    return {"ideas": ideas}


@router.post("/lint", response_model=LintResponse)
def lint() -> LintResponse:
    """
    Run a health check on the wiki.

    Checks for contradictions, stale claims, orphan concepts, missing
    wikilinks, and knowledge gaps with suggested web search queries.
    Saves the report to wiki/lint/.
    """
    try:
        report = review.lint()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return LintResponse(report=report)
