---
name: llm-wiki
description: >
  Build a complete LLM-maintained personal knowledge wiki — a second brain where an LLM
  automatically compiles, cross-references, and maintains structured knowledge from any source
  you feed it. Use this skill whenever the user wants to build a personal knowledge base,
  second brain, LLM wiki, or persistent wiki powered by an LLM; organize articles, PDFs,
  YouTube videos, or notes into a searchable interlinked wiki; implement the Karpathy LLM Wiki
  pattern; build a system where Claude automatically compiles knowledge from ingested sources;
  or add a query layer over their reading/research. Trigger for any variant of "second brain",
  "personal wiki", "knowledge base", "LLM wiki", "organize my research", "ingest articles into
  a wiki", "I want to query my notes", or "build me a RAG system" (this is better than RAG).
  Also trigger when the user asks about adding ingestion, query, or knowledge graph features
  to an existing project.
---

# LLM Wiki — Personal Knowledge OS

Build a persistent wiki owned and maintained by an LLM. You supply sources (URLs, PDFs, YouTube, plain text). The LLM compiles, cross-references, and files everything as structured markdown. You query it; answers are synthesized and filed back. The wiki compounds with every ingest and every question.

**Why this beats RAG:** RAG re-derives knowledge from scratch on every query. This system compiles knowledge once — cross-references already exist, contradictions already flagged, synthesis already done. Asking a question can create a new wiki page that future questions build on.

---

## Mental model

```
You ingest a source
      ↓
Compiler agent reads it → writes summary + concept + connection + insight pages
      ↓                    each page has [[wikilinks]] to related concepts
graph.py extracts triples: [[A]] --relation--> [[B]]  (append-only ontology)
      ↓
You ask a question
      ↓
BM25 searches full page content → top 10 relevant pages
      ↓
LLM synthesizes answer with [[wikilink]] citations
      ↓
_maybe_file(): non-trivial answers written back as qa/ or insight/ pages
      ↓
Graph analysis → isolated clusters, hub concepts, gap questions → new reading list
```

Every ingest, every query, every graph run makes the wiki denser. Nothing is wasted.

---

## Tech stack (use these exactly — they compose well)

| Layer | Choice | Reason |
|---|---|---|
| Package manager | `uv` | Fast, lockfile, reproducible |
| LLM client | `openai` SDK | Works with any OpenAI-compatible gateway |
| Retrieval | `rank-bm25` | No vectors, no cost, works offline, good enough |
| Graph | `networkx` + `pyvis` | In-process, self-contained HTML output |
| API | `fastapi` + `uvicorn` | Background tasks for slow ingest, auto-docs |
| Storage | Filesystem markdown | Git-native, Obsidian-compatible, no DB |
| Viewer | Obsidian | [[wikilink]] graph view, Dataview, free |

---

## Directory layout

```
<project>/
├── data/
│   ├── raw/                  ← sources go here (LLM never writes here)
│   ├── wiki/
│   │   ├── index.md          ← catalog, updated on every page write
│   │   ├── log.md            ← append-only operation history
│   │   ├── summary/          ← one page per ingested source
│   │   ├── concept/          ← one page per idea/entity (no duplicates)
│   │   ├── connection/       ← one page per relationship pair
│   │   ├── insight/          ← non-obvious cross-cutting findings
│   │   ├── qa/               ← filed query answers
│   │   └── lint/             ← health check reports
│   ├── output/
│   │   ├── ideas.md          ← research questions from ingestion
│   │   └── graph.html        ← interactive visualization
│   ├── infranodus/
│   │   └── wiki-ontology.md  ← append-only triple store
│   └── todos/
│       └── gaps.md           ← LLM-generated research questions
├── src/<package>/
│   ├── config.py
│   ├── llm.py
│   ├── wiki.py
│   ├── reader.py
│   ├── search.py
│   ├── graph.py
│   ├── cli.py
│   ├── agents/
│   │   ├── compiler.py
│   │   ├── query.py
│   │   └── review.py
│   └── api/
│       ├── main.py
│       ├── models.py
│       ├── jobs.py
│       └── routers/
│           ├── ingest.py
│           ├── query.py
│           ├── wiki.py
│           └── graph.py
├── backend/
│   └── server.py
└── pyproject.toml
```

---

## Step-by-step implementation

### Step 1 — Scaffold

```bash
uv init <project-name>
cd <project-name>
mkdir -p src/<package>/agents src/<package>/api/routers
mkdir -p data/raw data/wiki data/output backend
touch src/<package>/__init__.py src/<package>/agents/__init__.py
touch src/<package>/api/__init__.py src/<package>/api/routers/__init__.py

uv add openai python-dotenv click httpx html2text pypdf \
        youtube-transcript-api "duckduckgo-search>=6.0" \
        "rank-bm25>=0.2" "networkx>=3.0" pyvis \
        "fastapi>=0.100" "uvicorn[standard]>=0.20" python-multipart
```

`pyproject.toml` entry point:
```toml
[project.scripts]
<cli-name> = "<package>.cli:main"
```

`.env`:
```
TFY_API_KEY=<your-api-key>
TFY_BASE_URL=https://your-gateway/api/llm
DEFAULT_MODEL=your-model-id
```

**→ Read `references/core-modules.md` for complete `config.py`, `llm.py`, `wiki.py`, `search.py`**

---

### Step 2 — Reader

Handles local files + 3 URL types with automatic fallback:

| Input | Handler |
|---|---|
| `.txt`, `.md` | Direct read |
| `.pdf` | `pypdf.PdfReader` |
| YouTube URL | `YouTubeTranscriptApi().fetch(video_id)` — **instance method** in v1.x |
| Article URL | `httpx` + `html2text` |
| JS-rendered docs | Detect if < 300 chars → DuckDuckGo `site:` search → fetch real sub-pages |

**→ Read `references/reader.md` for complete `reader.py`**

---

### Step 3 — Compiler agent (most critical)

OpenAI tool-calling loop with two tools: `write_wiki_page` and `update_ideas`.

**Critical implementation details that commonly go wrong:**

```python
# CORRECT break condition — finish_reason=="length" also stops tool calls
if not choice.message.tool_calls:
    break

# WRONG — breaks prematurely when response is long
if choice.finish_reason != "tool_calls":
    break
```

- `max_tokens=16000` — compiler writes multiple long pages per call
- Validate required fields before accessing `args` dict (KeyError guard)
- Append `choice.message` object (not just content) as assistant turn
- After writing pages: call `extract_triples(pages_written)` for graph

SYSTEM prompt must instruct the LLM to:
1. Write one `summary` page for the source
2. Write one `concept` page per significant idea — **check index first, update existing, never duplicate**
3. Write `connection` pages for relationships between concepts
4. Write `insight` pages for non-obvious cross-cutting findings
5. Call `update_ideas` with research questions the source opens up
6. Use `[[wikilinks]]` throughout for cross-references
7. Flag contradictions: `> ⚠️ Contradiction: [old claim] vs [new claim (source)]`

**→ Read `references/agents.md` for complete compiler, query, review code**

---

### Step 4 — Query agent

Two-pass, no tool calling:
1. `bm25_search(question, top_k=10)` — replaces LLM index scan (faster, no extra LLM call)
2. LLM synthesizes answer with `[[wikilink]]` citations
3. `_maybe_file()` — LLM decides if worth preserving → write qa/ or insight/ page

Output format: LLM chooses — table for comparisons, numbered steps for how-to, prose for factual, structured sections for complex synthesis. Don't constrain it.

---

### Step 5 — Knowledge graph

Two functions to implement:

**`extract_triples(pages_written)`** — called by compiler after every ingest:
- LLM reads newly written pages
- Extracts `{"a": "...", "rel": "...", "b": "..."}` JSON
- Formats as `[[A]] --relation--> [[B]]`
- Appends only NEW triples to `wiki-ontology.md` (append-only, dedup)

**`analyze()`** — called by `second-brain graph`:
- Loads triples → builds `nx.DiGraph`
- Betweenness centrality, WCC, bridges, in/out degree
- LLM generates 7-10 research questions targeting gaps → writes to `gaps.md`

**`visualize()`** — called by `second-brain graph --view` or `GET /api/v1/graph/view`:
- pyvis Network from networkx graph
- Nodes coloured by centrality: red (hub) → orange → blue (peripheral)
- Hover shows entity name, centrality, connection count
- `cdn_resources="in_line"` for fully self-contained HTML

**→ Read `references/graph.md` for complete `graph.py`**

---

### Step 6 — CLI

```bash
<cli> ingest <file_or_url>      # single source
<cli> ingest-list <file.md>     # all URLs in a file
<cli> query "<question>"        # answer from wiki
<cli> query "<question>" --no-file  # without auto-filing
<cli> lint                      # health check
<cli> status                    # page counts
<cli> graph                     # analysis + gap questions
<cli> graph --view              # analysis + open browser visualization
<cli> serve                     # start FastAPI server
<cli> serve --reload            # dev mode
```

`ingest-list`: regex-extract all `https://` URLs from file, process sequentially, log issues to `ISSUES.md`.

---

### Step 7 — FastAPI backend

All ingest endpoints return **202 Accepted immediately** — ingest takes 30–60s, never block.

```
POST /api/v1/ingest/url           → 202 + job_id (URL fetch + compile in background)
POST /api/v1/ingest/text          → 202 + job_id
POST /api/v1/ingest/file          → 202 + job_id (multipart .txt/.md/.pdf)
POST /api/v1/ingest/batch         → 202 + [job_ids] (one per URL)
GET  /api/v1/ingest/jobs          → all jobs
GET  /api/v1/ingest/jobs/{id}     → poll: pending→running→done/failed
POST /api/v1/query                → answer (synchronous, 10-30s)
GET  /api/v1/wiki/status          → page counts by type
GET  /api/v1/wiki/pages           → list all page paths
GET  /api/v1/wiki/pages/{t}/{s}   → page content
GET  /api/v1/wiki/ideas           → research ideas list
POST /api/v1/wiki/lint            → health check report
POST /api/v1/graph/analyze        → analysis report
GET  /api/v1/graph/view           → interactive HTML visualization
GET  /api/v1/graph/data           → nodes + edges as JSON
GET  /health                      → liveness
```

**→ Read `references/api.md` for complete FastAPI code**

---

## Wiki conventions (put these in every agent's SYSTEM prompt)

```
- Every page: YAML frontmatter with title, type, summary (max 150 chars)
- Cross-references: [[Page Title]] wikilink syntax throughout
- Contradictions: > ⚠️ Contradiction: [old claim] vs [new claim (source)]
- Concept pages: check index first — update existing, never create a duplicate
- log.md: append-only — format: ## [YYYY-MM-DD HH:MM UTC] operation | details
```

---

## Index structure (categorized, not flat)

```markdown
# Wiki Index

## Summaries
- [[summary/foo.md|Source Title]] `summary` — one-line summary

## Concepts
- [[concept/bar.md|Concept Name]] `concept` — one-line summary

## Connections
## Insights
## Q&A
## Lint
```

`update_index()` inserts entries under the right section header, creating the section if it doesn't exist yet.

---

## Obsidian setup (zero code required)

1. Obsidian → "Open folder as vault" → select `data/wiki/`
2. Settings → Core plugins → enable: Backlinks, Graph view, Outgoing links
3. Community plugins: **Dataview** (frontmatter queries), **Obsidian Web Clipper** (capture URLs to `data/raw/`)
4. Cmd+G → Graph view shows the full [[wikilink]] network live

---

## Common pitfalls

| Pitfall | Fix |
|---|---|
| Compiler loop breaks on long responses | Use `if not choice.message.tool_calls: break`, not `finish_reason` |
| Query returns "no pages found" despite full wiki | Strip `wiki/` prefix from paths; use `relative_to(WIKI_DIR)` not `WIKI_DIR.parent` |
| YouTube transcripts fail with AttributeError | Use `YouTubeTranscriptApi().fetch(video_id)` (instance, v1.x), not class method |
| f-string backslash SyntaxError (Python < 3.12) | `"---\n".join(parts)` outside the f-string |
| Empty .md files appear in wiki root | Obsidian placeholders — skip `p.parent == WIKI_DIR` and empty files in `read_all_pages()` |
| Duplicate concept pages accumulate | Add to SYSTEM: "check the index first — update existing pages, never create a duplicate" |
| API ingest blocks on slow URL fetch | Move `read_source()` inside the background task, not before it |
