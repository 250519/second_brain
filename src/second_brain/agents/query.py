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
