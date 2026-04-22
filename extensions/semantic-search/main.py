"""Semantic search for Posit Connect content — ASGI entrypoint."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import lancedb
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from database import Database
from indexer import Indexer
from search import HybridSearch

INDEX_INTERVAL = int(os.environ.get("INDEX_INTERVAL", "60"))
DB_PATH = os.environ.get("DB_PATH", "data/search.db")
LANCE_PATH = os.environ.get("LANCE_PATH", "data/lancedb")

db = Database(db_path=DB_PATH)
lance_db = lancedb.connect(LANCE_PATH)
search_engine = HybridSearch(db=db, lance_db=lance_db)
indexer = Indexer(db=db, lance_db=lance_db, interval_seconds=INDEX_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await indexer.start()
    yield
    await indexer.stop()


api = FastAPI(title="Connect Content Search API")


@api.get("/search")
async def api_search(
    q: str = "",
    limit: int = 20,
    app_mode: str | None = None,
    content_category: str | None = None,
    mode: str = "hybrid",
):
    results = await asyncio.to_thread(
        search_engine.search, q, limit, app_mode, content_category, mode
    )
    return {"results": results}


@api.get("/filters")
async def api_filters():
    return {
        "app_modes": db.get_distinct_values("app_mode"),
        "content_categories": db.get_distinct_values("content_category"),
    }


@api.get("/status")
async def api_status():
    return indexer.status()


@api.post("/reindex")
async def api_reindex():
    asyncio.create_task(indexer.run_once())
    return {"status": "indexing"}


app = FastAPI(title="Connect Content Search", lifespan=lifespan)
app.mount("/api", api)

# Serve the Vue frontend — static assets at /assets, SPA fallback at /
static_dir = Path(__file__).parent / "static"
if static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(request: Request, path: str):
        # The built index.html uses relative asset paths (./assets/…) so Connect
        # can serve the extension under its /content/<guid>/ prefix. A trailing
        # slash on a route like /settings/ would resolve those relative paths
        # one directory deeper and 404 every asset — redirect so the browser
        # requests the canonical no-trailing-slash URL.
        if path and path != "/" and path.endswith("/"):
            return RedirectResponse(url=f"/{path.rstrip('/')}", status_code=307)
        # Try to serve the exact file first
        file_path = static_dir / path
        if path and file_path.is_file():
            return FileResponse(file_path)
        # Fall back to index.html for SPA routing
        return FileResponse(static_dir / "index.html")
