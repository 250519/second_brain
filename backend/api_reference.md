# Second Brain API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## Start the server

```bash
uv run second-brain serve               # default 0.0.0.0:8000
uv run second-brain serve --port 9000
uv run second-brain serve --reload      # dev mode

# or directly:
uv run python backend/server.py --reload
```

---

## Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service liveness check |

---

### Ingest  (`/api/v1/ingest`)
All ingest operations return **202 Accepted** immediately with a `job_id`.  
Poll `GET /api/v1/ingest/jobs/{job_id}` for the result.

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/url` | `{"url": "...", "source_name": "optional"}` | Ingest a URL (article, YouTube, docs) |
| POST | `/text` | `{"content": "...", "source_name": "..."}` | Ingest raw text |
| POST | `/file` | multipart `file` field | Upload `.txt`, `.md`, or `.pdf` |
| POST | `/batch` | `{"urls": ["...", "..."]}` | Ingest multiple URLs, one job each |
| GET  | `/jobs` | — | List all jobs |
| GET  | `/jobs/{job_id}` | — | Poll a specific job |

**Job status values:** `pending` → `running` → `done` / `failed`

---

### Query  (`/api/v1/query`)
Synchronous — waits for the answer (10–30 s typical).

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `` | `{"question": "...", "file_back": true}` | Answer a question from the wiki |

`file_back: true` (default) auto-files non-trivial answers back into the wiki.

---

### Wiki  (`/api/v1/wiki`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Page counts, raw sources, ideas count |
| GET | `/index` | Full wiki index markdown |
| GET | `/pages` | List all page paths |
| GET | `/pages/{type}/{slug}` | Get a specific page (e.g. `concept/rag`) |
| GET | `/ideas` | All research ideas from ingestion |
| POST | `/lint` | Run wiki health check (slow, ~30 s) |

---

### Graph  (`/api/v1/graph`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/analyze` | Run knowledge graph analysis + generate gap questions |
