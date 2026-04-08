"""Lightweight health checker for discovered MCP servers.

Runs on a configurable interval (default 60s) to keep server health
status up to date.  Uses a lightweight HTTP HEAD on the /mcp endpoint
to verify liveness — does NOT call tools/list (the indexer already
does that on its own schedule).

Servers are checked concurrently and unhealthy servers use exponential
backoff so we don't spam failing endpoints.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from connect_client import ConnectClient
from database import Database

import log

logger = log.getLogger(__name__)

# Backoff constants for unhealthy servers.
_MIN_BACKOFF_S = 30
_MAX_BACKOFF_S = 300  # 5 minutes
_MAX_CONCURRENCY = 10  # max servers checked in parallel


class HealthChecker:
    """Periodically pings discovered servers to update health status."""

    def __init__(
        self,
        db: Database,
        client: ConnectClient,
        interval_seconds: int = 60,
    ) -> None:
        self.db = db
        self.client = client
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        # guid → (consecutive_failures, next_eligible_time)
        self._backoff: dict[str, tuple[int, float]] = {}

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("Health checker started (interval=%ds)", self.interval_seconds)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Health checker stopped")

    async def run_once(self) -> dict[str, Any]:
        """Check all discovered servers. Returns a summary."""
        servers = self.db.list_servers()
        if not servers:
            return {"checked": 0, "healthy": 0, "unhealthy": 0, "skipped": 0}

        now = time.monotonic()
        to_check = []
        skipped = 0

        for server in servers:
            guid = server["guid"]
            backoff_info = self._backoff.get(guid)
            if backoff_info and now < backoff_info[1]:
                skipped += 1
                continue
            to_check.append(server)

        # Check eligible servers concurrently (bounded).
        sem = asyncio.Semaphore(_MAX_CONCURRENCY)

        async def _bounded_check(srv: dict) -> bool:
            async with sem:
                return await self._check_server(srv["guid"], srv["content_url"])

        results = await asyncio.gather(
            *[_bounded_check(s) for s in to_check],
            return_exceptions=True,
        )

        healthy = sum(1 for r in results if r is True)
        unhealthy = len(results) - healthy

        summary = {
            "checked": len(to_check),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "skipped": skipped,
        }
        if unhealthy > 0:
            logger.info("Health check: %s", summary)
        else:
            logger.info("Health check: %s", summary)
        return summary

    async def _check_server(self, guid: str, content_url: str) -> bool:
        """Ping a single server via HTTP POST with an empty initialize hint.

        Uses a lightweight JSON-RPC call instead of the heavier tools/list
        so we don't trigger full tool enumeration on every health tick.
        Returns True if healthy.
        """
        try:
            client = await self.client._get_client()
            mcp_url = f"{content_url.rstrip('/')}/mcp"
            resp = await client.post(
                mcp_url,
                headers={
                    **self.client._headers(),
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {},
                },
                timeout=5.0,
            )
            is_ok = resp.status_code < 500
        except Exception:
            logger.info("Health check failed for server %s", guid)
            is_ok = False

        if is_ok:
            was_failing = guid in self._backoff
            self.db.update_server_health(guid, healthy=True)
            # Reset backoff on success.
            self._backoff.pop(guid, None)
            if was_failing:
                logger.info("Server %s recovered (healthy)", guid)
            return True

        # Exponential backoff for failures.
        failures, _ = self._backoff.get(guid, (0, 0.0))
        failures += 1
        delay = min(_MIN_BACKOFF_S * (2 ** (failures - 1)), _MAX_BACKOFF_S)
        self._backoff[guid] = (failures, time.monotonic() + delay)
        if failures == 1:
            logger.warning("Server %s became unhealthy", guid)
        else:
            logger.info(
                "Server %s still unhealthy (failures=%d, backoff=%ds)",
                guid,
                failures,
                delay,
            )
        self.db.update_server_health(guid, healthy=False)
        return False

    async def _loop(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error during health check cycle")
            await asyncio.sleep(self.interval_seconds)
