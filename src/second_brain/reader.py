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
    import logging
    log = logging.getLogger(__name__)

    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url}")

    errors: list[str] = []

    # ── Attempt 1: yt-dlp (works on cloud IPs — fetches subtitle CDN URLs) ───
    try:
        text = _fetch_ytdlp_transcript(video_id, url)
        if text:
            content = f"# YouTube Transcript\n\nSource: {url}\n\n{text}"
            return content, f"youtube/{video_id}"
        else:
            errors.append("yt-dlp: returned empty transcript")
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        log.warning("yt-dlp transcript failed for %s: %s", video_id, e)

    # ── Attempt 2: YoutubeLoader / youtube_transcript_api (local/residential) ─
    try:
        from langchain_community.document_loaders import YoutubeLoader
        loader = YoutubeLoader.from_youtube_url(url, add_video_info=False, language=["en", "en-US"])
        docs = loader.load()
        text = " ".join(d.page_content for d in docs)
        if text.strip():
            content = f"# YouTube Transcript\n\nSource: {url}\n\n{text}"
            return content, f"youtube/{video_id}"
        else:
            errors.append("YoutubeLoader: returned empty transcript")
    except Exception as e:
        errors.append(f"YoutubeLoader: {e}")
        log.warning("YoutubeLoader transcript failed for %s: %s", video_id, e)

    # All transcript methods failed — raise with details so the job is marked failed
    # (gives the caller a chance to surface the real error rather than silently returning empty)
    error_summary = " | ".join(errors)
    raise RuntimeError(
        f"Could not fetch transcript for YouTube video {url}. "
        f"Errors: {error_summary}"
    )


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


# ── yt-dlp transcript helper ─────────────────────────────────────────────────

def _fetch_ytdlp_transcript(video_id: str, url: str) -> str | None:
    """Extract transcript/subtitles using yt-dlp.

    yt-dlp mimics a real browser client and works from cloud IPs where
    youtube_transcript_api gets blocked. Tries manual captions first,
    then auto-generated ones.
    """
    import io
    import yt_dlp

    transcript_lines: list[str] = []

    class _SubtitleLogger:
        def debug(self, msg: str) -> None: pass
        def warning(self, msg: str) -> None: pass
        def error(self, msg: str) -> None: pass

    def _subtitle_hook(d: dict) -> None:
        pass

    import os
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "")

    ydl_opts: dict = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
        "logger": _SubtitleLogger(),
        "progress_hooks": [_subtitle_hook],
        "outtmpl": "/tmp/yt_%(id)s.%(ext)s",
    }
    if cookies_file and Path(cookies_file).exists():
        ydl_opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            return None

        # Try to get subtitle data directly from info dict
        subs = info.get("subtitles") or {}
        auto_subs = info.get("automatic_captions") or {}

        for lang in ["en", "en-US", "en-GB"]:
            tracks = subs.get(lang) or auto_subs.get(lang, [])
            # prefer VTT, then json3, then anything else
            ordered = sorted(tracks, key=lambda t: (
                0 if t.get("ext") == "vtt" else
                1 if t.get("ext") == "json3" else 2
            ))
            for track in ordered:
                sub_url = track.get("url")
                ext = track.get("ext", "")
                if not sub_url:
                    continue
                try:
                    raw = httpx.get(sub_url, timeout=20).text
                    if ext == "json3":
                        lines = _parse_json3(raw)
                    else:
                        lines = _parse_vtt(raw)
                    if lines:
                        return " ".join(lines)
                except Exception:
                    continue

    return None


def _parse_json3(raw: str) -> list[str]:
    """Extract plain text from YouTube's json3 subtitle format."""
    import json as _json
    seen: set[str] = set()
    result: list[str] = []
    try:
        data = _json.loads(raw)
        for event in data.get("events", []):
            for seg in event.get("segs", []):
                text = seg.get("utf8", "").strip()
                if text and text not in ("\n", "") and text not in seen:
                    # skip music/sound cues
                    if text.startswith("[") and text.endswith("]"):
                        continue
                    seen.add(text)
                    result.append(text)
    except Exception:
        pass
    return result


def _parse_vtt(vtt: str) -> list[str]:
    """Extract plain text from a WebVTT subtitle string, deduplicating lines."""
    seen: set[str] = set()
    result: list[str] = []
    for line in vtt.splitlines():
        line = line.strip()
        # Skip metadata lines
        if (not line or line.startswith("WEBVTT") or line.startswith("NOTE")
                or "-->" in line or re.match(r"^\d+$", line)
                or line.startswith("Kind:") or line.startswith("Language:")):
            continue
        # Strip VTT inline tags like <00:00:00.000> or <c>
        line = re.sub(r"<[^>]+>", "", line).strip()
        # Decode HTML entities (&nbsp; etc.)
        line = line.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        line = re.sub(r"\s+", " ", line).strip()
        if line and line not in seen:
            seen.add(line)
            result.append(line)
    return result


# ── Supadata transcript helper ───────────────────────────────────────────────

def _fetch_supadata_transcript(video_id: str) -> str | None:
    """Fetch transcript via Supadata API — works from cloud IPs.

    Free tier: https://supadata.ai  — set SUPADATA_API_KEY env var.
    Without a key, still tries the unauthenticated endpoint (may be rate-limited).
    """
    import os
    api_key = os.getenv("SUPADATA_API_KEY", "")
    headers = {"x-api-key": api_key} if api_key else {}
    resp = httpx.get(
        "https://api.supadata.ai/v1/youtube/transcript",
        params={"videoId": video_id, "text": "true"},
        headers=headers,
        timeout=30,
        follow_redirects=True,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    # Response shape: {"content": "...", "lang": "en"} or {"transcript": [...]}
    if isinstance(data, dict):
        if "content" in data:
            return str(data["content"])
        if "transcript" in data:
            return " ".join(t.get("text", "") for t in data["transcript"])
    return None


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
