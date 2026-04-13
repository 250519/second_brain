# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Vision

`second_brain` is a personal knowledge OS — ingest any resource, and Claude compiles it into a persistent, interlinked wiki you can query anytime. The human curates sources and asks questions; the LLM does all bookkeeping, cross-referencing, and synthesis.

This is **not RAG** — knowledge is compiled once and kept current, not re-derived on every query.

---

## V1 — What's Built

A CLI tool backed by plain filesystem markdown. No database, no graph layer, no mobile capture.

### Commands

```bash
uv run second-brain ingest <file_or_url>   # process a source into the wiki
uv run second-brain query "<question>"     # ask a question against the wiki
uv run second-brain lint                   # health check the wiki
uv run second-brain status                 # show wiki statistics
```

`<file_or_url>` accepts: local `.txt`, `.md`, `.pdf`, or any `https://` URL.

### Package Management

Use **uv** (not pip).

```bash
uv sync                   # install all dependencies + create .venv
uv add <package>          # add runtime dependency
uv add --dev <package>    # add dev dependency
uv run <command>          # run inside managed environment
```

### Development

```bash
uv run pytest             # tests
uv run ruff check .       # lint
uv run ruff format .      # format
uv run mypy .             # type check
```

---

## Directory Structure

```
data/
├── raw/          ← drop your sources here (immutable, LLM never writes here)
├── wiki/
│   ├── index.md  ← catalog of all pages (updated on every ingest)
│   ├── log.md    ← append-only history of all operations
│   ├── summary/  ← one page per source
│   ├── concept/  ← one page per idea/entity (never duplicate)
│   ├── connection/ ← one page per relationship pair
│   ├── insight/  ← cross-cutting findings
│   ├── qa/       ← filed query answers
│   └── lint/     ← health check reports
└── output/
    └── ideas.md  ← research questions and ideas (updated on every ingest)

src/second_brain/
├── cli.py          ← Click entry point (ingest, query, lint, status)
├── config.py       ← paths and constants (MODEL, DATA_DIR, etc.)
├── reader.py       ← source reading: local files (.txt, .md, .pdf) + URLs
├── wiki.py         ← filesystem operations (write_page, update_index, append_log)
└── agents/
    ├── compiler.py ← ingest agent: tool-calling loop that writes wiki pages
    ├── query.py    ← query agent: two-pass (find pages → synthesize answer)
    └── review.py   ← lint agent: health check, saves report to wiki/lint/
```

---

## How It Works

### Ingest flow
1. `reader.py` reads the source (file or URL → plain text)
2. Compiler agent gets the source + current `wiki/index.md` as context
3. Agent calls `write_wiki_page` tool repeatedly to write summary, concept, connection, insight pages
4. Agent calls `update_ideas` to append to `output/ideas.md`
5. Each tool call immediately writes the file and updates `index.md`
6. `log.md` gets an append entry

> **Continuous update rule**: every ingest updates both `wiki/` and `output/ideas.md`. The ideas file always reflects the latest state of knowledge.

### Query flow
1. Read `wiki/index.md`
2. First Claude call: identify relevant page paths from the index
3. Read those pages
4. Second Claude call: synthesize answer with `[[wikilink]]` citations

### Lint flow
Claude reads all wiki pages (up to 30) + index, returns a structured report covering: contradictions, stale claims, orphan concepts, missing cross-references, and suggested gaps to explore.

---

## Wiki Conventions (for agents)

- All pages use `[[wikilinks]]` for cross-references
- Every page has YAML frontmatter: `title`, `type`, `summary` (max 150 chars)
- Contradictions: `> ⚠️ Contradiction: [old claim] vs [new claim (source)]`
- `concept/` pages: update existing — never create a duplicate
- `log.md`: append-only — never edit past entries

---

## Environment

Requires `ANTHROPIC_API_KEY` environment variable.

---

## V2+ Roadmap (not yet built)

- Knowledge graph layer (InfraNodus / networkx) for structural gap detection
- `infranodus/` ontology files — living memory updated on every ingest
- GitHub repo ingestion (README + file tree + key function summaries)
- YouTube ingestion (transcript → wiki)
- Voice note ingestion
- Image/OCR ingestion
- Telegram bot for mobile capture
- Spaced repetition — surface wiki pages due for review
- Query answers auto-filed back into wiki
