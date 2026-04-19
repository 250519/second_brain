# Agents Reference

## Table of Contents
1. [compiler.py](#compilerpy) — ingest agent (tool-calling loop)
2. [query.py](#querypy) — question answering + self-filing
3. [review.py](#reviewpy) — wiki health check / lint

---

## compiler.py

```python
import json

from ..config import MODEL, MAX_SOURCE_CHARS
from ..graph import extract_triples
from ..llm import get_client
from ..wiki import ensure_dirs, write_page, update_index, append_log, append_ideas

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_wiki_page",
            "description": (
                "Write or update a wiki page. Call this for each summary, concept, "
                "connection, or insight extracted from the source. "
                "Use [[wikilinks]] inside content to cross-reference other pages."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_type": {
                        "type": "string",
                        "enum": ["summary", "concept", "connection", "insight"],
                    },
                    "title": {"type": "string"},
                    "content": {
                        "type": "string",
                        "description": (
                            "Full markdown content including YAML frontmatter. "
                            "Frontmatter must include: title, type, summary (max 150 chars)."
                        ),
                    },
                    "summary": {
                        "type": "string",
                        "description": "One-line summary, max 150 chars, used in the wiki index.",
                    },
                },
                "required": ["page_type", "title", "content", "summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_ideas",
            "description": "Add ideas or research questions sparked by this source to ideas.md.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ideas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of concrete ideas or questions to record.",
                    }
                },
                "required": ["ideas"],
            },
        },
    },
]

SYSTEM = """You are the Compiler agent for a personal second-brain wiki.

Your job: extract the knowledge that matters from a new source and write it into the wiki in clear, humanised language — like a smart friend explaining ideas, not a textbook.

## Writing style

- Use plain, simple English. Avoid jargon unless the concept requires it.
- Be direct and concrete. "This means X" beats "It can be argued that X may be the case."
- Show the insight, don't just describe it. A good page teaches something.

## What to write

**Summary (always — exactly one)**
Explain what the source is about, what it argues, and why it matters.

**Concept pages (central ideas only)**
- Short source: 3–5 concepts. Long source: 6–8 concepts.
- Check the index first: update existing pages, never create a duplicate.

**Connection pages** — only when the relationship is the source's explicit point, not mere co-appearance.

**Insight pages** — non-obvious findings only. Ask: "Would this surprise someone who knows the basics?"

**Ideas (always)**
Call `update_ideas` with 2–3 concrete research questions this source opens up.

## How to write

- Use [[wikilinks]] throughout using exact page titles
- Every page must begin with YAML frontmatter: `title`, `type`, `summary` (max 150 chars)
- Flag contradictions inline: `> ⚠️ Contradiction: [old claim] vs [new claim (source)]`
- Prefer depth over breadth: fewer, richer pages compound better than many thin ones

## Technical accuracy — commands, code, package names (CRITICAL)

YouTube and video transcripts are **speech-to-text only** — they capture spoken words but miss everything shown on screen (terminals, editors, browsers). This creates a trap: the speaker says "run the install command" but the exact command was only on screen, not spoken.

**Rules:**
- Only write a terminal command, package name, API call, or code snippet if it appears **verbatim** in the source text.
- Do NOT infer, autocomplete, or reconstruct commands from context. If the transcript says "install the lmcp package" but gives no exact command, write: *"install lmcp (exact command not captured in transcript)"* — never a guessed command.
- Do NOT assume package managers. A speaker saying "install it" does not tell you whether they used `pip`, `uv`, `npm`, `brew`, or anything else.
- **Never put an uncertain command in a code block.** If you are not 100% sure the command is verbatim from the source, use plain prose instead. A code block implies the reader can copy-paste it — do not create that false confidence.
- When uncertain about any technical detail (version numbers, flag names, API endpoints, config keys), omit it rather than guess. A gap in the wiki is far less harmful than wrong information."""


def ingest(source_content: str, source_name: str, current_index: str) -> list[str]:
    ensure_dirs()
    client = get_client()

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Process this source and write it into the wiki.\n\n"
                f"**Source:** {source_name}\n\n"
                f"**Current wiki index:**\n{current_index or '(empty)'}\n\n"
                f"**Source content:**\n{source_content[:MAX_SOURCE_CHARS]}"
            ),
        },
    ]

    pages_written: list[str] = []

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=16000,
            tools=TOOLS,
            messages=messages,
        )

        choice = response.choices[0]
        messages.append(choice.message)  # append assistant turn (preserves tool_calls)

        # KEY: use tool_calls presence, not finish_reason
        # finish_reason=="length" also stops tool calls — checking it breaks the loop early
        if not choice.message.tool_calls:
            break

        tool_results: list[dict] = []
        for tc in choice.message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_results.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": "error: truncated arguments"}
                )
                continue

            if tc.function.name == "write_wiki_page":
                required = {"page_type", "title", "content", "summary"}
                missing = required - args.keys()
                if missing:
                    tool_results.append(
                        {"role": "tool", "tool_call_id": tc.id, "content": f"error: missing fields {missing}"}
                    )
                    continue
                path = write_page(args["page_type"], args["title"], args["content"])
                update_index(args["title"], args["page_type"], args["summary"], path)
                pages_written.append(f"{args['page_type']}/{args['title']}")
                result = f"Written: {path.name}"

            elif tc.function.name == "update_ideas":
                append_ideas(args.get("ideas", []))
                result = f"Added {len(args.get('ideas', []))} ideas"

            else:
                result = "unknown tool"

            tool_results.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )

        messages.extend(tool_results)

    append_log(f"ingest | {source_name} | {len(pages_written)} pages written")

    # Extract knowledge graph triples from newly written pages
    if pages_written:
        try:
            n = extract_triples(pages_written)
            if n:
                append_log(f"graph | extracted {n} new triples from {source_name}")
        except Exception:
            pass  # graph extraction failure never blocks ingest

    return pages_written
```

---

## query.py

```python
import json
import re

from ..config import MODEL, WIKI_DIR
from ..llm import get_client
from ..search import bm25_search
from ..wiki import read_index, append_log, write_page, update_index

SYSTEM = """You are the Query agent for a personal second-brain wiki.
Answer questions using only the provided wiki pages.
Cite sources with [[wikilinks]]. Be specific and direct.

Choose the output format that best serves the question:
- Comparison table for "compare X vs Y" or "differences" questions
- Numbered steps for "how to" or process questions
- Structured markdown sections for complex multi-part synthesis
- Plain prose for straightforward factual questions

If the wiki lacks enough information, say so clearly rather than guessing."""


def answer(question: str, file_back: bool = True) -> str:
    client = get_client()
    index = read_index()

    if not index.strip() or index.strip() == "# Wiki Index":
        return "The wiki is empty. Ingest some sources first."

    # Step 1: BM25 retrieval — no LLM call needed here
    page_paths = bm25_search(question, top_k=10)

    pages_content = []
    for rel in page_paths:
        p = WIKI_DIR / rel
        if p.exists():
            pages_content.append(f"### {rel}\n{p.read_text()}")

    if not pages_content:
        return "No relevant pages found in the wiki for this question."

    # Step 2: synthesize answer
    separator = "---\n"
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    "Wiki pages:\n\n" + separator.join(pages_content)
                ),
            },
        ],
    )

    result = resp.choices[0].message.content
    append_log(f"query | {question[:80]}")

    # Step 3: optionally file the answer back into the wiki
    if file_back:
        _maybe_file(question, result, client)

    return result


def _maybe_file(question: str, answer_text: str, client) -> None:
    """Ask the LLM if this answer is worth preserving, and if so write it to the wiki."""
    prompt = (
        f"Question: {question}\n\nAnswer:\n{answer_text}\n\n"
        "Is this answer a non-trivial synthesis worth preserving in a personal knowledge wiki?\n"
        "File it if: it connects multiple concepts, contains a non-obvious insight, "
        "or would make a genuinely useful reference for later.\n"
        "Do NOT file it if: it is a simple factual lookup or just restates one source.\n\n"
        "Return ONLY raw JSON, no markdown fences:\n"
        '{"file": true, "type": "qa" or "insight", "title": "<concise title>", "summary": "<max 150 chars>"}\n'
        "or:\n"
        '{"file": false}'
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
        decision = json.loads(raw)
    except Exception:
        return

    if not decision.get("file"):
        return

    page_type = decision.get("type", "qa")
    if page_type not in ("qa", "insight"):
        page_type = "qa"
    title = str(decision.get("title", "")).strip()
    summary = str(decision.get("summary", "")).strip()[:150]

    if not title:
        return

    content = (
        f"---\ntitle: {title}\ntype: {page_type}\nsummary: {summary}\n---\n\n"
        f"## Question\n\n{question}\n\n"
        f"## Answer\n\n{answer_text}\n"
    )
    try:
        path = write_page(page_type, title, content)
        update_index(title, page_type, summary, path)
        append_log(f"filed | {page_type}/{title}")
    except Exception:
        return
```

---

## review.py

```python
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
```
