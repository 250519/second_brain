from datetime import datetime, timezone

from ..config import MODEL, WIKI_DIR
from ..llm import get_client
from ..wiki import append_log, ensure_dirs, read_all_pages, read_index

SYSTEM = """You are the Review agent for a personal second-brain wiki.
Perform a health check and produce a clear lint report covering:
1. Contradictions between pages
2. Stale or unsupported claims
3. Important concepts mentioned but lacking their own page
4. Missing [[wikilinks]] that should exist
5. Knowledge gaps — topics worth exploring next

For each knowledge gap, include:
**Gap**: [description of what's missing]
**Search**: `[exact search query to paste into DuckDuckGo or Google]`

Be specific: name the pages and the exact issues."""


def lint() -> str:
    ensure_dirs()
    client = get_client()
    pages = read_all_pages()

    if not pages:
        return "Wiki is empty — nothing to lint."

    pages_text = "\n\n---\n\n".join(
        f"**{path}**\n{content}" for path, content in list(pages.items())[:30]
    )

    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Wiki index:\n{read_index()}\n\nWiki pages:\n{pages_text}",
            },
        ],
    )

    report = resp.choices[0].message.content

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    lint_path = WIKI_DIR / "lint" / f"lint-{ts}.md"
    lint_path.write_text(
        f"---\ntitle: Lint {ts}\ntype: lint\nsummary: Wiki health check {ts}\n---\n\n{report}"
    )

    append_log(f"lint | health check | saved to lint/lint-{ts}.md")
    return report
