import json
import re
import threading
from collections.abc import Generator

from ..config import MODEL, WIKI_DIR
from ..llm import get_client
from ..search import bm25_search
from ..wiki import read_index, append_log, write_page, update_index

SYSTEM = """You are the Query agent for a personal second-brain wiki.

Your job: synthesize an answer from the provided wiki pages for someone who has studied these topics and wants to recall or connect ideas.

## Rules

- Use only the provided wiki pages — do not add outside knowledge
- Cite with [[wikilinks]] using the exact page title, not just "the wiki says"
- Prefer synthesizing across multiple pages over summarizing one page; the user can read individual pages themselves
- When pages only partially cover the question, name what is covered and what's missing — do not pad with tangential material

## Output format

Choose the format that best serves the question:
- **Comparison table** — for "X vs Y" or "differences between" questions
- **Numbered steps** — for "how to" or process questions
- **Structured sections** — for complex multi-part synthesis
- **Plain prose** — for focused factual questions

If the wiki lacks enough information to answer well, say so directly and name which pages came closest.

When the wiki only partially covers the question or is missing key information, add a final section:

## To explore
- `<exact search query 1>`
- `<exact search query 2>`

Only include this section when genuinely needed — omit it when the wiki fully answers the question."""


def answer(question: str, file_back: bool = True) -> str:
    client = get_client()
    index = read_index()

    if not index.strip() or index.strip() == "# Wiki Index":
        return "The wiki is empty. Ingest some sources first."

    # Step 1: find relevant pages using BM25 search (no LLM call needed)
    page_paths = bm25_search(question, top_k=10)

    pages_content = []
    for rel in page_paths:
        p = WIKI_DIR / rel
        if p.exists():
            pages_content.append(f"### {rel}\n{p.read_text()}")

    if not pages_content:
        return "No relevant pages found in the wiki for this question."

    # Step 2: synthesize answer from those pages
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
                    f"Wiki pages:\n\n" + separator.join(pages_content)
                ),
            },
        ],
    )

    result = resp.choices[0].message.content
    append_log(f"query | {question[:80]}")

    # Step 3: decide whether to file the answer back into the wiki
    if file_back:
        _maybe_file(question, result, client)

    return result


def _build_context(question: str) -> tuple[list[str], str]:
    """Return (page_paths, joined_page_content) for a question, or empty if wiki is empty."""
    index = read_index()
    if not index.strip() or index.strip() == "# Wiki Index":
        return [], ""

    page_paths = bm25_search(question, top_k=10)
    separator = "---\n"
    pages_content = []
    for rel in page_paths:
        p = WIKI_DIR / rel
        if p.exists():
            pages_content.append(f"### {rel}\n{p.read_text()}")

    return page_paths, separator.join(pages_content)


def stream_answer(question: str, file_back: bool = True) -> Generator[str, None, None]:
    """
    Stream the answer token by token as SSE-formatted strings.
    Yields ``data: {"delta": "..."}\\n\\n`` lines, then ``data: [DONE]\\n\\n``.
    After streaming, optionally files the answer back into the wiki in a background thread.
    """
    client = get_client()
    _, pages_content = _build_context(question)

    if not pages_content:
        msg = (
            "The wiki is empty. Ingest some sources first."
            if not read_index().strip() or read_index().strip() == "# Wiki Index"
            else "No relevant pages found in the wiki for this question."
        )
        yield f"data: {json.dumps({'delta': msg})}\n\n"
        yield "data: [DONE]\n\n"
        return

    stream = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Question: {question}\n\nWiki pages:\n\n{pages_content}",
            },
        ],
    )

    collected: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            collected.append(delta)
            yield f"data: {json.dumps({'delta': delta})}\n\n"

    append_log(f"query | {question[:80]}")
    yield "data: [DONE]\n\n"

    if file_back and collected:
        full_answer = "".join(collected)
        t = threading.Thread(target=_maybe_file, args=(question, full_answer, client), daemon=True)
        t.start()


def _maybe_file(question: str, answer_text: str, client) -> None:
    """Ask the LLM if this answer is worth preserving, and if so write it to the wiki."""
    prompt = (
        f"Question: {question}\n\nAnswer:\n{answer_text}\n\n"
        "Decide whether this answer is worth preserving in a personal knowledge wiki.\n\n"
        "FILE IT if it synthesizes multiple concepts, surfaces a non-obvious connection, "
        "or would serve as a useful reference the user would want to query again.\n"
        "DO NOT FILE if it is a simple factual lookup, a definition, or just restates one source.\n\n"
        "If filing:\n"
        '  type = "insight" if the answer reveals a non-obvious cross-cutting finding\n'
        '  type = "qa" if it directly answers a specific question the user asked\n\n'
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
