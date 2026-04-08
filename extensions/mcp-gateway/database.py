"""Local SQLite database for the MCP Gateway.

Stores watched tags, discovered servers, and tool metadata.
The PLAID index handles embeddings separately — this is the
structured metadata companion.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import log

logger = log.getLogger(__name__)

# Maximum length for search queries to prevent abuse.
_MAX_QUERY_LENGTH = 500


def _build_fts_query(raw: str) -> str:
    """Build a safe FTS5 query from raw user input.

    Strips special characters, quotes each term to prevent FTS5 syntax
    injection, and joins with OR (any term can match).  Each term also
    gets a prefix variant (``word*``) so partial matches work — e.g.
    "calc" matches "calculate", "calculator".

    Returns empty string if no usable terms remain.
    """
    # Remove everything except word characters and whitespace.
    cleaned = re.sub(r"[^\w\s]", " ", raw)
    words = cleaned.split()
    if not words:
        return ""
    # Each word matches as exact OR prefix.  Join terms with OR so
    # any matching term surfaces results, ranked by BM25.
    parts = []
    for w in words:
        parts.append(f'"{w}" OR {w}*')
    return " OR ".join(parts)


def sanitize_search_query(query: str, max_length: int = _MAX_QUERY_LENGTH) -> str:
    """Strip null bytes, control characters, and truncate to *max_length*."""
    # Remove null bytes and control chars (keep space, tab, newline).
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", query)
    return cleaned[:max_length]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS watched_tags (
    tag TEXT PRIMARY KEY,
    tag_id TEXT
);

CREATE TABLE IF NOT EXISTS discovered_servers (
    guid TEXT PRIMARY KEY,
    name TEXT,
    content_url TEXT,
    tag TEXT NOT NULL REFERENCES watched_tags(tag) ON DELETE CASCADE,
    healthy BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'pending',
    last_health_check DATETIME,
    last_indexed DATETIME,
    tool_count INTEGER DEFAULT 0,
    tools_hash TEXT,
    discovered_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tool_metadata (
    doc_id TEXT PRIMARY KEY,
    server_guid TEXT NOT NULL REFERENCES discovered_servers(guid) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    description TEXT,
    input_schema TEXT,
    schema_type TEXT DEFAULT 'tool',
    indexed_at DATETIME
);

CREATE TABLE IF NOT EXISTS gateway_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_tool_metadata_server
    ON tool_metadata(server_guid);

CREATE INDEX IF NOT EXISTS idx_discovered_servers_tag
    ON discovered_servers(tag);

CREATE TABLE IF NOT EXISTS user_tools (
    user_guid TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    server_guid TEXT NOT NULL,
    description TEXT DEFAULT '',
    input_schema TEXT DEFAULT '{}',
    added_at DATETIME DEFAULT (datetime('now')),
    PRIMARY KEY (user_guid, tool_name)
);

CREATE INDEX IF NOT EXISTS idx_user_tools_user
    ON user_tools(user_guid);

CREATE VIRTUAL TABLE IF NOT EXISTS tool_search USING fts5(
    doc_id UNINDEXED,
    tool_name,
    description
);
"""


class Database:
    """Thin wrapper around SQLite for gateway state."""

    def __init__(self, db_path: str | Path = "data/gateway.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        # Use DELETE journal mode — Connect's content storage is NFS-mounted
        # and WAL's shm/wal files cause disk I/O errors on network filesystems
        # even when the PRAGMA appears to succeed.
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _tx(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._tx() as conn:
            conn.executescript(_SCHEMA)

    # --- Watched tags ---

    def list_watched_tags(self) -> list[dict[str, Any]]:
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT tag, tag_id FROM watched_tags ORDER BY tag"
            ).fetchall()
        return [{"tag": r["tag"], "tag_id": r["tag_id"]} for r in rows]

    def add_watched_tag(self, tag: str, tag_id: str | None = None) -> None:
        with self._tx() as conn:
            conn.execute(
                """INSERT INTO watched_tags (tag, tag_id) VALUES (?, ?)
                   ON CONFLICT(tag) DO UPDATE SET tag_id = excluded.tag_id""",
                (tag, tag_id),
            )

    def remove_watched_tag(self, tag: str) -> None:
        with self._tx() as conn:
            conn.execute("DELETE FROM watched_tags WHERE tag = ?", (tag,))

    # --- Discovered servers ---

    def list_servers(self, tag: str | None = None) -> list[dict[str, Any]]:
        with self._tx() as conn:
            if tag:
                rows = conn.execute(
                    "SELECT * FROM discovered_servers WHERE tag = ? ORDER BY name",
                    (tag,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM discovered_servers ORDER BY name"
                ).fetchall()
        return [dict(r) for r in rows]

    def upsert_server(
        self,
        guid: str,
        name: str,
        content_url: str,
        tag: str,
    ) -> None:
        with self._tx() as conn:
            conn.execute(
                """INSERT INTO discovered_servers (guid, name, content_url, tag)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(guid) DO UPDATE SET
                       name = excluded.name,
                       content_url = excluded.content_url,
                       tag = excluded.tag""",
                (guid, name, content_url, tag),
            )

    def remove_servers_not_in(self, tag: str, guids: set[str]) -> list[str]:
        """Remove servers for a tag that are no longer discovered.

        Returns the GUIDs that were removed.
        """
        with self._tx() as conn:
            existing = conn.execute(
                "SELECT guid FROM discovered_servers WHERE tag = ?", (tag,)
            ).fetchall()
            removed = [r["guid"] for r in existing if r["guid"] not in guids]
            if removed:
                placeholders = ",".join("?" for _ in removed)
                conn.execute(
                    f"DELETE FROM discovered_servers WHERE guid IN ({placeholders})",
                    removed,
                )
        return removed

    def update_server_health(
        self, guid: str, healthy: bool, tool_count: int | None = None
    ) -> None:
        """Update health status. Also sets status to 'ready' or 'error'."""
        now = datetime.now(timezone.utc).isoformat()
        status = "ready" if healthy else "error"
        with self._tx() as conn:
            if tool_count is not None:
                conn.execute(
                    """UPDATE discovered_servers
                       SET healthy = ?, last_health_check = ?, tool_count = ?,
                           status = ?
                       WHERE guid = ?""",
                    (healthy, now, tool_count, status, guid),
                )
            else:
                conn.execute(
                    """UPDATE discovered_servers
                       SET healthy = ?, last_health_check = ?,
                           status = ?
                       WHERE guid = ?""",
                    (healthy, now, status, guid),
                )

    def update_server_indexed(self, guid: str, tools_hash: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._tx() as conn:
            conn.execute(
                """UPDATE discovered_servers
                   SET last_indexed = ?, tools_hash = ?
                   WHERE guid = ?""",
                (now, tools_hash, guid),
            )

    def set_server_indexing(self, guid: str) -> None:
        """Mark a server as currently being indexed."""
        with self._tx() as conn:
            conn.execute(
                "UPDATE discovered_servers SET status = 'indexing' WHERE guid = ?",
                (guid,),
            )

    def get_server(self, guid: str) -> dict[str, Any] | None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM discovered_servers WHERE guid = ?", (guid,)
            ).fetchone()
        return dict(row) if row else None

    # --- Tool metadata ---

    def upsert_tool(
        self,
        server_guid: str,
        tool_name: str,
        description: str | None,
        input_schema: str | None,
        schema_type: str = "tool",
    ) -> None:
        doc_id = f"{server_guid}:{tool_name}"
        now = datetime.now(timezone.utc).isoformat()
        with self._tx() as conn:
            conn.execute(
                """INSERT INTO tool_metadata
                       (doc_id, server_guid, tool_name, description, input_schema,
                        schema_type, indexed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(doc_id) DO UPDATE SET
                       description = excluded.description,
                       input_schema = excluded.input_schema,
                       schema_type = excluded.schema_type,
                       indexed_at = excluded.indexed_at""",
                (
                    doc_id,
                    server_guid,
                    tool_name,
                    description,
                    input_schema,
                    schema_type,
                    now,
                ),
            )

    def remove_tools_for_server(self, server_guid: str) -> None:
        with self._tx() as conn:
            conn.execute(
                "DELETE FROM tool_metadata WHERE server_guid = ?", (server_guid,)
            )

    def list_tools(self, server_guid: str | None = None) -> list[dict[str, Any]]:
        with self._tx() as conn:
            if server_guid:
                rows = conn.execute(
                    "SELECT * FROM tool_metadata WHERE server_guid = ? ORDER BY tool_name",
                    (server_guid,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tool_metadata ORDER BY tool_name"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_tool(self, server_guid: str, tool_name: str) -> dict[str, Any] | None:
        doc_id = f"{server_guid}:{tool_name}"
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM tool_metadata WHERE doc_id = ?", (doc_id,)
            ).fetchone()
        return dict(row) if row else None

    def rebuild_fts_index(self) -> int:
        """Rebuild the FTS5 full-text search index from tool_metadata.

        Clears the index and re-populates from the tool_metadata table.
        Returns the number of documents indexed.
        """
        with self._tx() as conn:
            conn.execute("DELETE FROM tool_search")
            conn.execute(
                """INSERT INTO tool_search (doc_id, tool_name, description)
                   SELECT doc_id, tool_name, COALESCE(description, '')
                   FROM tool_metadata"""
            )
            count = conn.execute("SELECT count(*) FROM tool_search").fetchone()[0]
        return count

    def search_tools_fts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Full-text search using FTS5 with BM25 ranking.

        Returns results joined with server metadata, ordered by relevance.
        Returns an empty list if the query is empty or FTS5 match fails.
        """
        query = sanitize_search_query(query)
        fts_query = _build_fts_query(query)
        if not fts_query:
            return []

        sql = (
            "SELECT tm.*, ds.name as server_name, ds.content_url, ds.healthy,"
            "       bm25(tool_search, 10.0, 1.0) as fts_rank"
            " FROM tool_search ts"
            " JOIN tool_metadata tm ON ts.doc_id = tm.doc_id"
            " JOIN discovered_servers ds ON tm.server_guid = ds.guid"
            " WHERE tool_search MATCH ? AND ds.status = 'ready'"
            " ORDER BY fts_rank"
            " LIMIT ?"
        )

        try:
            with self._tx() as conn:
                rows = conn.execute(sql, (fts_query, limit)).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.info("FTS5 search failed for query %r", query, exc_info=True)
            return []

    def search_tools_keyword(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Keyword search across tool names and descriptions.

        Splits the query into words and requires ANY word to match
        (in either the tool name or description).  Results are ranked
        by number of matching words, with tool_name matches boosted.

        Used as fallback when FTS5 search returns no results.
        """
        query = sanitize_search_query(query)
        words = query.split()
        if not words:
            return []

        # Build parameterized WHERE: any word must appear in name OR desc.
        word_clauses = []
        for _ in words:
            word_clauses.append("(tm.tool_name LIKE ? OR tm.description LIKE ?)")
        where_sql = " OR ".join(word_clauses)

        params: list[Any] = []
        for word in words:
            pattern = f"%{word}%"
            params.extend([pattern, pattern])

        # Score: count matching words, with name matches worth 2x.
        score_parts = []
        for _ in words:
            score_parts.append(
                "CASE WHEN tm.tool_name LIKE ? THEN 2"
                " WHEN tm.description LIKE ? THEN 1 ELSE 0 END"
            )
        score_sql = " + ".join(score_parts)

        for word in words:
            pattern = f"%{word}%"
            params.extend([pattern, pattern])

        params.append(limit)

        sql = (
            f"SELECT tm.*, ds.name as server_name, ds.content_url, ds.healthy,"
            f"       ({score_sql}) as match_score"
            " FROM tool_metadata tm"
            " JOIN discovered_servers ds ON tm.server_guid = ds.guid"
            f" WHERE ds.status = 'ready' AND ({where_sql})"
            " ORDER BY match_score DESC, tm.tool_name"
            " LIMIT ?"
        )

        with self._tx() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # --- Gateway settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a gateway setting value, returning default if not found."""
        with self._tx() as conn:
            row = conn.execute(
                "SELECT value FROM gateway_settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Set a gateway setting value."""
        with self._tx() as conn:
            conn.execute(
                """INSERT INTO gateway_settings (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                (key, value),
            )

    # --- User tools ---

    def list_user_tools(self, user_guid: str) -> list[dict[str, Any]]:
        """Return all saved tools for a user."""
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT tool_name, server_guid, description, input_schema "
                "FROM user_tools WHERE user_guid = ? ORDER BY added_at",
                (user_guid,),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_user_tool(
        self,
        user_guid: str,
        tool_name: str,
        server_guid: str,
        description: str,
        input_schema: str,
    ) -> None:
        """Persist a user tool (upsert)."""
        with self._tx() as conn:
            conn.execute(
                """INSERT INTO user_tools
                       (user_guid, tool_name, server_guid, description, input_schema)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_guid, tool_name) DO UPDATE SET
                       server_guid = excluded.server_guid,
                       description = excluded.description,
                       input_schema = excluded.input_schema""",
                (user_guid, tool_name, server_guid, description, input_schema),
            )

    def remove_user_tool(self, user_guid: str, tool_name: str) -> bool:
        """Remove a user tool. Returns True if a row was deleted."""
        with self._tx() as conn:
            cur = conn.execute(
                "DELETE FROM user_tools WHERE user_guid = ? AND tool_name = ?",
                (user_guid, tool_name),
            )
        return cur.rowcount > 0
