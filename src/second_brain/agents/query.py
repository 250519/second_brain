import json
import re

from ..config import MODEL, WIKI_DIR
from ..llm import get_client
from ..wiki import read_index, append_log

SYSTEM = """You are the Query agent for a personal second-brain wiki.
Answer questions using only the provided wiki pages.
Cite sources with [[wikilinks]]. Be specific and direct.
If the wiki lacks enough information, say so clearly rather than guessing."""


def answer(question: str) -> str:
    client = get_client()
    index = read_index()

    if not index.strip() or index.strip() == "# Wiki Index":
        return "The wiki is empty. Ingest some sources first."

    # Step 1: find relevant pages from the index
    plan = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    f'Given this wiki index, return a JSON array of page paths '
                    f'most relevant to answering:\n"{question}"\n\n'
                    f"Index:\n{index}\n\n"
                    f'Reply with ONLY a JSON array like: ["summary/foo.md", "concept/bar.md"] — max 10 paths.'
                ),
            }
        ],
    )

    raw = plan.choices[0].message.content.strip()
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    page_paths: list[str] = json.loads(match.group()) if match else []

    pages_content = []
    for rel in page_paths:
        # strip leading "wiki/" if the model copied the index path format
        if rel.startswith("wiki/"):
            rel = rel[5:]
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
    return result
