"""Full-text search engine using SQLite FTS5.

Wraps the FTS5 virtual table in the gateway database for tool discovery.
Falls back to keyword (LIKE) search if FTS5 queries fail.
"""

from __future__ import annotations

import json
from typing import Any

from database import Database

import log

logger = log.getLogger(__name__)


class SearchEngine:
    """FTS5-based search over MCP tool names and descriptions.

    The FTS5 index lives in the same SQLite database as the tool metadata.
    Rebuilding is fast (milliseconds for hundreds of tools) since it's
    just DELETE + INSERT — no ML model or external index files.

    Falls back to SQLite LIKE-based keyword search if FTS5 match fails.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def rebuild(self) -> int:
        """Rebuild the FTS5 index from current tool_metadata.

        Returns the number of documents indexed.
        """
        count = self.db.rebuild_fts_index()
        logger.info("FTS5 index rebuilt with %d documents", count)
        return count

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for tools matching the query.

        Tries FTS5 first (BM25-ranked), falls back to keyword (LIKE).

        Returns a list of dicts with: server_guid, server_name,
        server_healthy, tool_name, description, input_schema, score.
        """
        logger.info("Search query=%r limit=%d", query, limit)

        # Try FTS5 first.
        results = self.db.search_tools_fts(query, limit=limit)
        if results:
            formatted = _format_results(results, source="fts5")
            logger.info(
                "Search results: %d hits via fts5 [%s]",
                len(formatted),
                ", ".join(r["tool_name"] for r in formatted),
            )
            return formatted

        # Keyword fallback.
        results = self.db.search_tools_keyword(query, limit=limit)
        formatted = _format_results(results, source="keyword")
        if formatted:
            logger.info(
                "Search results: %d hits via keyword fallback [%s]",
                len(formatted),
                ", ".join(r["tool_name"] for r in formatted),
            )
        else:
            logger.info("Search results: 0 hits for query=%r", query)
        return formatted


def _format_results(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    """Normalize DB rows into the search result format."""
    return [
        {
            "server_guid": r["server_guid"],
            "server_name": r.get("server_name", ""),
            "server_healthy": bool(r.get("healthy", False)),
            "tool_name": r["tool_name"],
            "description": r.get("description", ""),
            "input_schema": (
                json.loads(r["input_schema"]) if r.get("input_schema") else None
            ),
            "score": r.get("fts_rank") if source == "fts5" else None,
        }
        for r in rows
    ]
