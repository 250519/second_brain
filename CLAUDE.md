# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Vision

`second_brain` is a personal knowledge OS — ingest any resource, and Claude compiles it into a persistent, interlinked wiki you can query anytime. The human curates sources and asks questions; the LLM does all bookkeeping, cross-referencing, and synthesis.

This is **not RAG** — knowledge is compiled once and kept current, not re-derived on every query.

---

## What's Built

A full-stack application: FastAPI backend + React frontend + CLI, all backed by plain filesystem markdown.

### CLI Commands

```bash
uv run second-brain ingest <file_or_url>    # process a source into the wiki
uv run second-brain ingest-list <file.md>   # ingest all URLs found in a file
uv run second-brain query "<question>"      # ask a question against the wiki
uv run second-brain lint                    # health check the wiki
uv run second-brain status                  # show wiki statistics
uv run second-brain graph                   # analyze knowledge graph + gap questions
uv run second-brain graph --view            # analysis + open browser visualization
uv run second-brain serve                   # start FastAPI server (port 8000)
uv run second-brain serve --reload          # dev mode with auto-reload
```

`<file_or_url>` accepts: local `.txt`, `.md`, `.pdf`, YouTube URLs, social media URLs, or any `https://` URL.

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
├── raw/              ← drop your sources here (LLM never writes here)
├── wiki/
│   ├── index.md      ← catalog of all pages (updated on every ingest)
│   ├── log.md        ← append-only history of all operations
│   ├── summary/      ← one page per ingested source
│   ├── concept/      ← one page per idea/entity (never duplicate)
│   ├── connection/   ← one page per relationship pair
│   ├── insight/      ← non-obvious cross-cutting findings
│   ├── qa/           ← filed query answers
│   └── lint/         ← health check reports
├── output/
│   ├── ideas.md      ← research questions (updated on every ingest)
│   └── graph.html    ← interactive knowledge graph visualization
├── infranodus/
│   └── wiki-ontology.md  ← append-only triple store: [[A]] --rel--> [[B]]
└── todos/
    └── gaps.md       ← LLM-generated research questions from graph analysis

src/second_brain/
├── cli.py            ← Click entry point
├── config.py         ← paths and constants (MODEL, DATA_DIR, etc.)
├── reader.py         ← source reading: local files + URLs + YouTube + social
├── wiki.py           ← filesystem ops (write_page, update_index, append_log)
├── search.py         ← BM25 full-text search over wiki pages
├── graph.py          ← knowledge graph: extract_triples, analyze, visualize
├── llm.py            ← OpenAI-compatible client factory
└── agents/
    ├── compiler.py   ← ingest agent: tool-calling loop that writes wiki pages
    ├── query.py      ← query agent: BM25 retrieval → LLM synthesis → auto-file
    └── review.py     ← lint agent: health check, saves report to wiki/lint/

src/second_brain/api/
├── main.py           ← FastAPI app factory
├── models.py         ← Pydantic request/response models
├── jobs.py           ← in-memory job store for async ingest tracking
└── routers/
    ├── ingest.py     ← POST /api/v1/ingest/{url,text,file,batch}
    ├── query.py      ← POST /api/v1/query
    ├── wiki.py       ← GET  /api/v1/wiki/{status,pages,...}
    ├── graph.py      ← GET  /api/v1/graph/{view,data,analyze}
    └── search.py     ← GET  /api/v1/search

frontend/
├── src/
│   ├── pages/        ← Dashboard, Ingest, Query, Wiki, Graph, Ideas
│   ├── components/   ← Shell, TopBar, Sidebar, GraphFrame, ...
│   └── api/          ← typed API client (BASE_URL from VITE_API_URL)
└── Dockerfile        ← multi-stage build (node → nginx)

deploy/
├── deploy_backend.py  ← TrueFoundry: creates EFS volume + deploys service
└── deploy_frontend.py ← TrueFoundry: deploys frontend service
```

---

## How It Works

### Ingest flow
1. `reader.py` reads the source → plain text
   - YouTube → Supadata SDK (works from cloud IPs)
   - Social media → Jina.ai reader → DuckDuckGo fallback
   - JS-rendered docs → DuckDuckGo `site:` search → fetch sub-pages
   - Local `.pdf` → pypdf
2. Compiler agent gets source text + current `wiki/index.md`
3. Agent calls `write_wiki_page` tool repeatedly: summary, concept, connection, insight pages
4. Agent calls `update_ideas` → appends to `output/ideas.md`
5. Each tool call writes the file and updates `index.md` immediately
6. After ingest: `extract_triples()` builds knowledge graph from new pages
7. `log.md` gets an append entry

### Query flow
1. BM25 search over all wiki page content → top 10 relevant pages
2. LLM synthesizes answer with `[[wikilink]]` citations
3. `_maybe_file()` — LLM decides if worth preserving → writes `qa/` or `insight/` page

### Graph flow
1. `extract_triples()` — LLM reads new pages, outputs `[[A]] --rel--> [[B]]` triples → appended to `wiki-ontology.md`
2. `analyze()` — loads triples into networkx DiGraph, computes centrality/bridges/gaps → LLM writes research questions to `gaps.md`
3. `visualize()` — pyvis HTML with nodes coloured by centrality (red=hub, blue=peripheral)

### API flow
- All ingest endpoints return **202 Accepted immediately** — ingest is slow (30–60s), never block
- Job tracking: `POST /api/v1/ingest/url` → `job_id` → poll `GET /api/v1/ingest/jobs/{id}`

---

## API Endpoints

```
POST /api/v1/ingest/url           → 202 + job_id
POST /api/v1/ingest/text          → 202 + job_id
POST /api/v1/ingest/file          → 202 + job_id (multipart)
POST /api/v1/ingest/batch         → 202 + [job_ids]
GET  /api/v1/ingest/jobs          → all jobs
GET  /api/v1/ingest/jobs/{id}     → pending → running → done/failed
POST /api/v1/query                → answer (synchronous)
GET  /api/v1/wiki/status          → page counts by type
GET  /api/v1/wiki/pages           → list all page paths
GET  /api/v1/wiki/pages/{t}/{s}   → page content
GET  /api/v1/wiki/ideas           → research ideas list
POST /api/v1/wiki/lint            → health check report
POST /api/v1/graph/analyze        → analysis report
GET  /api/v1/graph/view           → interactive HTML visualization
GET  /api/v1/graph/data           → nodes + edges as JSON
GET  /api/v1/search               → BM25 search
GET  /health                      → liveness
```

---

## Wiki Conventions (for agents)

- All pages use `[[wikilinks]]` for cross-references
- Every page has YAML frontmatter: `title`, `type`, `summary` (max 150 chars)
- Contradictions: `> ⚠️ Contradiction: [old claim] vs [new claim (source)]`
- `concept/` pages: update existing — never create a duplicate
- `log.md`: append-only — never edit past entries

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `TFY_API_KEY` | Yes | TrueFoundry / LLM gateway API key |
| `TFY_BASE_URL` | Yes | LLM gateway base URL |
| `DEFAULT_MODEL` | No | Model ID (default: `tfy-ai-anthropic/claude-sonnet-4-6`) |
| `SUPADATA_API_KEY` | Yes (YouTube) | YouTube transcript fetching via Supadata |

`.env` file in project root is auto-loaded.

---

## Deployment (TrueFoundry)

```bash
# Backend — creates EFS persistent volume + deploys FastAPI service
python deploy/deploy_backend.py

# Frontend — deploys React app
python deploy/deploy_frontend.py
```

**Critical:** wiki data lives in `data/` which must be on a persistent volume — the container filesystem is ephemeral. `deploy_backend.py` creates an EFS volume (`efs-sc`, 10 GB) and mounts it at `/app/data`.

The frontend iframe for the knowledge graph must use an absolute URL (`VITE_API_URL` baked at Docker build time) — a relative `/api/v1/graph/view` resolves against the frontend host, not the backend.

---

## Roadmap

- GitHub repo ingestion (README + file tree + key function summaries)
- Voice note ingestion
- Image/OCR ingestion
- Telegram bot for mobile capture
- Spaced repetition — surface wiki pages due for review
