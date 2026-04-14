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

- Use plain, simple English. Avoid jargon unless the concept requires it — and when you use it, explain it in one sentence.
- Write as if explaining to a curious person who is smart but not yet an expert on this topic.
- Be direct and concrete. "This means X" beats "It can be argued that X may be the case."
- Show the insight, don't just describe it. A good page teaches something; a bad one just restates the source.

## What to write

**Summary (always — exactly one)**
Explain what the source is about, what it argues, and why it matters. Make it useful to someone who hasn't read the source.

**Concept pages (central ideas only)**
Write a concept page only for ideas that are central to the source's main argument — not every concept mentioned in passing.
- Short source (tweet, post, short article): 3–5 concepts
- Long source (article, video, paper): 6–8 concepts
- Check the index first: update an existing page rather than creating a duplicate
- A richer updated page beats two thin new ones

**Connection pages (explicit relationships only)**
Write a connection page only when the relationship between two concepts is the source's explicit point — not when they merely co-appear in the text.

**Insight pages (non-obvious findings only)**
The best insights are things the reader wouldn't have figured out without this source. Ask yourself: "Would this surprise someone who knows the basics?" If yes, write it. If it's obvious, skip it.
- One sharp, surprising insight beats three observations any reader could have guessed
- Explain *why* it's non-obvious, not just *that* it is

**Ideas (always)**
Call `update_ideas` with 2–3 concrete research questions this source opens up.

## How to write

- Use [[wikilinks]] throughout using exact page titles
- Every page must begin with YAML frontmatter: `title`, `type`, `summary` (max 150 chars)
- Flag contradictions inline: `> ⚠️ Contradiction: [old claim] vs [new claim (source)]`
- Prefer depth over breadth: fewer, richer pages compound better than many thin ones"""


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

        # Break if no tool calls present (end_turn or pure text response)
        if not choice.message.tool_calls:
            break

        tool_results: list[dict] = []
        for tc in choice.message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                # Truncated tool call — skip silently
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

    if pages_written:
        try:
            n = extract_triples(pages_written)
            if n:
                append_log(f"graph | extracted {n} new triples from {source_name}")
        except Exception:
            pass  # graph extraction failure never blocks ingest

    return pages_written
