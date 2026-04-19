# Reader Reference — reader.py

Handles all source types: local files, article URLs, YouTube transcripts, JS-rendered docs, and social media posts (LinkedIn, X/Twitter, Reddit, Instagram, etc.).

## Routing logic

```
read_source(input)
  ├── YouTube URL          → _read_youtube()        transcript via Supadata SDK (SUPADATA_API_KEY)
  ├── Social media URL     → _read_social_post()    Jina.ai reader → DuckDuckGo fallback
  ├── Other https:// URL   → _fetch_url()
  │     └── < 300 chars?  → _read_js_doc()          DuckDuckGo site: search fallback
  └── Local file           → direct read / pypdf
```

> **Why Supadata instead of youtube-transcript-api?**
> Cloud provider IPs (AWS, GCP, Azure) are blocked by YouTube. `youtube-transcript-api` and `yt-dlp` both fail from cloud deployments even with cookies. Supadata is a third-party API that handles YouTube transcript fetching server-side — works reliably from any IP. Free tier available at https://supadata.ai

## Complete reader.py

```python
import re
import time
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

    # Local file
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {source}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path), path.name
    if suffix in (".txt", ".md"):
        return path.read_text(), path.name

    raise ValueError(f"Unsupported file type: {suffix}. Supported: .txt, .md, .pdf, URLs")


# ── Social media ──────────────────────────────────────────────────────────────

def _is_social_media(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(d in domain for d in _SOCIAL_DOMAINS)


def _read_social_post(url: str) -> str:
    """Fetch social media post content via Jina.ai's free reader API.

    Jina.ai (r.jina.ai) renders JS, handles login-walled pages, and returns
    clean markdown — no API key required for basic usage.

    Falls back to DuckDuckGo search if Jina returns too little content
    (e.g. posts requiring authentication).

    Tested working: LinkedIn posts, X/Twitter threads, Reddit threads.
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


# ── YouTube ───────────────────────────────────────────────────────────────────

def _is_youtube(url: str) -> bool:
    return "youtube.com/watch" in url or "youtu.be/" in url


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
    Works from cloud IPs (AWS/GCP/Azure) where youtube-transcript-api is blocked.
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


# ── URL fetching ──────────────────────────────────────────────────────────────

def _fetch_url(url: str) -> str:
    """Fetch URL and convert HTML to clean markdown text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        h.body_width = 0
        return h.handle(resp.text)
    except Exception as e:
        raise ValueError(f"Failed to fetch {url}: {e}")


def _read_js_doc(url: str) -> str:
    """Fallback for JS-rendered pages: DuckDuckGo site: search + fetch real sub-pages."""
    from duckduckgo_search import DDGS

    parsed = urlparse(url)
    domain = parsed.netloc
    path_keywords = " ".join(
        p for p in parsed.path.strip("/").replace("-", " ").split("/") if p
    )
    query = f"site:{domain} {path_keywords}".strip()
    if not path_keywords:
        query = f"site:{domain} overview introduction"

    try:
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
        if result_url and result_url != url:
            try:
                full = _fetch_url(result_url)
                if len(full.strip()) > JS_DETECTION_THRESHOLD:
                    parts.append(full[:3000])
            except Exception:
                pass

    return "\n\n".join(parts)


# ── PDF ───────────────────────────────────────────────────────────────────────

def _read_pdf(path: Path) -> str:
    """Extract text from PDF using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except Exception as e:
        raise ValueError(f"Could not read PDF {path}: {e}")
```

## Usage examples

```bash
# Social media posts — all go through Jina.ai automatically
second-brain ingest "https://www.linkedin.com/posts/..."
second-brain ingest "https://x.com/user/status/..."
second-brain ingest "https://reddit.com/r/MachineLearning/comments/..."
second-brain ingest "https://threads.net/@user/post/..."

# YouTube (transcript via Supadata — requires SUPADATA_API_KEY)
second-brain ingest "https://youtu.be/abc123"

# Articles / docs
second-brain ingest "https://blog.langchain.com/..."

# Local files
second-brain ingest data/raw/paper.pdf
second-brain ingest data/raw/notes.md
```

## Required env vars

| Var | Purpose |
|---|---|
| `SUPADATA_API_KEY` | YouTube transcript fetching — sign up free at https://supadata.ai |

## How Jina.ai works

`https://r.jina.ai/{url}` — Jina spins up a headless browser, renders the page, and returns clean markdown. Free, no API key needed for personal use. Returns 10k–30k chars for most public social media posts.

**Limitation:** Private posts or posts requiring login return limited content even through Jina. In that case the DuckDuckGo fallback tries to find cached/shared versions of the content.

## Why NOT youtube-transcript-api or yt-dlp

Both are blocked by YouTube on cloud IPs (AWS/GCP/Azure). Even valid browser cookies don't help — YouTube now requires a BotGuard "Proof of Origin Token" that can only be generated by a real browser running JavaScript. Supadata handles this server-side.
