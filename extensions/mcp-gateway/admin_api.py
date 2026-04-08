"""FastAPI admin REST API for the MCP Gateway.

Provides endpoints for managing watched tags, viewing discovered servers
and tools, adjusting settings, and triggering re-indexing.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from connect_client import ConnectClient
from database import Database
from indexer import Indexer
from search_engine import SearchEngine
from mcp_tools import sync_call_tool

import log

logger = log.getLogger(__name__)

# Contextvar for admin routes only — safe because admin requests run in
# the ASGI request task (NOT the MCP transport's internal task).
_admin_visitor_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_admin_visitor_key", default=None
)


def create_admin_app(
    db: Database,
    client: ConnectClient,
    search_engine: SearchEngine,
    indexer: Indexer,
) -> FastAPI:
    """Build and return the FastAPI admin app with all routes."""

    app = FastAPI(
        title="MCP Gateway",
        description="Admin API for the MCP Gateway extension",
        version="0.1.0",
    )

    async def _require_editor() -> str | None:
        content_guid = os.environ.get("CONNECT_CONTENT_GUID", "")
        visitor_key = _admin_visitor_key.get()
        if not content_guid or not visitor_key:
            return None
        role = await client.get_content_role(content_guid, visitor_key)
        if role not in ("owner", "editor"):
            return "Forbidden"
        return None

    @app.get("/api/me")
    async def api_me():
        content_guid = os.environ.get("CONNECT_CONTENT_GUID", "")
        visitor_key = _admin_visitor_key.get()
        if not content_guid or not visitor_key:
            return JSONResponse({"role": "viewer"})
        role = await client.get_content_role(content_guid, visitor_key)
        return JSONResponse({"role": role})

    @app.get("/api/settings")
    async def api_get_settings():
        call_tool_enabled = db.get_setting("call_tool_enabled", "false") == "true"
        return JSONResponse({"call_tool_enabled": call_tool_enabled})

    @app.put("/api/settings")
    async def api_update_settings(request: Request):
        error = await _require_editor()
        if error:
            return JSONResponse({"error": error}, status_code=403)
        body = await request.json()
        if "call_tool_enabled" in body:
            enabled = bool(body["call_tool_enabled"])
            db.set_setting("call_tool_enabled", "true" if enabled else "false")
            sync_call_tool(enabled)
        return await api_get_settings()

    @app.get("/api/tags")
    async def api_list_tags():
        logger.info("GET /api/tags")
        watched = db.list_watched_tags()
        try:
            available = await client.list_tags()
        except Exception:
            logger.warning("Failed to fetch available tags from Connect", exc_info=True)
            available = []
        logger.info(
            "GET /api/tags: %d watched, %d available", len(watched), len(available)
        )
        return JSONResponse({"watched": watched, "available": available})

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    @app.post("/api/tags")
    async def api_add_tag(tag: str, tag_id: str | None = None):
        error = await _require_editor()
        if error:
            return JSONResponse({"error": error}, status_code=403)
        logger.info("POST /api/tags: tag=%r tag_id=%s", tag, tag_id)
        db.add_watched_tag(tag, tag_id=tag_id)

        async def stream():
            yield _sse("started", {"tag": tag})
            try:
                async for event in indexer.index_single_tag_stream(tag, tag_id=tag_id):
                    yield _sse(event["event"], event)
            except Exception as exc:
                logger.exception("Error indexing tag %r", tag)
                yield _sse("error", {"tag": tag, "message": str(exc)})

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.delete("/api/tags/{tag}")
    async def api_remove_tag(tag: str):
        error = await _require_editor()
        if error:
            return JSONResponse({"error": error}, status_code=403)
        logger.info("DELETE /api/tags/%s", tag)
        db.remove_watched_tag(tag)
        asyncio.create_task(indexer.cleanup_after_tag_removal(tag))
        return JSONResponse({"status": "ok"})

    @app.get("/api/servers")
    async def api_list_servers(tag: str | None = None):
        servers = db.list_servers(tag=tag)
        return JSONResponse({"servers": servers})

    @app.get("/api/servers/{guid}/tools")
    async def api_list_server_tools(guid: str):
        tools = db.list_tools(server_guid=guid)
        return JSONResponse({"tools": tools})

    @app.get("/api/search")
    async def api_search(query: str, limit: int = 10):
        results = search_engine.search(query, limit=limit)
        return JSONResponse({"results": results})

    _last_reindex_time: dict[str, datetime | None] = {"t": None}
    _REINDEX_COOLDOWN = timedelta(seconds=30)

    @app.post("/api/reindex")
    async def api_reindex():
        error = await _require_editor()
        if error:
            return JSONResponse({"error": error}, status_code=403)
        logger.info("POST /api/reindex")
        now = datetime.now(timezone.utc)
        last = _last_reindex_time["t"]
        if last and (now - last) < _REINDEX_COOLDOWN:
            remaining = int((_REINDEX_COOLDOWN - (now - last)).total_seconds())
            return JSONResponse(
                {"status": "rate_limited", "retry_after_seconds": remaining},
                status_code=429,
            )
        _last_reindex_time["t"] = now
        asyncio.create_task(indexer.run_once())
        return JSONResponse({"status": "indexing"})

    # Static files for the Registry UI.
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
