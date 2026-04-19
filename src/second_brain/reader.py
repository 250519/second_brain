import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
import html2text

JS_DETECTION_THRESHOLD = 300  # chars — below this we assume JS-rendered

# Social media / login-walled domains — always route through Jina.ai reader
_SOCIAL_DOMAINS = {
    "linkedin.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "facebook.com",
    "threads.net",
    "reddit.com",
    "tiktok.com",
}


def read_source(source: str) -> tuple[str, str]:
    """Return (content, source_name) for a local file path or URL."""
    if _is_youtube(source):
        return _read_youtube(source)

    if source.startswith("http://") or source.startswith("https://"):
        if _is_social_media(source):
            content = _read_social_post(source)
        else:
            content = _fetch_url(source)
            if len(content.strip()) < JS_DETECTION_THRESHOLD:
                content = _read_js_doc(source)
        return content, source

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Not found: {source}")

    if path.suffix.lower() == ".pdf":
        return _read_pdf(path), path.name

    return path.read_text(encoding="utf-8", errors="replace"), path.name


# ── Social media ─────────────────────────────────────────────────────────────

def _is_social_media(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(d in domain for d in _SOCIAL_DOMAINS)


def _read_social_post(url: str) -> str:
    """Fetch social media post content via Jina.ai's free reader API.

    Jina.ai (r.jina.ai) renders JS, bypasses many paywalls, and returns
    clean markdown — no API key required for basic usage.

    Falls back to DuckDuckGo search if Jina returns too little content
    (e.g. LinkedIn posts that require login).
    """
    jina_url = f"https://r.jina.ai/{url}"
    try:
        content = _fetch_url(jina_url)
        if len(content.strip()) > JS_DETECTION_THRESHOLD:
            return content
    except Exception:
        pass

    # Jina couldn't get enough content (login-walled) — try DuckDuckGo
    return _read_js_doc(url)


# ── YouTube ──────────────────────────────────────────────────────────────────

def _is_youtube(url: str) -> bool:
    return "youtu.be/" in url or "youtube.com/watch" in url


def _extract_video_id(url: str) -> str | None:
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)
        return match.group(1) if match else None
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    ids = qs.get("v", [])
    return ids[0] if ids else None


def _read_youtube(url: str) -> tuple[str, str]:
    """Fetch YouTube transcript via Supadata SDK.

    Requires SUPADATA_API_KEY env var — sign up free at https://supadata.ai
    """
    import os
    from supadata import Supadata, SupadataError

    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url}")

    api_key = os.environ.get("SUPADATA_API_KEY", "")
    if not api_key:
        raise RuntimeError("SUPADATA_API_KEY env var is not set")

    client = Supadata(api_key=api_key)
    try:
        transcript = client.youtube.transcript(video_id=video_id, text=True)
    except SupadataError as e:
        raise RuntimeError(
            f"Supadata failed to fetch transcript for {url}: {e}"
        ) from e

    text = transcript.content if hasattr(transcript, "content") else None
    if not text:
        raise RuntimeError(f"Supadata returned empty transcript for {url}")

    content = f"# YouTube Transcript\n\nSource: {url}\n\n{text}"
    return content, f"youtube/{video_id}"


# ── JS-rendered docs fallback ─────────────────────────────────────────────────

def _read_js_doc(url: str) -> str:
    """For JS-rendered pages: use DuckDuckGo to find sub-pages and fetch them."""
    parsed = urlparse(url)
    domain = parsed.netloc
    # Build search keywords from path segments
    path_words = " ".join(
        p for p in parsed.path.strip("/").replace("-", " ").split("/") if p
    )
    query = f"site:{domain} {path_words}".strip()
    if not path_words:
        query = f"site:{domain} overview introduction"

    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(query, max_results=5))
    except Exception as e:
        return f"[JS-rendered page — DuckDuckGo search failed: {e}]\n\nOriginal URL: {url}"

    if not results:
        return f"[JS-rendered page — no search results found for: {query}]\n\nOriginal URL: {url}"

    parts = [f"# Content compiled from: {url}\n\n*Fetched via search (JS-rendered page)*\n"]
    for r in results:
        result_url = r.get("href", "")
        snippet = r.get("body", "")
        parts.append(f"## {r.get('title', result_url)}\nSource: {result_url}\n\n{snippet}\n")
        # Try to fetch the full page for top results
        if result_url and result_url != url:
            try:
                full = _fetch_url(result_url)
                if len(full.strip()) > JS_DETECTION_THRESHOLD:
                    parts.append(full[:3000])
            except Exception:
                pass

    return "\n\n".join(parts)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_url(url: str) -> str:
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    return h.handle(resp.text)


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)
