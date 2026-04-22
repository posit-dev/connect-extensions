"""SQLite database for content metadata and FTS5 full-text search."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_MAX_QUERY_LENGTH = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS content (
    guid TEXT PRIMARY KEY,
    name TEXT,
    title TEXT,
    description TEXT,
    app_mode TEXT,
    content_category TEXT,
    access_type TEXT,
    owner_guid TEXT,
    owner_username TEXT,
    owner_first_name TEXT,
    owner_last_name TEXT,
    content_url TEXT,
    dashboard_url TEXT,
    vanity_url TEXT,
    tags TEXT,
    tags_text TEXT,
    r_version TEXT,
    py_version TEXT,
    quarto_version TEXT,
    created_time TEXT,
    last_deployed_time TEXT,
    bundle_id TEXT,
    checksum TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_content_app_mode ON content(app_mode);
CREATE INDEX IF NOT EXISTS idx_content_category ON content(content_category);

CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
    guid UNINDEXED,
    title,
    name,
    description,
    owner_name,
    tags_text
);
"""


def _build_fts_query(raw: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", raw)
    words = cleaned.split()
    if not words:
        return ""
    parts = []
    for w in words:
        parts.append(f'"{w}" OR {w}*')
    return " OR ".join(parts)


def _sanitize_query(query: str, max_length: int = _MAX_QUERY_LENGTH) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", query)
    return cleaned[:max_length]


class Database:
    def __init__(self, db_path: str | Path = "data/search.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
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

    def upsert_content(self, item: dict[str, Any], checksum: str) -> None:
        owner = item.get("owner") or {}
        tags = item.get("tags") or []
        tags_json = json.dumps(tags, default=str)
        tag_names = [t.get("name", "") for t in tags if t.get("name")]
        tags_text = ", ".join(tag_names)

        with self._tx() as conn:
            conn.execute(
                """INSERT INTO content (
                    guid, name, title, description, app_mode, content_category,
                    access_type, owner_guid, owner_username, owner_first_name,
                    owner_last_name, content_url, dashboard_url, vanity_url,
                    tags, tags_text, r_version, py_version, quarto_version,
                    created_time, last_deployed_time, bundle_id, checksum
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(guid) DO UPDATE SET
                    name=excluded.name, title=excluded.title,
                    description=excluded.description, app_mode=excluded.app_mode,
                    content_category=excluded.content_category,
                    access_type=excluded.access_type, owner_guid=excluded.owner_guid,
                    owner_username=excluded.owner_username,
                    owner_first_name=excluded.owner_first_name,
                    owner_last_name=excluded.owner_last_name,
                    content_url=excluded.content_url,
                    dashboard_url=excluded.dashboard_url,
                    vanity_url=excluded.vanity_url, tags=excluded.tags,
                    tags_text=excluded.tags_text, r_version=excluded.r_version,
                    py_version=excluded.py_version,
                    quarto_version=excluded.quarto_version,
                    created_time=excluded.created_time,
                    last_deployed_time=excluded.last_deployed_time,
                    bundle_id=excluded.bundle_id, checksum=excluded.checksum""",
                (
                    item.get("guid"), item.get("name"), item.get("title"),
                    item.get("description"), item.get("app_mode"),
                    item.get("content_category"), item.get("access_type"),
                    owner.get("guid"), owner.get("username"),
                    owner.get("first_name"), owner.get("last_name"),
                    item.get("content_url"), item.get("dashboard_url"),
                    item.get("vanity_url"), tags_json, tags_text,
                    item.get("r_version"), item.get("py_version"),
                    item.get("quarto_version"),
                    str(item["created_time"]) if item.get("created_time") else None,
                    str(item["last_deployed_time"]) if item.get("last_deployed_time") else None,
                    item.get("bundle_id"), checksum,
                ),
            )

    def delete_content(self, guid: str) -> None:
        with self._tx() as conn:
            conn.execute("DELETE FROM content WHERE guid = ?", (guid,))

    def get_checksums(self) -> dict[str, str]:
        with self._tx() as conn:
            rows = conn.execute("SELECT guid, checksum FROM content").fetchall()
        return {r["guid"]: r["checksum"] for r in rows}

    def get_content_batch(self, guids: list[str]) -> list[dict[str, Any]]:
        if not guids:
            return []
        placeholders = ",".join("?" for _ in guids)
        with self._tx() as conn:
            rows = conn.execute(
                f"SELECT * FROM content WHERE guid IN ({placeholders})", guids
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("tags"):
                try:
                    d["tags"] = json.loads(d["tags"])
                except (json.JSONDecodeError, TypeError):
                    d["tags"] = []
            else:
                d["tags"] = []
            result.append(d)
        return result

    def browse(
        self,
        limit: int = 20,
        app_mode: str | None = None,
        content_category: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if app_mode:
            clauses.append("app_mode = ?")
            params.append(app_mode)
        if content_category:
            clauses.append("content_category = ?")
            params.append(content_category)
        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)
        params.append(limit)
        with self._tx() as conn:
            rows = conn.execute(
                f"SELECT * FROM content {where} ORDER BY last_deployed_time DESC LIMIT ?",
                params,
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("tags"):
                try:
                    d["tags"] = json.loads(d["tags"])
                except (json.JSONDecodeError, TypeError):
                    d["tags"] = []
            else:
                d["tags"] = []
            result.append(d)
        return result

    def get_distinct_values(self, column: str) -> list[str]:
        allowed = {"app_mode", "content_category"}
        if column not in allowed:
            return []
        with self._tx() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT {column} FROM content "
                f"WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
            ).fetchall()
        return [r[0] for r in rows]

    def rebuild_fts(self) -> int:
        with self._tx() as conn:
            conn.execute("DELETE FROM content_fts")
            conn.execute(
                """INSERT INTO content_fts (guid, title, name, description, owner_name, tags_text)
                   SELECT
                       guid,
                       COALESCE(title, ''),
                       COALESCE(name, ''),
                       COALESCE(description, ''),
                       TRIM(COALESCE(owner_first_name, '') || ' ' || COALESCE(owner_last_name, '')),
                       COALESCE(tags_text, '')
                   FROM content"""
            )
            count = conn.execute("SELECT count(*) FROM content_fts").fetchone()[0]
        return count

    def search_fts(
        self,
        query: str,
        limit: int = 20,
        app_mode: str | None = None,
        content_category: str | None = None,
    ) -> list[dict[str, Any]]:
        query = _sanitize_query(query)
        fts_query = _build_fts_query(query)
        if not fts_query:
            return []

        extra_where = ""
        params: list[Any] = [fts_query]
        if app_mode:
            extra_where += " AND c.app_mode = ?"
            params.append(app_mode)
        if content_category:
            extra_where += " AND c.content_category = ?"
            params.append(content_category)
        params.append(limit)

        sql = (
            "SELECT c.guid, bm25(content_fts, 10.0, 5.0, 3.0, 2.0, 2.0) as fts_rank"
            " FROM content_fts f"
            " JOIN content c ON f.guid = c.guid"
            f" WHERE content_fts MATCH ?{extra_where}"
            " ORDER BY fts_rank"
            " LIMIT ?"
        )

        try:
            with self._tx() as conn:
                rows = conn.execute(sql, params).fetchall()
            return [{"guid": r["guid"], "fts_rank": r["fts_rank"]} for r in rows]
        except Exception:
            return []

    def content_count(self) -> int:
        with self._tx() as conn:
            return conn.execute("SELECT count(*) FROM content").fetchone()[0]

    def clear_all(self) -> None:
        """Drop every indexed row so the next cycle re-embeds from scratch.

        Used by the indexer's heal path when LanceDB is detected as corrupt.
        """
        with self._tx() as conn:
            conn.execute("DELETE FROM content")
            conn.execute("DELETE FROM content_fts")
