# Connect Content Semantic Search

A hybrid semantic search engine for Posit Connect content. Combines vector embeddings (MiniLM) with SQLite FTS5 full-text search, merged via Reciprocal Rank Fusion (RRF), so users can find content by meaning rather than exact keywords.

The app is a FastAPI backend with a Vue 3 single-page frontend. A background indexer syncs all content metadata from Connect on a configurable interval.

## Architecture

```
FastAPI (main.py)
├── /api/search      — hybrid search endpoint
├── /api/filters     — available app_mode / content_category values
├── /api/status      — indexer status (last run, content count)
├── /api/reindex     — trigger a manual re-index
└── /               — serves the Vue 3 SPA (static/)

Background Indexer (indexer.py)
└── Fetches Connect content → SHA-256 diff → embed with MiniLM → store in LanceDB + SQLite FTS5

Search Engine (search.py)
├── Vector search:  LanceDB cosine similarity (all-MiniLM-L6-v2, 384-dim)
├── FTS5 search:    SQLite BM25 full-text
└── RRF merge:      Reciprocal Rank Fusion (K=60) combines both rankings

Frontend (ui/ → static/)
└── Vue 3 + Vite SPA — debounced search, filters by type/category, search mode toggle
```

## Prerequisites

- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- Node.js 18+ and npm (only needed if rebuilding the frontend)
- A running Posit Connect server with an API key

> **Note:** The embedding model (`all-MiniLM-L6-v2`, ~87 MB) is downloaded automatically from HuggingFace on first startup. It is cached in a `models/` directory alongside the app. This directory is gitignored and should not be committed.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CONNECT_SERVER` | Yes | — | URL of your Connect server, e.g. `https://connect.example.com/` |
| `CONNECT_API_KEY` | Yes | — | Connect API key with at least Viewer permissions to read content metadata |
| `INDEX_INTERVAL` | No | `60` | How often (in seconds) to re-index content from Connect |
| `DB_PATH` | No | `data/search.db` | Path for the SQLite database |
| `LANCE_PATH` | No | `data/lancedb` | Path for the LanceDB vector store |

Create a `.env` file in the extension root (never commit this file):

```
CONNECT_SERVER=https://your-connect-server.example.com/
CONNECT_API_KEY=your_api_key_here
INDEX_INTERVAL=60
```

## Running Locally

### 1. Install Python dependencies

```bash
uv sync
```

Or with pip:

```bash
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env   # if an example exists, otherwise create .env manually
# Edit .env with your CONNECT_SERVER and CONNECT_API_KEY
```

### 3. (Optional) Pre-download the embedding model

The model downloads automatically on first startup, but you can pre-download it to avoid the delay:

```bash
uv run python -c "from embeddings import get_model; get_model(); print('Model ready.')"
```

The model is cached in `models/` (~87 MB). This directory is gitignored.

### 4. Start the server

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or using `just`:

```bash
just serve
```

The app is available at [http://localhost:8000](http://localhost:8000).

On first start, the indexer runs automatically (with a 2-second delay) and fetches all content from your Connect server. Depending on the number of content items and whether the model needs to download, this can take 1–5 minutes.

## Development Mode (Frontend Hot Reload)

The `static/` directory contains a pre-built Vue 3 frontend that is served directly by FastAPI. For frontend development with hot module replacement:

### 1. Install Node dependencies

```bash
cd ui && npm install
```

### 2. Start both servers together

```bash
just dev
```

This runs:
- FastAPI backend on port `8000`
- Vite dev server on port `5173` (proxies `/api` requests to the backend)

Open [http://localhost:5173](http://localhost:5173) for the dev server with HMR.

### 3. Build the frontend

When done with frontend changes, rebuild the static bundle:

```bash
just ui-build
```

This writes the compiled output to `static/` (which is gitignored in the source repo but should be committed in this extensions repo).

## Useful `just` Commands

| Command | Description |
|---|---|
| `just serve` | Start the FastAPI server (serves pre-built frontend) |
| `just dev` | Start backend + Vite dev server together |
| `just sync` | Install Python dependencies via uv |
| `just ui-setup` | Install Node dependencies |
| `just ui-build` | Build the Vue frontend into `static/` |
| `just setup` | Full setup: Python + UI deps |
| `just reindex` | Trigger a manual re-index (server must be running) |
| `just search "query"` | Search via the API (server must be running) |
| `just status` | Check indexer status |

## API Reference

All endpoints are under `/api/`.

### `GET /api/search`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | string | `""` | Search query |
| `limit` | int | `20` | Max results to return |
| `app_mode` | string | — | Filter by app mode (e.g. `shiny`, `python-fastapi`) |
| `content_category` | string | — | Filter by content category |
| `mode` | string | `hybrid` | Search mode: `hybrid`, `vector`, or `fts` |

Returns `{ "results": [...] }` where each result is a content item with an added `score` field.

### `GET /api/filters`

Returns `{ "app_modes": [...], "content_categories": [...] }` — the distinct values available for filtering.

### `GET /api/status`

Returns the indexer state: last run time, content count, whether indexing is in progress.

### `POST /api/reindex`

Triggers a manual re-index in the background. Returns immediately.

## Data Storage

All runtime data is stored in the `data/` directory (gitignored):

| Path | Contents |
|---|---|
| `data/search.db` | SQLite database with content metadata and FTS5 index |
| `data/lancedb/` | LanceDB vector store with MiniLM embeddings |

Both are created automatically on first run. Delete `data/` to force a full re-index from scratch.

## Deploying to Posit Connect

1. Ensure `static/` is built and committed (run `just ui-build` if needed).
2. Set the environment variables (`CONNECT_SERVER`, `CONNECT_API_KEY`) in the Connect content settings under **Vars**.
3. Deploy using `rsconnect` or the Connect UI with `manifest.json`.

The indexer starts automatically when the content is deployed and runs every `INDEX_INTERVAL` seconds.
