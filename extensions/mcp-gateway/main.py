"""MCP Gateway — ASGI entrypoint.

Uses FastMCP's ``streamable_http_app()`` to serve the MCP transport at
``/mcp`` and mounts the admin FastAPI app + static files as custom
routes in the same Starlette application.

A thin ASGI middleware handles two cross-cutting concerns:
1. **Service lifecycle** — starts/stops the indexer, health checker,
   and HTTP client pool at ASGI lifespan boundaries.
2. **Visitor identity** — extracts the Connect session token from
   incoming requests and resolves it to a visitor API key + user GUID,
   injected as headers so both MCP tool handlers and admin routes can
   read them.

The entrypoint is ``main:app``.
"""

from __future__ import annotations

import asyncio
import os

from starlette.routing import Mount

from connect_client import ConnectClient
from database import Database
from health_checker import HealthChecker
from indexer import Indexer
from search_engine import SearchEngine
from user_tool_store import UserToolStore
from mcp_tools import mcp_server, init_mcp_server, sync_call_tool, make_tool
from admin_api import create_admin_app, _admin_visitor_key

import log

logger = log.getLogger("mcp_gateway")


# --- Configuration ---

INDEX_INTERVAL = int(os.environ.get("MCP_GATEWAY_INDEX_INTERVAL", "120"))
HEALTH_INTERVAL = int(os.environ.get("MCP_GATEWAY_HEALTH_INTERVAL", "60"))
DB_PATH = os.environ.get("MCP_GATEWAY_DB_PATH", "data/gateway.db")


# --- Shared state ---

logger.info(
    "Configuration: db=%s index_interval=%ds health_interval=%ds",
    DB_PATH, INDEX_INTERVAL, HEALTH_INTERVAL,
)
db = Database(db_path=DB_PATH)
connect = ConnectClient()
logger.info("Connect server: %s", connect.server_url or "(not set)")
search_engine = SearchEngine(db=db)
indexer = Indexer(
    db=db, client=connect, search_engine=search_engine, interval_seconds=INDEX_INTERVAL
)
health_checker = HealthChecker(db=db, client=connect, interval_seconds=HEALTH_INTERVAL)
user_store = UserToolStore(db=db, tool_factory=make_tool)

# Wire dependencies into the MCP server module.
init_mcp_server(db, connect, search_engine, user_store)

# Build the admin FastAPI app (handles /api/* routes + static UI).
admin_app = create_admin_app(db, connect, search_engine, indexer)

# Mount admin + static as custom routes in the MCP Starlette app.
# These are appended AFTER the /mcp route so MCP takes priority.
mcp_server._custom_starlette_routes.append(Mount("/", app=admin_app))

# Build the combined Starlette app (MCP at /mcp, admin at /*).
starlette_app = mcp_server.streamable_http_app()


# --- ASGI middleware ---


class _GatewayMiddleware:
    """Thin ASGI wrapper for service lifecycle and visitor identity.

    Wraps the Starlette app returned by ``streamable_http_app()`` to:
    - Start/stop background services (indexer, health checker) at
      ASGI lifespan boundaries, coordinating with the inner app's
      own lifespan (session manager).
    - Resolve Connect visitor identity from the session token header
      and inject it as ``x-gateway-visitor-key`` / ``x-gateway-user-guid``
      headers into the ASGI scope for downstream handlers.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        elif scope["type"] in ("http", "websocket"):
            await self._handle_request(scope, receive, send)

    async def _handle_request(self, scope, receive, send):
        """Resolve visitor identity, inject headers, set admin contextvar."""
        token = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"posit-connect-user-session-token":
                token = header_value.decode("latin-1")
                break

        visitor_key = None
        extra_headers: list[tuple[bytes, bytes]] = []

        if token:
            try:
                visitor_key = await connect.exchange_visitor_token(token)
                extra_headers.append(
                    (b"x-gateway-visitor-key", visitor_key.encode("latin-1"))
                )
                try:
                    uguid = await connect.get_user_guid(visitor_key)
                    extra_headers.append(
                        (b"x-gateway-user-guid", uguid.encode("latin-1"))
                    )
                except Exception:
                    logger.warning("Failed to resolve user GUID", exc_info=True)
            except Exception:
                logger.warning("Failed to exchange visitor session token", exc_info=True)

        if extra_headers:
            scope = {**scope, "headers": list(scope.get("headers", [])) + extra_headers}

        # Set the contextvar for admin routes (safe because admin runs in
        # the same ASGI task; MCP tools use the injected headers instead).
        reset_token = _admin_visitor_key.set(visitor_key)
        try:
            await self.inner(scope, receive, send)
        finally:
            _admin_visitor_key.reset(reset_token)

    async def _handle_lifespan(self, scope, receive, send):
        """Start gateway services, then delegate to the inner app's lifespan."""
        message = await receive()
        if message["type"] != "lifespan.startup":
            return

        try:
            # Start gateway background services.
            await indexer.start()
            await health_checker.start()
            sync_call_tool(db.get_setting("call_tool_enabled", "false") == "true")
            logger.info("MCP Gateway started")

            # Proxy lifespan to the inner Starlette app so its session
            # manager starts and stops correctly.
            inner_started = asyncio.Event()
            inner_shutdown = asyncio.Event()

            async def inner_receive():
                if not inner_started.is_set():
                    inner_started.set()
                    return {"type": "lifespan.startup"}
                await inner_shutdown.wait()
                return {"type": "lifespan.shutdown"}

            async def inner_send(msg):
                if msg["type"] == "lifespan.startup.failed":
                    raise RuntimeError(msg.get("message", "inner startup failed"))

            inner_task = asyncio.create_task(
                self.inner(scope, inner_receive, inner_send)
            )
            await inner_started.wait()

            await send({"type": "lifespan.startup.complete"})

            # Wait for the outer shutdown signal.
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.shutdown":
                    break

            # Shut down inner app, then gateway services.
            inner_shutdown.set()
            await inner_task

            await health_checker.stop()
            await indexer.stop()
            await connect.close()
            logger.info("MCP Gateway stopped")

            await send({"type": "lifespan.shutdown.complete"})
        except Exception as exc:
            await send({"type": "lifespan.startup.failed", "message": str(exc)})


app = _GatewayMiddleware(starlette_app)
