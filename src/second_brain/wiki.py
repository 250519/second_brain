from datetime import datetime, timezone
from pathlib import Path
import re

from .config import WIKI_DIR, INDEX_FILE, LOG_FILE, IDEAS_FILE, OUTPUT_DIR


def ensure_dirs() -> None:
    for d in [
        WIKI_DIR / "summary",
        WIKI_DIR / "concept",
        WIKI_DIR / "connection",
        WIKI_DIR / "insight",
        WIKI_DIR / "qa",
        WIKI_DIR / "lint",
        OUTPUT_DIR,
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
    index = INDEX_FILE.read_text()
    rel = str(path.relative_to(WIKI_DIR))  # e.g. "summary/foo.md" — relative to vault root
    entry = f"- [[{rel}|{title}]] `{page_type}` — {summary}\n"

    # Remove stale entry for this title
    lines = [l for l in index.splitlines(keepends=True) if f"|{title}]]" not in l]
    INDEX_FILE.write_text("".join(lines) + entry)


def append_log(entry: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with LOG_FILE.open("a") as f:
        f.write(f"\n## [{ts}] {entry}\n")


def append_ideas(ideas: list[str]) -> None:
    with IDEAS_FILE.open("a") as f:
        for idea in ideas:
            f.write(f"- {idea}\n")


def read_all_pages() -> dict[str, str]:
    pages = {}
    skip = {INDEX_FILE.name, LOG_FILE.name, "overview.md"}
    for p in WIKI_DIR.rglob("*.md"):
        # skip root-level files (index, log, Obsidian placeholders) and empty files
        if p.parent == WIKI_DIR or p.name in skip or p.stat().st_size == 0:
            continue
        pages[str(p.relative_to(WIKI_DIR))] = p.read_text()
    return pages
