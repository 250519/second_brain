# Core Modules Reference

## Table of Contents
1. [config.py](#configpy)
2. [llm.py](#llmpy)
3. [wiki.py](#wikipy)
4. [search.py](#searchpy)

---

## config.py

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WIKI_DIR = DATA_DIR / "wiki"
OUTPUT_DIR = DATA_DIR / "output"

INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
IDEAS_FILE = OUTPUT_DIR / "ideas.md"
ISSUES_FILE = ROOT / "ISSUES.md"

INFRANODUS_DIR = DATA_DIR / "infranodus"
ONTOLOGY_FILE = INFRANODUS_DIR / "wiki-ontology.md"
TODOS_DIR = DATA_DIR / "todos"
GAPS_FILE = TODOS_DIR / "gaps.md"

# OpenAI-compatible LLM gateway
API_KEY: str = os.environ["TFY_API_KEY"]
BASE_URL: str = os.environ["TFY_BASE_URL"]
MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4o")

MAX_SOURCE_CHARS = 20_000
```

---

## llm.py

```python
from openai import OpenAI
from .config import API_KEY, BASE_URL

def get_client() -> OpenAI:
    """Return an OpenAI-compatible client pointed at your LLM gateway."""
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)
```

---

## wiki.py

```python
from datetime import datetime, timezone
from pathlib import Path
import re

from .config import (
    WIKI_DIR, INDEX_FILE, LOG_FILE, IDEAS_FILE,
    OUTPUT_DIR, INFRANODUS_DIR, TODOS_DIR,
)

# Maps page_type → index section header
_SECTION_HEADERS: dict[str, str] = {
    "summary":    "## Summaries",
    "concept":    "## Concepts",
    "connection": "## Connections",
    "insight":    "## Insights",
    "qa":         "## Q&A",
    "lint":       "## Lint",
}


def ensure_dirs() -> None:
    for d in [
        WIKI_DIR / "summary",
        WIKI_DIR / "concept",
        WIKI_DIR / "connection",
        WIKI_DIR / "insight",
        WIKI_DIR / "qa",
        WIKI_DIR / "lint",
        OUTPUT_DIR,
        INFRANODUS_DIR,
        TODOS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("# Wiki Index\n\n")
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# Log\n\n")
    if not IDEAS_FILE.exists():
        IDEAS_FILE.write_text("# Ideas\n\n")


def read_index() -> str:
    return INDEX_FILE.read_text() if INDEX_FILE.exists() else ""


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


def write_page(page_type: str, title: str, content: str) -> Path:
    path = WIKI_DIR / page_type / f"{_slug(title)}.md"
    path.write_text(content)
    return path


def update_index(title: str, page_type: str, summary: str, path: Path) -> None:
    index_text = INDEX_FILE.read_text()
    rel = str(path.relative_to(WIKI_DIR))   # e.g. "summary/foo.md"
    entry = f"- [[{rel}|{title}]] `{page_type}` — {summary}"

    section_header = _SECTION_HEADERS.get(page_type, f"## {page_type.title()}")

    # Remove stale entry for this title
    lines = [l for l in index_text.splitlines() if f"|{title}]]" not in l]

    # Locate the section
    try:
        sec_idx = lines.index(section_header)
    except ValueError:
        sec_idx = None

    if sec_idx is not None:
        # Find start of next section
        next_sec = len(lines)
        for i in range(sec_idx + 1, len(lines)):
            if lines[i].startswith("## "):
                next_sec = i
                break
        # Insert after last non-blank line in this section
        insert_at = next_sec
        for i in range(next_sec - 1, sec_idx, -1):
            if lines[i].strip():
                insert_at = i + 1
                break
        lines.insert(insert_at, entry)
    else:
        # Section doesn't exist yet — append at end
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(section_header)
        lines.append(entry)

    INDEX_FILE.write_text("\n".join(lines) + "\n")


def append_log(entry: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with LOG_FILE.open("a") as f:
        f.write(f"\n## [{ts}] {entry}\n")


def append_ideas(ideas: list[str]) -> None:
    with IDEAS_FILE.open("a") as f:
        for idea in ideas:
            f.write(f"- {idea}\n")


def read_all_pages() -> dict[str, str]:
    """Return {relative_path: content} for all non-empty, non-root wiki pages."""
    pages = {}
    skip = {INDEX_FILE.name, LOG_FILE.name, "overview.md"}
    for p in WIKI_DIR.rglob("*.md"):
        # Skip root-level files (index, log) and Obsidian placeholders (empty files)
        if p.parent == WIKI_DIR or p.name in skip or p.stat().st_size == 0:
            continue
        pages[str(p.relative_to(WIKI_DIR))] = p.read_text()
    return pages
```

---

## search.py

BM25 full-text search over wiki pages. Replaces the LLM index-scan in the query agent — faster, no extra LLM call, scales to hundreds of pages.

```python
"""BM25 full-text search over wiki pages."""

from rank_bm25 import BM25Okapi
from .wiki import read_all_pages


def bm25_search(question: str, top_k: int = 10) -> list[str]:
    """Return top_k page paths most relevant to the question.

    Indexes full page content plus the path slug so title tokens
    also contribute to ranking.
    """
    pages = read_all_pages()
    if not pages:
        return []

    paths = list(pages.keys())
    corpus = [
        path.replace("/", " ").replace("-", " ") + " " + content
        for path, content in pages.items()
    ]

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    tokenized_query = question.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    ranked = sorted(zip(paths, scores), key=lambda x: x[1], reverse=True)
    return [path for path, _ in ranked[:top_k]]
```
