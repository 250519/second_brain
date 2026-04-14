from datetime import datetime, timezone

from ..config import MODEL, WIKI_DIR
from ..llm import get_client
from ..wiki import append_log, ensure_dirs, read_all_pages, read_index

SYSTEM = """You are the Review agent for a personal second-brain wiki.

Your job: produce a structured health check report that helps the owner prioritize what to fix and what to read next.

Use this exact structure:

### 🔴 High Priority
**Contradictions** — claims that directly conflict across pages. Name both pages and quote the conflicting claims.
**Broken cross-references** — [[wikilinks]] that reference a concept with no corresponding page.

### 🟡 Medium Priority
**Orphan concepts** — important ideas mentioned across multiple pages but lacking their own concept page.
**Missing wikilinks** — places where a concept page exists but isn't linked from a page that discusses it. Only flag cases where the target page actually exists.

### 🟢 Gaps to Explore
For each gap:
**Gap**: [what's missing and why it matters to the wiki's existing threads]
**Search**: `[exact search query to paste into Google or DuckDuckGo]`

## Rules

- Name specific pages and exact issues — do not describe problems in the abstract
- For contradictions: quote the conflicting claims directly, do not paraphrase
- Limit to the 3 most important items per section — triage ruthlessly, do not list every minor issue"""


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
