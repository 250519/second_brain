import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
import html2text

JS_DETECTION_THRESHOLD = 300  # chars — below this we assume JS-rendered


def read_source(source: str) -> tuple[str, str]:
    """Return (content, source_name) for a local file path or URL."""
    if _is_youtube(source):
        return _read_youtube(source)

    if source.startswith("http://") or source.startswith("https://"):
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
    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url}")

    try:
        import time
        from youtube_transcript_api import YouTubeTranscriptApi
        api = _youtube_api()
        transcript = api.fetch(video_id)
        text = " ".join(entry.text for entry in transcript)
        content = f"# YouTube Transcript\n\nSource: {url}\n\n{text}"
        time.sleep(2)  # be polite — avoid rate-limiting on sequential fetches
        return content, f"youtube/{video_id}"

    except Exception as e:
        # Fall back to page metadata
        try:
            page = _fetch_url(f"https://www.youtube.com/watch?v={video_id}")
            # Extract title from metadata
            title_match = re.search(r'"title":"([^"]+)"', page)
            title = title_match.group(1) if title_match else video_id
            content = (
                f"# YouTube Video: {title}\n\n"
                f"Source: {url}\n\n"
                f"**Note:** Transcript unavailable ({e}). "
                f"Only page metadata was extracted.\n\n"
                f"{page[:2000]}"
            )
            return content, f"youtube/{video_id}"
        except Exception:
            raise RuntimeError(f"Could not fetch YouTube video {url}: {e}")


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


# ── YouTube API factory ───────────────────────────────────────────────────────

def _youtube_api():
    """Return a YouTubeTranscriptApi instance, using browser cookies if available.

    Set YOUTUBE_COOKIES_FILE in .env to the path of a Netscape-format cookies.txt
    exported from your browser (use the 'Get cookies.txt LOCALLY' Chrome extension).
    This bypasses YouTube IP-based rate limiting.
    """
    import os
    from youtube_transcript_api import YouTubeTranscriptApi

    cookies_path = os.getenv("YOUTUBE_COOKIES_FILE", "")
    if cookies_path and Path(cookies_path).exists():
        import requests
        from http.cookiejar import MozillaCookieJar
        session = requests.Session()
        cj = MozillaCookieJar()
        cj.load(cookies_path, ignore_discard=True, ignore_expires=True)
        session.cookies = cj  # type: ignore[assignment]
        return YouTubeTranscriptApi(http_client=session)

    return YouTubeTranscriptApi()


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
