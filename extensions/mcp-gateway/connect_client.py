"""HTTP client for the Connect server API.

Uses the extension's ephemeral API key (CONNECT_API_KEY) for discovery,
and the visitor API key for proxied tool execution.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import urllib.parse
from typing import Any

import time

import httpx

import log

logger = log.getLogger(__name__)

# Max response body size (10 MB) to prevent memory exhaustion from
# malicious or buggy backend servers.
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024

# Private/reserved IP networks that must never be targeted via proxy.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fd00::/8"),
    ipaddress.ip_network("fe80::/10"),
]


class McpError(Exception):
    """Structured MCP JSON-RPC error preserving code/message/data."""

    def __init__(
        self,
        message: str,
        code: int = -32000,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def validate_url(url: str, *, trusted_origin: str = "") -> None:
    """Validate that *url* is safe to proxy requests to.

    Rejects non-HTTP schemes, private/reserved IPs, and link-local
    addresses. Resolves the hostname to guard against DNS rebinding.

    If *trusted_origin* is set and *url* starts with it, the IP-block
    check is skipped — the gateway legitimately calls back to Connect
    content URLs on the same host.

    Raises ``ValueError`` if the URL is not allowed.
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    # Skip IP-block check for URLs on our own Connect server.
    if trusted_origin and url.startswith(trusted_origin):
        return

    # Resolve hostname to IP(s) and check every address.
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname {hostname!r}: {exc}") from exc

    for _family, _type, _proto, _canon, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                raise ValueError(f"URL resolves to blocked address {ip} (in {net})")


class ConnectClient:
    """Client for Connect's REST API and MCP server content URLs.

    Uses a shared ``httpx.AsyncClient`` for connection pooling so that
    health checks, indexing, and tool calls reuse TCP/TLS connections
    instead of opening a new one per request.
    """

    def __init__(
        self,
        server_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        raw_url = (server_url or os.environ.get("CONNECT_SERVER", "")).rstrip("/")
        self.server_url = raw_url
        # The Connect REST API lives under /__api__/.
        if raw_url and "/__api__" not in raw_url:
            self.api_url = f"{raw_url}/__api__"
        else:
            self.api_url = raw_url
        self.api_key = api_key or os.environ.get("CONNECT_API_KEY", "")

        # Shared client for connection pooling.  Created lazily because
        # httpx.AsyncClient must be instantiated inside a running loop
        # when using HTTP/2.
        self._client: httpx.AsyncClient | None = None
        # api_key → user GUID cache (avoids repeated /v1/user calls).
        self._user_guid_cache: dict[str, str] = {}

        if not self.server_url:
            logger.warning("CONNECT_SERVER not set — Connect API calls will fail")

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the shared ``httpx.AsyncClient``, creating it on first use."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                ),
            )
        return self._client

    async def close(self) -> None:
        """Close the shared HTTP client (call on shutdown)."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _headers(self, api_key: str | None = None) -> dict[str, str]:
        key = api_key or self.api_key
        headers: dict[str, str] = {}
        if key:
            headers["Authorization"] = f"Key {key}"
        return headers

    # --- Visitor token exchange ---

    async def exchange_visitor_token(self, user_session_token: str) -> str:
        """Exchange a user session token for a visitor API key.

        Uses Connect's OAuth token exchange (RFC 8693) to get an API key
        scoped to the visiting user. This is the async equivalent of
        ``posit.connect.Client.with_user_session_token()``.

        Returns the visitor API key string.
        Raises ``ValueError`` if the exchange fails.
        """
        client = await self._get_client()
        url = f"{self.api_url}/v1/oauth/integrations/credentials"
        logger.info("Exchanging visitor session token")
        t0 = time.monotonic()
        resp = await client.post(
            url,
            headers=self._headers(),
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token_type": "urn:posit:connect:user-session-token",
                "subject_token": user_session_token,
                "requested_token_type": "urn:posit:connect:api-key",
            },
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        resp.raise_for_status()
        result = resp.json()
        api_key = result.get("access_token", "")
        if not api_key:
            raise ValueError("Token exchange returned empty access_token")
        logger.info("Visitor token exchanged (%.0fms)", elapsed_ms)
        return api_key

    async def get_user_guid(self, api_key: str) -> str:
        """Return the GUID of the user who owns *api_key*.

        Calls GET /v1/user (returns the authenticated user) and caches
        the result for the lifetime of this client so subsequent calls
        for the same key don't hit the network.
        """
        cached = self._user_guid_cache.get(api_key)
        if cached:
            return cached

        client = await self._get_client()
        url = f"{self.api_url}/v1/user"
        resp = await client.get(url, headers=self._headers(api_key))
        resp.raise_for_status()
        guid = resp.json().get("guid", "")
        if not guid:
            raise ValueError("GET /v1/user returned empty guid")
        self._user_guid_cache[api_key] = guid
        return guid

    # --- Content discovery ---

    async def list_content_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Fetch content items that have a specific tag applied.

        Uses GET /v1/content with tag filtering.
        Falls back to name→ID resolution if no tag_id is provided.
        """
        logger.info("Resolving tag name %r to tag ID", tag)
        # First, resolve the tag name to a tag ID.
        tags = await self._get_tags()
        tag_id = None
        for t in tags:
            if t.get("name") == tag:
                tag_id = t.get("id")
                break

        if tag_id is None:
            logger.info("Tag %r not found on Connect instance", tag)
            return []

        return await self._list_content_with_tag_id(tag_id)

    async def list_content_by_tag_id(self, tag_id: str) -> list[dict[str, Any]]:
        """Fetch content items by Connect tag ID directly."""
        return await self._list_content_with_tag_id(tag_id)

    async def _list_content_with_tag_id(self, tag_id: str) -> list[dict[str, Any]]:
        """Fetch content items filtered by tag ID.

        Uses GET /v1/tags/{id}/content.
        """
        client = await self._get_client()
        url = f"{self.api_url}/v1/tags/{tag_id}/content"
        t0 = time.monotonic()
        resp = await client.get(url, headers=self._headers())
        elapsed_ms = (time.monotonic() - t0) * 1000
        resp.raise_for_status()
        items = resp.json()
        logger.info(
            "Listed %d content items for tag_id=%s (%.0fms)",
            len(items),
            tag_id,
            elapsed_ms,
        )
        return items

    async def _get_tags(self) -> list[dict[str, Any]]:
        client = await self._get_client()
        url = f"{self.api_url}/v1/tags"
        resp = await client.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def list_tags(self) -> list[dict[str, Any]]:
        """List all tags on the Connect instance."""
        return await self._get_tags()

    # --- MCP server introspection ---

    async def mcp_tools_list(
        self, content_url: str, api_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Call tools/list on an MCP server via its content URL.

        Uses MCP JSON-RPC 2.0 over Streamable HTTP.
        Returns the list of tools from the server's response.
        """
        mcp_url = f"{content_url.rstrip('/')}/mcp"
        validate_url(mcp_url, trusted_origin=self.server_url)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        logger.info("tools/list → %s", mcp_url)
        client = await self._get_client()
        t0 = time.monotonic()
        resp = await client.post(
            mcp_url,
            headers={
                **self._headers(api_key),
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json=payload,
            timeout=10.0,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        resp.raise_for_status()
        if len(resp.content) > _MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Response from {mcp_url} exceeds {_MAX_RESPONSE_BYTES} bytes"
            )

        # Guard against non-JSON responses (HTML error pages, empty bodies,
        # or non-MCP content that happens to be tagged).
        content_type = resp.headers.get("content-type", "")
        if not resp.content or not resp.content.strip():
            raise ValueError(
                f"Empty response from {mcp_url} — endpoint may not be an MCP server"
            )
        if "json" not in content_type and "text/event-stream" not in content_type:
            snippet = resp.text[:200]
            raise ValueError(
                f"Non-JSON response from {mcp_url} "
                f"(content-type: {content_type!r}): {snippet!r}"
            )

        result = resp.json()

        if "error" in result:
            err = result["error"]
            raise McpError(
                message=err.get("message", str(err)),
                code=err.get("code", -32000),
                data=err.get("data"),
            )

        tools = result.get("result", {}).get("tools", [])
        logger.info(
            "tools/list ← %s: %d tools (%.0fms)", mcp_url, len(tools), elapsed_ms
        )
        return tools

    async def mcp_call_tool(
        self,
        content_url: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        api_key: str | None = None,
    ) -> Any:
        """Call a specific tool on an MCP server via its content URL.

        Uses MCP JSON-RPC 2.0 over Streamable HTTP.
        """
        mcp_url = f"{content_url.rstrip('/')}/mcp"
        validate_url(mcp_url, trusted_origin=self.server_url)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        logger.info("tools/call %s → %s", tool_name, mcp_url)
        client = await self._get_client()
        t0 = time.monotonic()
        resp = await client.post(
            mcp_url,
            headers={
                **self._headers(api_key),
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json=payload,
            timeout=30.0,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        resp.raise_for_status()
        if len(resp.content) > _MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Response from {mcp_url} exceeds {_MAX_RESPONSE_BYTES} bytes"
            )

        content_type = resp.headers.get("content-type", "")
        if not resp.content or not resp.content.strip():
            raise ValueError(
                f"Empty response from {mcp_url} — endpoint may not be an MCP server"
            )
        if "json" not in content_type and "text/event-stream" not in content_type:
            snippet = resp.text[:200]
            raise ValueError(
                f"Non-JSON response from {mcp_url} "
                f"(content-type: {content_type!r}): {snippet!r}"
            )

        result = resp.json()

        if "error" in result:
            err = result["error"]
            raise McpError(
                message=err.get("message", str(err)),
                code=err.get("code", -32000),
                data=err.get("data"),
            )

        logger.info("tools/call %s ← %s: ok (%.0fms)", tool_name, mcp_url, elapsed_ms)
        return result.get("result")

    # --- Permission checks ---

    async def get_content_role(self, content_guid: str, api_key: str) -> str:
        """Get the user's app_role for a content item.

        Uses GET /v1/content/{guid} with the user's API key.
        Returns the app_role: "owner", "editor", "viewer", or "none".
        Returns "viewer" on any error (fail closed).
        """
        client = await self._get_client()
        url = f"{self.api_url}/v1/content/{content_guid}"
        try:
            logger.info("Getting content role for %s", content_guid)
            resp = await client.get(url, headers=self._headers(api_key))
            resp.raise_for_status()
            data = resp.json()
            role = data.get("app_role", "viewer")
            logger.info("Content role for %s: %s", content_guid, role)
            return role
        except Exception:
            logger.warning(
                "Failed to get content role for %s, defaulting to viewer",
                content_guid,
                exc_info=True,
            )
            return "viewer"

    # --- Content URL resolution ---

    def content_url(self, guid: str) -> str:
        """Build the content URL for a given GUID."""
        return f"{self.server_url}/content/{guid}"
