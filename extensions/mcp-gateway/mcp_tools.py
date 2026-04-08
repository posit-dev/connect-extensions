"""MCP server, tool manager override, and tool handler definitions.

Creates the ``FastMCP`` server, overrides its ToolManager for per-user
tool isolation, and registers the permanent meta-tools (search_tools,
add_tools, remove_tools, call_tool).
"""

from __future__ import annotations

import inspect
import time
from typing import Any
from urllib.parse import urlparse
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.server.fastmcp.tools import Tool as McpTool
from mcp.server.lowlevel.server import request_ctx as _server_request_ctx
from mcp.server.sse import TransportSecuritySettings

from connect_client import ConnectClient
from database import Database
from search_engine import SearchEngine
from user_tool_store import UserToolStore

import log

logger = log.getLogger(__name__)

# Names of the permanent meta-tools that must never be removed.
PERMANENT_TOOLS = frozenset({"search_tools", "call_tool", "add_tools", "remove_tools"})

# JSON Schema type → Python type mapping for proxy function signatures.
_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


# --- Request-context helpers ---


def _request_header(name: str) -> str | None:
    """Read a header from the current MCP request context."""
    try:
        ctx = _server_request_ctx.get()
        if ctx and ctx.request:
            return ctx.request.headers.get(name)
    except LookupError:
        pass
    return None


def _visitor_key() -> str | None:
    return _request_header("x-gateway-visitor-key")


def _user_guid() -> str | None:
    return _request_header("x-gateway-user-guid")


# --- Transport security ---


def _build_transport_security() -> TransportSecuritySettings | None:
    connect_server = os.environ.get("CONNECT_SERVER", "")
    if connect_server:
        parsed = urlparse(connect_server)
        host = (parsed.netloc or parsed.path).rstrip("/")
        if host:
            settings = TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=[host, f"{host}:*"],
            )
            logger.info("Transport security: allowed hosts %s", [host, f"{host}:*"])
            return settings
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


# --- Proxy call ---


def _make_proxy_fn(server_guid: str, tool_name: str, input_schema: dict | None) -> Any:
    """Create a proxy function with a proper signature for FastMCP."""
    params = []
    annotations: dict[str, Any] = {}
    schema_props = {}
    required_set: set[str] = set()

    if input_schema:
        schema_props = input_schema.get("properties", {})
        required_set = set(input_schema.get("required", []))

    for prop_name, prop_def in schema_props.items():
        json_type = prop_def.get("type", "string")
        py_type = _TYPE_MAP.get(json_type, Any)
        annotations[prop_name] = py_type

        if prop_name in required_set:
            params.append(
                inspect.Parameter(prop_name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            )
        else:
            default = prop_def.get("default", None)
            params.append(
                inspect.Parameter(
                    prop_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default,
                )
            )

    sig = inspect.Signature(params, return_annotation=Any)

    async def proxy_fn(**kwargs: Any) -> Any:
        return await _proxy_call(server_guid, tool_name, kwargs)

    proxy_fn.__signature__ = sig  # type: ignore[attr-defined]
    proxy_fn.__annotations__ = annotations
    proxy_fn.__name__ = tool_name
    proxy_fn.__qualname__ = tool_name

    return proxy_fn


def make_tool(
    server_guid: str,
    tool_name: str,
    input_schema: dict | None,
    description: str = "",
) -> McpTool:
    """Create an McpTool proxy — used as the ``tool_factory`` for UserToolStore."""
    proxy_fn = _make_proxy_fn(server_guid, tool_name, input_schema)
    return McpTool.from_function(
        proxy_fn,
        name=tool_name,
        description=description,
    )


# Module-level refs injected by ``init_mcp_server()``.
_db: Database | None = None
_connect: ConnectClient | None = None
_search_engine: SearchEngine | None = None
_user_store: UserToolStore | None = None


async def _proxy_call(
    server_guid: str, tool_name: str, arguments: dict[str, Any]
) -> Any:
    """Execute a tool on a backend MCP server."""
    assert _db is not None and _connect is not None

    visitor_key = _visitor_key()
    if not visitor_key:
        return {"error": "Visitor API key not available."}

    server = _db.get_server(server_guid)
    if server is None:
        return {"error": f"Server {server_guid} not found."}
    if not server.get("healthy"):
        return {"error": f"Server {server_guid} is currently unhealthy."}

    logger.info("Proxy call: %s on server %s", tool_name, server_guid)
    t0 = time.monotonic()
    try:
        result = await _connect.mcp_call_tool(
            content_url=server["content_url"],
            tool_name=tool_name,
            arguments=arguments,
            api_key=visitor_key,
        )
    except Exception:
        logger.exception("Error calling tool %s on server %s", tool_name, server_guid)
        return {"error": "Tool execution failed. Check gateway logs."}

    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info("Proxy call: %s completed (%.0fms)", tool_name, elapsed_ms)
    return result


# --- ToolManager override ---


def _override_tool_manager(mcp: FastMCP, user_store: UserToolStore):
    """Replace the FastMCP ToolManager with one that merges per-user tools."""

    original = mcp._tool_manager

    expected = {"get_tool", "list_tools", "add_tool", "remove_tool", "call_tool"}
    actual = {
        m
        for m in dir(original)
        if not m.startswith("_") and callable(getattr(original, m))
    }
    unexpected = actual - expected - {"__class__"}
    if unexpected:
        logger.warning(
            "ToolManager has unexpected methods %s — _UserToolManager may "
            "need updating. Check for MCP SDK changes.",
            unexpected,
        )

    class _UserToolManager:
        warn_on_duplicate_tools = original.warn_on_duplicate_tools

        def list_tools(self):
            permanent = original.list_tools()
            uguid = _user_guid()
            if uguid:
                user_tools = user_store.user_tools(uguid)
                try:
                    ctx = _server_request_ctx.get()
                    if ctx and ctx.session:
                        user_store.register_session(uguid, ctx.session)
                except LookupError:
                    pass
                logger.info(
                    "list_tools: user=%s permanent=%d user=%d",
                    uguid,
                    len(permanent),
                    len(user_tools),
                )
                return permanent + user_tools
            logger.info(
                "list_tools: no user context, returning %d permanent tools",
                len(permanent),
            )
            return permanent

        def get_tool(self, name):
            uguid = _user_guid()
            if uguid:
                tool = user_store.get_tool(uguid, name)
                if tool:
                    return tool
            return original.get_tool(name)

        async def call_tool(self, name, arguments, context, convert_result=False):
            uguid = _user_guid()
            if uguid:
                tool = user_store.get_tool(uguid, name)
                if tool:
                    return await tool.run(
                        arguments, context, convert_result=convert_result
                    )
            return await original.call_tool(
                name, arguments, context, convert_result=convert_result
            )

        def add_tool(self, *args, **kwargs):
            return original.add_tool(*args, **kwargs)

        def remove_tool(self, name):
            return original.remove_tool(name)

    mcp._tool_manager = _UserToolManager()


# --- Create + configure MCP server ---

mcp_server = FastMCP(
    "MCP Gateway",
    instructions=(
        "This is an MCP Gateway for a Posit Connect instance. "
        "IMPORTANT: At the start of every conversation, check your available tools. "
        "Use search_tools to find relevant tools, then add_tools to register the "
        "ones you need. Added tools become available in SUBSEQUENT prompts. "
        "Workflow: 1) search_tools to discover, 2) add_tools to register by name, "
        "3) use registered tools in the next prompt. "
        "If call_tool is available, you can use it as an immediate fallback to "
        "execute any discovered tool by passing server_guid and tool_name. "
        "Do NOT try to guess tool names — always search first."
    ),
    transport_security=_build_transport_security(),
)


# --- MCP tool definitions ---


@mcp_server.tool()
async def search_tools(
    query: str,
    limit: int = 10,
    ctx: Context = None,  # type: ignore[assignment]
) -> list[dict[str, Any]]:
    """Search for MCP tools across all servers on this Connect instance.

    Use this to find tools by describing what you need. After reviewing
    results, use add_tools to register the tools you want to use.

    Search tips:
    - Use short keywords: "add" or "weather" instead of full sentences.
    - Partial words work: "calc" matches "calculate", "calculator".

    Returns tool name, description, server_guid, and input schema for each match.
    """
    assert _search_engine is not None and _user_store is not None

    uguid = _user_guid()
    if uguid:
        logger.info("search_tools: user=%s query=%r", uguid, query)

    if ctx:
        await ctx.info(f"Searching for: {query}")

    t0 = time.monotonic()
    results = _search_engine.search(query, limit=limit)
    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "search_tools: %d results for query=%r (%.0fms)",
        len(results),
        query,
        elapsed_ms,
    )

    if ctx:
        if results:
            names = ", ".join(r["tool_name"] for r in results[:5])
            suffix = f" (and {len(results) - 5} more)" if len(results) > 5 else ""
            await ctx.info(f"Found {len(results)} tools: {names}{suffix}")
        else:
            await ctx.info("No tools found. Try different keywords.")

    if uguid and results:
        _user_store.cache_search_results(uguid, results)

    return results


@mcp_server.tool()
async def add_tools(
    tool_names: list[str],
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Register tools from search results into your tool list.

    After calling search_tools, pass the tool names you want to add.
    Added tools become callable in SUBSEQUENT prompts, not the current one.
    Tell the user which tools were added and that they're ready to use next.

    If call_tool is available, you can also use it as an immediate fallback.
    """
    assert _user_store is not None

    uguid = _user_guid()
    if not uguid:
        return {"error": "No user context available."}

    logger.info("add_tools: user=%s tools=%s", uguid, tool_names)

    if ctx:
        await ctx.info(f"Registering {len(tool_names)} tool(s)...")

    added = []
    skipped = []
    not_found = []

    async with _user_store._lock_for(uguid):
        existing = _user_store.user_tool_names(uguid)

        for name in tool_names:
            if name in PERMANENT_TOOLS:
                skipped.append(name)
                continue
            if name in existing:
                skipped.append(name)
                continue

            result = _user_store.get_cached_tool(uguid, name)
            if not result:
                not_found.append(name)
                continue

            server_guid = result["server_guid"]
            description = result.get("description", "")
            input_schema = result.get("input_schema")

            tool = make_tool(server_guid, name, input_schema, description)
            _user_store.add(
                uguid,
                name,
                server_guid,
                tool,
                description,
                input_schema,
            )
            added.append(name)
            logger.info("add_tools: added %r for user %s", name, uguid)

    if added:
        try:
            await ctx.session.send_tool_list_changed()
        except Exception:
            logger.warning("Failed to send tool_list_changed", exc_info=True)
        await _user_store.notify_user_sessions(
            uguid, except_session=ctx.session if ctx else None
        )

    if ctx:
        if added:
            await ctx.info(
                f"Added {len(added)} tool(s): {', '.join(added)}. "
                "They are available in your next prompt."
            )
        if not_found:
            await ctx.warning(
                f"Not found (search first): {', '.join(not_found)}"
            )

    return {"added": added, "skipped": skipped, "not_found": not_found}


@mcp_server.tool()
async def remove_tools(
    tool_names: list[str],
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Remove dynamically registered tools from your tool list.

    Pass a list of tool names to remove. Permanent tools (search_tools,
    add_tools, call_tool, remove_tools) cannot be removed. After removal,
    the tool list is updated so all your sessions see the change.
    """
    assert _user_store is not None

    uguid = _user_guid()
    if not uguid:
        return {"error": "No user context available."}

    logger.info("remove_tools: user=%s tools=%s", uguid, tool_names)

    removed = []
    skipped = []
    not_found = []

    async with _user_store._lock_for(uguid):
        for name in tool_names:
            if name in PERMANENT_TOOLS:
                skipped.append(name)
                continue
            if _user_store.remove(uguid, name):
                removed.append(name)
            else:
                not_found.append(name)

    if removed:
        try:
            await ctx.session.send_tool_list_changed()
        except Exception:
            logger.warning("Failed to send tool_list_changed", exc_info=True)
        await _user_store.notify_user_sessions(
            uguid, except_session=ctx.session if ctx else None
        )

    if ctx and removed:
        await ctx.info(f"Removed {len(removed)} tool(s): {', '.join(removed)}")

    return {"removed": removed, "skipped_permanent": skipped, "not_found": not_found}


# --- Conditional call_tool ---


async def _call_tool_fn(
    server_guid: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> Any:
    """Execute a tool on a backend MCP server.

    Use this as a fallback when direct tool calling is not available.
    Requires server_guid and tool_name from search_tools results.
    """
    return await _proxy_call(server_guid, tool_name, arguments or {})


_call_tool_registered = False


def sync_call_tool(enabled: bool):
    """Register or remove the call_tool based on the enabled setting."""
    global _call_tool_registered
    if enabled and not _call_tool_registered:
        mcp_server.add_tool(
            _call_tool_fn,
            name="call_tool",
            description=(
                "Execute a tool on a backend MCP server. Use this as a fallback "
                "when tools discovered via search_tools cannot be called directly. "
                "Requires server_guid and tool_name from search_tools results."
            ),
        )
        _call_tool_registered = True
        logger.info("call_tool registered")
    elif not enabled and _call_tool_registered:
        try:
            mcp_server.remove_tool("call_tool")
        except Exception:
            logger.warning("Failed to remove call_tool", exc_info=True)
        _call_tool_registered = False
        logger.info("call_tool removed")


# --- Public initialization ---


def init_mcp_server(
    db: Database,
    client: ConnectClient,
    search_engine: SearchEngine,
    user_store: UserToolStore,
):
    """Wire dependencies and apply the ToolManager override."""
    global _db, _connect, _search_engine, _user_store
    _db = db
    _connect = client
    _search_engine = search_engine
    _user_store = user_store
    _override_tool_manager(mcp_server, user_store)
