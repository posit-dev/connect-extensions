"""Background indexer for MCP server discovery and tool cataloging.

Runs on a configurable interval to:
1. Query Connect API for content matching watched tags
2. Sync discovered servers table
3. Health-check each server via tools/list
4. Store tool metadata in SQLite
5. Rebuild the FTS5 search index

When POSIT_PRODUCT is not set (local dev), the indexer skips Connect
discovery and instead probes servers listed in MCP_GATEWAY_LOCAL_SERVERS.
Format: "name=url,name=url" (e.g. "math=http://localhost:8081,weather=http://localhost:8082")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import TYPE_CHECKING, Any

from connect_client import ConnectClient
from database import Database

if TYPE_CHECKING:
    from search_engine import SearchEngine

import log

logger = log.getLogger(__name__)


def _is_connect_mode() -> bool:
    """Return True when running on Connect (POSIT_PRODUCT is set)."""
    return bool(os.environ.get("POSIT_PRODUCT"))


def _parse_local_servers() -> list[dict[str, str]]:
    """Parse MCP_GATEWAY_LOCAL_SERVERS env var.

    Format: "name=url,name=url"
    Returns list of {"name": ..., "url": ...} dicts.
    """
    raw = os.environ.get("MCP_GATEWAY_LOCAL_SERVERS", "")
    if not raw:
        return []
    servers = []
    for entry in raw.split(","):
        entry = entry.strip()
        if "=" not in entry:
            continue
        name, url = entry.split("=", 1)
        servers.append({"name": name.strip(), "url": url.strip()})
    return servers


class Indexer:
    """Discovers MCP servers and indexes their tools."""

    def __init__(
        self,
        db: Database,
        client: ConnectClient,
        search_engine: SearchEngine | None = None,
        interval_seconds: int = 300,
    ) -> None:
        self.db = db
        self.client = client
        self.search_engine = search_engine
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background indexing loop."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())
        mode = "Connect" if _is_connect_mode() else "local"
        logger.info(
            "Background indexer started (mode=%s, interval=%ds)",
            mode,
            self.interval_seconds,
        )

    async def stop(self) -> None:
        """Stop the background indexing loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Background indexer stopped")

    async def run_once(self) -> dict[str, Any]:
        """Run a single indexing cycle. Returns a summary."""
        if _is_connect_mode():
            return await self._run_connect_mode()
        return await self._run_local_mode()

    async def index_single_tag(
        self, tag_name: str, tag_id: str | None = None
    ) -> dict[str, Any]:
        """Index a single tag independently.

        Called when a new tag is added so it can run in parallel with
        other indexing jobs without waiting for a full cycle.
        """
        logger.info("Starting targeted index for tag %r (id=%s)", tag_name, tag_id)
        discovered, healthy, tools = await self._index_tag(tag_name, tag_id=tag_id)
        await self._rebuild_search_index()
        summary = {
            "tag": tag_name,
            "discovered": discovered,
            "healthy": healthy,
            "tools": tools,
        }
        logger.info("Targeted index complete for tag %r: %s", tag_name, summary)
        return summary

    async def index_single_tag_stream(self, tag_name: str, tag_id: str | None = None):
        """Index a single tag, yielding progress events as SSE data.

        Yields dicts with an "event" key: discovered, server_indexed, done, error.
        """
        logger.info("Starting streamed index for tag %r (id=%s)", tag_name, tag_id)

        try:
            if tag_id:
                content_items = await self.client.list_content_by_tag_id(tag_id)
            else:
                content_items = await self.client.list_content_by_tag(tag_name)
        except Exception:
            logger.exception("Failed to list content for tag %r", tag_name)
            yield {
                "event": "error",
                "tag": tag_name,
                "message": "Failed to query Connect for content",
            }
            return

        # Sync discovered servers.
        discovered_guids: set[str] = set()
        for item in content_items:
            guid = item.get("guid", "")
            name = item.get("name", "") or item.get("title", "")
            content_url = self.client.content_url(guid)
            self.db.upsert_server(guid, name, content_url, tag_name)
            discovered_guids.add(guid)

        removed = self.db.remove_servers_not_in(tag_name, discovered_guids)
        if removed:
            for guid in removed:
                self.db.remove_tools_for_server(guid)

        yield {
            "event": "discovered",
            "tag": tag_name,
            "servers": len(content_items),
        }

        # Index each server, yielding progress per server.
        healthy_count = 0
        tool_count = 0
        for item in content_items:
            guid = item["guid"]
            name = item.get("name", "") or item.get("title", "")
            content_url = self.client.content_url(guid)
            is_healthy, tools_indexed = await self._index_server(guid, content_url)
            if is_healthy:
                healthy_count += 1
            tool_count += tools_indexed
            yield {
                "event": "server_indexed",
                "tag": tag_name,
                "server": name,
                "guid": guid,
                "healthy": is_healthy,
                "tools": tools_indexed,
            }

        await self._rebuild_search_index()

        yield {
            "event": "done",
            "tag": tag_name,
            "discovered": len(content_items),
            "healthy": healthy_count,
            "tools": tool_count,
        }

    async def cleanup_after_tag_removal(self, tag_name: str) -> None:
        """Rebuild the search index after a tag (and its servers/tools) were removed.

        The DB cascade delete already removed the servers and tools rows.
        This just refreshes the search index so removed tools no longer
        appear in results.
        """
        logger.info("Rebuilding search index after removal of tag %r", tag_name)
        await self._rebuild_search_index()
        logger.info("Search index rebuilt after tag %r removal", tag_name)

    async def _run_connect_mode(self) -> dict[str, Any]:
        """Index via Connect API using watched tags."""
        watched = self.db.list_watched_tags()
        if not watched:
            logger.info("No watched tags configured — skipping indexing cycle")
            return {"tags": 0, "discovered": 0, "healthy": 0, "tools": 0}

        total_discovered = 0
        total_healthy = 0
        total_tools = 0

        for entry in watched:
            tag_name = entry["tag"]
            tag_id = entry.get("tag_id")
            discovered, healthy, tools = await self._index_tag(tag_name, tag_id=tag_id)
            total_discovered += discovered
            total_healthy += healthy
            total_tools += tools

        await self._rebuild_search_index()

        summary = {
            "tags": len(watched),
            "discovered": total_discovered,
            "healthy": total_healthy,
            "tools": total_tools,
        }
        logger.info("Indexing cycle complete: %s", summary)
        return summary

    async def _run_local_mode(self) -> dict[str, Any]:
        """Index local MCP servers listed in MCP_GATEWAY_LOCAL_SERVERS."""
        local_servers = _parse_local_servers()
        if not local_servers:
            logger.info(
                "Local mode: no servers configured in MCP_GATEWAY_LOCAL_SERVERS"
            )
            return {"discovered": 0, "healthy": 0, "tools": 0}

        # Ensure a "local" tag exists so the DB schema is satisfied.
        self.db.add_watched_tag("local")

        total_healthy = 0
        total_tools = 0

        for srv in local_servers:
            name = srv["name"]
            url = srv["url"]
            # Use name as the guid for local servers.
            self.db.upsert_server(name, name, url, "local")
            healthy, tool_count = await self._index_server(name, url)
            if healthy:
                total_healthy += 1
            total_tools += tool_count

        await self._rebuild_search_index()

        summary = {
            "discovered": len(local_servers),
            "healthy": total_healthy,
            "tools": total_tools,
        }
        logger.info("Local indexing cycle complete: %s", summary)
        return summary

    async def _loop(self) -> None:
        """Run indexing cycles forever on the configured interval.

        Waits a few seconds before the first cycle so the app can start
        serving HTTP (health checks, MCP) while the heavy index runs.
        """
        await asyncio.sleep(3)
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error during indexing cycle")
            await asyncio.sleep(self.interval_seconds)

    async def _index_tag(
        self, tag: str, tag_id: str | None = None
    ) -> tuple[int, int, int]:
        """Index all content for a single watched tag.

        Uses tag_id (Connect UUID) for direct lookup when available,
        falling back to name-based resolution.

        Returns (discovered_count, healthy_count, tool_count).
        """
        logger.info("Indexing tag: %s (id=%s)", tag, tag_id)

        try:
            if tag_id:
                content_items = await self.client.list_content_by_tag_id(tag_id)
            else:
                content_items = await self.client.list_content_by_tag(tag)
        except Exception:
            logger.exception("Failed to list content for tag %r", tag)
            return 0, 0, 0

        # Sync discovered servers — add new, remove untagged.
        discovered_guids: set[str] = set()
        for item in content_items:
            guid = item.get("guid", "")
            name = item.get("name", "") or item.get("title", "")
            content_url = self.client.content_url(guid)
            self.db.upsert_server(guid, name, content_url, tag)
            discovered_guids.add(guid)

        removed = self.db.remove_servers_not_in(tag, discovered_guids)
        if removed:
            logger.info(
                "Removed %d servers no longer tagged %r: %s",
                len(removed),
                tag,
                removed,
            )
            for guid in removed:
                self.db.remove_tools_for_server(guid)

        # Index tools for each discovered server concurrently.
        async def _index_one(item: dict) -> tuple[bool, int]:
            guid = item["guid"]
            content_url = self.client.content_url(guid)
            return await self._index_server(guid, content_url)

        results = await asyncio.gather(
            *[_index_one(item) for item in content_items],
            return_exceptions=True,
        )

        healthy_count = 0
        tool_count = 0
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Error indexing server: %s", r)
                continue
            is_healthy, count = r
            if is_healthy:
                healthy_count += 1
            tool_count += count

        return len(content_items), healthy_count, tool_count

    async def _index_server(self, guid: str, content_url: str) -> tuple[bool, int]:
        """Fetch tools from a server and store metadata.

        Skips the DB write if the tool set hasn't changed since the last
        index (compared by sha256 checksum), avoiding unnecessary churn.

        Status transitions: pending → indexing → ready | error

        Returns (is_reachable, tool_count).
        """
        self.db.set_server_indexing(guid)
        try:
            tools = await self.client.mcp_tools_list(content_url)
        except Exception:
            logger.warning(
                "Failed to fetch tools from server %s at %s",
                guid,
                content_url,
                exc_info=True,
            )
            self.db.update_server_health(guid, healthy=False)
            return False, 0

        self.db.update_server_health(guid, healthy=True, tool_count=len(tools))

        # Checksum the tools/list response to detect changes cheaply.
        # Canonical form: sorted JSON of the tool list.
        canonical = json.dumps(tools, sort_keys=True, separators=(",", ":"))
        new_hash = hashlib.sha256(canonical.encode()).hexdigest()

        server = self.db.get_server(guid)
        if server and server.get("tools_hash") == new_hash:
            logger.info(
                "Tools unchanged for server %s (%d tools, hash=%s…), skipping write",
                guid,
                len(tools),
                new_hash[:8],
            )
            self.db.update_server_indexed(guid, tools_hash=new_hash)
            return True, len(tools)

        # Tools changed — rewrite metadata.
        self.db.remove_tools_for_server(guid)
        for tool in tools:
            tool_name = tool.get("name", "")
            description = tool.get("description", "")
            input_schema = (
                json.dumps(tool.get("inputSchema")) if tool.get("inputSchema") else None
            )
            self.db.upsert_tool(
                server_guid=guid,
                tool_name=tool_name,
                description=description,
                input_schema=input_schema,
            )

        self.db.update_server_indexed(guid, tools_hash=new_hash)
        logger.info(
            "Indexed %d tools from server %s (hash=%s…)", len(tools), guid, new_hash[:8]
        )
        return True, len(tools)

    async def _rebuild_search_index(self) -> None:
        """Rebuild the FTS5 search index from all tool metadata.

        FTS5 rebuild is fast (milliseconds) so no thread pool is needed.
        """
        if self.search_engine is None:
            return

        try:
            count = self.search_engine.rebuild()
            logger.info("FTS5 index rebuilt with %d tools", count)
        except Exception:
            logger.exception("FTS5 index rebuild failed — keyword search will be used")
