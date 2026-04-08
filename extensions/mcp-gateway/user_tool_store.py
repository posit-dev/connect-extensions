"""Per-user tool store for the MCP Gateway.

Tracks dynamically registered tools per Connect user.  Tools are persisted
to the database so they survive process restarts.  All MCP sessions
belonging to the same user share a single tool list.  Active sessions
are tracked via ``weakref.WeakSet`` so they're automatically cleaned up
when the transport task exits.

Thread safety: all mutations go through an ``asyncio.Lock`` per user to
prevent interleaving between concurrent tool add/remove operations from
different sessions belonging to the same user.
"""

from __future__ import annotations

import asyncio
import json
import weakref
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp.tools import Tool as McpTool
from mcp.server.session import ServerSession

from database import Database

import log

logger = log.getLogger(__name__)

# Type for the factory that creates McpTool from stored metadata.
ToolFactory = Callable[[str, str, dict | None], McpTool]


class UserToolStore:
    """Tracks dynamically registered tools keyed by Connect user GUID.

    Args:
        db: Database instance for persistence.
        tool_factory: Callable(server_guid, tool_name, input_schema) → McpTool.
            Used to reconstitute proxy tools from stored metadata.
    """

    def __init__(self, db: Database, tool_factory: ToolFactory):
        self._db = db
        self._tool_factory = tool_factory

        # user_guid → {tool_name: McpTool}
        self._users: dict[str, dict[str, McpTool]] = {}
        # user_guid → {tool_name: server_guid}
        self._tool_servers: dict[str, dict[str, str]] = {}
        # user_guid → set of active ServerSession objects (weak refs)
        self._user_sessions: dict[str, weakref.WeakSet[ServerSession]] = {}
        # user_guid → {tool_name: search result dict} (accumulated)
        self._search_cache: dict[str, dict[str, dict[str, Any]]] = {}
        # user_guid → asyncio.Lock for mutation serialization
        self._locks: dict[str, asyncio.Lock] = {}
        # Track which users have been hydrated from DB.
        self._hydrated: set[str] = set()

    def _lock_for(self, user_guid: str) -> asyncio.Lock:
        """Return (or create) the per-user asyncio lock."""
        lock = self._locks.get(user_guid)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_guid] = lock
        return lock

    def _ensure_hydrated(self, user_guid: str) -> None:
        """Load tools from the database on first access for a user."""
        if user_guid in self._hydrated:
            return

        rows = self._db.list_user_tools(user_guid)
        for row in rows:
            tool_name = row["tool_name"]
            server_guid = row["server_guid"]
            description = row.get("description", "")
            input_schema_str = row.get("input_schema", "{}")
            try:
                input_schema = (
                    json.loads(input_schema_str) if input_schema_str else None
                )
            except (json.JSONDecodeError, TypeError):
                input_schema = None

            tool = self._tool_factory(server_guid, tool_name, input_schema, description)
            self._users.setdefault(user_guid, {})[tool_name] = tool
            self._tool_servers.setdefault(user_guid, {})[tool_name] = server_guid

        self._hydrated.add(user_guid)
        if rows:
            logger.info("Hydrated %d tools from DB for user %s", len(rows), user_guid)

    # --- Session tracking ---

    def register_session(self, user_guid: str, session: ServerSession):
        """Register a session for a user (idempotent)."""
        ws = self._user_sessions.setdefault(user_guid, weakref.WeakSet())
        was_new = session not in ws
        ws.add(session)
        if was_new:
            logger.info(
                "register_session: user=%s session=%s total=%d",
                user_guid, id(session), len(ws),
            )

    # --- Tool management (must be called under the per-user lock) ---

    def add(
        self,
        user_guid: str,
        tool_name: str,
        server_guid: str,
        tool: McpTool,
        description: str,
        input_schema: dict | None,
    ):
        """Add a tool to the in-memory store and persist to DB."""
        self._users.setdefault(user_guid, {})[tool_name] = tool
        self._tool_servers.setdefault(user_guid, {})[tool_name] = server_guid
        self._db.save_user_tool(
            user_guid=user_guid,
            tool_name=tool_name,
            server_guid=server_guid,
            description=description,
            input_schema=json.dumps(input_schema) if input_schema else "{}",
        )

    def remove(self, user_guid: str, tool_name: str) -> bool:
        """Remove a tool from in-memory store and DB. Returns True if removed."""
        removed = False
        if user_guid in self._users and tool_name in self._users[user_guid]:
            del self._users[user_guid][tool_name]
            removed = True
        if (
            user_guid in self._tool_servers
            and tool_name in self._tool_servers[user_guid]
        ):
            del self._tool_servers[user_guid][tool_name]
        if removed:
            self._db.remove_user_tool(user_guid, tool_name)
        return removed

    # --- Read-only accessors (hydrate on first access) ---

    def get_tool(self, user_guid: str, tool_name: str) -> McpTool | None:
        self._ensure_hydrated(user_guid)
        return self._users.get(user_guid, {}).get(tool_name)

    def user_tool_names(self, user_guid: str) -> set[str]:
        self._ensure_hydrated(user_guid)
        return set(self._users.get(user_guid, {}).keys())

    def user_tools(self, user_guid: str) -> list[McpTool]:
        self._ensure_hydrated(user_guid)
        return list(self._users.get(user_guid, {}).values())

    # --- Search cache (accumulated across searches) ---

    def cache_search_results(self, user_guid: str, results: list[dict[str, Any]]):
        """Merge search results into the user's cache."""
        cache = self._search_cache.setdefault(user_guid, {})
        for r in results:
            cache[r["tool_name"]] = r

    def get_cached_tool(self, user_guid: str, tool_name: str) -> dict[str, Any] | None:
        return self._search_cache.get(user_guid, {}).get(tool_name)

    # --- Notifications ---

    async def notify_user_sessions(
        self, user_guid: str, *, except_session: ServerSession | None = None
    ):
        """Send ``tools/list_changed`` to all active sessions for a user."""
        sessions = self._user_sessions.get(user_guid)
        if not sessions:
            logger.info("notify_user_sessions: no sessions for user %s", user_guid)
            return
        snapshot = list(sessions)
        logger.info(
            "notify_user_sessions: user=%s sessions=%d excluding_caller=%s",
            user_guid, len(snapshot), except_session is not None,
        )
        notified = 0
        for session in snapshot:
            if session is except_session:
                continue
            try:
                await session.send_tool_list_changed()
                notified += 1
            except Exception:
                logger.warning(
                    "notify_user_sessions: failed for user %s",
                    user_guid, exc_info=True,
                )
        logger.info(
            "notify_user_sessions: notified %d other sessions for user %s",
            notified, user_guid,
        )
