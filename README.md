# Second Brain

A personal knowledge OS powered by Claude. Feed it anything — articles, PDFs, YouTube videos, social posts — and it compiles everything into a persistent, interlinked wiki you can query in plain English.

**Not RAG.** Knowledge is compiled once and kept current. Cross-references already exist, contradictions already flagged, synthesis already done. Every ingest and every query makes the wiki denser.

---

## How it works

```
You ingest a source (URL / PDF / YouTube / social post)
          ↓
Reader fetches the content as plain text
          ↓
Compiler agent writes: summary + concept + connection + insight pages
          ↓                    each page has [[wikilinks]] to related ideas
Knowledge graph extracts triples: [[A]] --relation--> [[B]]
          ↓
You ask a question
          ↓
BM25 finds the 10 most relevant wiki pages
          ↓
LLM synthesizes a cited answer
          ↓
Non-trivial answers are filed back as new wiki pages
```

---

## Quickstart

**1. Install dependencies**

```bash
uv sync
```

**2. Set environment variables**

```bash
cp .env.example .env
# fill in:
#   TFY_API_KEY       — TrueFoundry / LLM gateway key
#   TFY_BASE_URL      — LLM gateway base URL
#   SUPADATA_API_KEY  — YouTube transcripts (free at https://supadata.ai)
```

**3. Ingest something**

```bash
# Article
uv run second-brain ingest "https://example.com/some-article"

# YouTube video
uv run second-brain ingest "https://youtu.be/abc123"

# PDF
uv run second-brain ingest data/raw/paper.pdf

# LinkedIn / X / Reddit post
uv run second-brain ingest "https://x.com/user/status/..."
```

**4. Ask a question**

```bash
uv run second-brain query "What are the key ideas from everything I've read?"
```

**5. Start the web UI**

```bash
# Backend API
uv run second-brain serve

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`

---

## CLI reference

| Command | What it does |
|---|---|
| `ingest <source>` | Compile a source into the wiki |
| `ingest-list <file.md>` | Ingest all URLs found in a file |
| `query "<question>"` | Ask the wiki a question |
| `status` | Page counts by type |
| `lint` | Wiki health check (contradictions, gaps, orphans) |
| `graph` | Analyze knowledge graph, generate research questions |
| `graph --view` | Graph analysis + open interactive visualization |
| `serve` | Start FastAPI backend on port 8000 |
| `serve --reload` | Dev mode with auto-reload |

---

## What gets written

Every ingest produces:

- **Summary** — what the source argues and why it matters
- **Concept pages** — one per central idea, updated (not duplicated) across ingests
- **Connection pages** — when the relationship between two ideas is the source's explicit point
- **Insight pages** — non-obvious findings that would surprise someone who knows the basics
- **Ideas** — 2–3 research questions the source opens up, appended to `output/ideas.md`

---

## Source types supported

| Source | How |
|---|---|
| `.txt`, `.md` | Direct read |
| `.pdf` | pypdf text extraction |
| YouTube URL | Supadata SDK — works from cloud IPs where `yt-dlp` is blocked |
| LinkedIn / X / Reddit / Threads | Jina.ai reader → DuckDuckGo fallback |
| Article URL | httpx + html2text |
| JS-rendered docs | DuckDuckGo `site:` search → fetch real sub-pages |

---

## Web UI pages

| Page | Purpose |
|---|---|
| Dashboard | Recent activity, wiki stats |
| Ingest | Paste a URL or upload a file, track job progress |
| Query | Ask questions, get cited answers |
| Wiki | Browse all pages by type |
| Graph | Interactive knowledge graph (nodes coloured by centrality) |
| Ideas | Research questions generated from ingested sources |

API docs at `http://localhost:8000/docs`

---

## Data layout

```
data/
├── raw/              ← drop sources here (LLM never writes here)
├── wiki/
│   ├── index.md      ← full catalog, updated on every page write
│   ├── log.md        ← append-only operation history
│   ├── summary/
│   ├── concept/
│   ├── connection/
│   ├── insight/
│   ├── qa/
│   └── lint/
├── output/
│   ├── ideas.md      ← research questions
│   └── graph.html    ← interactive visualization
├── infranodus/
│   └── wiki-ontology.md  ← triple store: [[A]] --rel--> [[B]]
└── todos/
    └── gaps.md       ← LLM-generated research questions from graph analysis
```

---

## Deployment (TrueFoundry)

```bash
# Creates EFS persistent volume + deploys FastAPI service
python deploy/deploy_backend.py

# Deploys React frontend
python deploy/deploy_frontend.py
```

Wiki data is stored in `data/` which is mounted from a persistent EFS volume — it survives pod restarts and redeployments.

---

## Development

```bash
uv run pytest           # tests
uv run ruff check .     # lint
uv run ruff format .    # format
```
