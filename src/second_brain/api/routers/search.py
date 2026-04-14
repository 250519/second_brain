"""Web search router — proxies DuckDuckGo so the frontend avoids CORS issues."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
def web_search(q: str = Query(..., description="Search query")):
    """Search the web via DuckDuckGo and return top 5 results."""
    try:
        from duckduckgo_search import DDGS
        raw = list(DDGS().text(q, max_results=5))
    except Exception as e:
        return {"results": [], "error": str(e)}

    return {
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
        ]
    }
