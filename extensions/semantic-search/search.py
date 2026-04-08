"""Hybrid search combining LanceDB vector search with SQLite FTS5."""

from __future__ import annotations

from typing import Any

import lancedb

from database import Database
from embeddings import encode

TABLE_NAME = "content"
RRF_K = 60


class HybridSearch:
    def __init__(self, db: Database, lance_db: lancedb.DBConnection) -> None:
        self.db = db
        self.lance_db = lance_db

    @property
    def _table(self) -> lancedb.table.Table | None:
        try:
            if TABLE_NAME in self.lance_db.table_names():
                return self.lance_db.open_table(TABLE_NAME)
        except Exception:
            pass
        return None

    def search(
        self,
        query: str,
        limit: int = 20,
        app_mode: str | None = None,
        content_category: str | None = None,
        mode: str = "hybrid",
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return self.db.browse(limit, app_mode, content_category)

        if mode == "vector":
            ranked = self._vector_search(query, limit * 3)
            guids_scored = [(r["guid"], 1.0 - r["distance"]) for r in ranked]
        elif mode == "fts":
            ranked = self.db.search_fts(query, limit * 3, app_mode, content_category)
            guids_scored = [(r["guid"], -r["fts_rank"]) for r in ranked]
        else:
            vector_results = self._vector_search(query, limit * 3)
            fts_results = self.db.search_fts(
                query, limit * 3, app_mode, content_category
            )
            vector_guids = [r["guid"] for r in vector_results]
            fts_guids = [r["guid"] for r in fts_results]
            guids_scored = _rrf_merge(vector_guids, fts_guids)

        top_guids = [guid for guid, _ in guids_scored[: limit * 2]]
        content_map = {c["guid"]: c for c in self.db.get_content_batch(top_guids)}

        results = []
        for guid, score in guids_scored:
            if guid not in content_map:
                continue
            item = content_map[guid]
            if app_mode and item.get("app_mode") != app_mode:
                continue
            if content_category and item.get("content_category") != content_category:
                continue
            item["score"] = round(score, 4)
            results.append(item)
            if len(results) >= limit:
                break

        return results

    def _vector_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        table = self._table
        if table is None:
            return []
        try:
            query_vec = encode([query])[0].tolist()
            rows = table.search(query_vec).metric("cosine").limit(limit).to_list()
            return [{"guid": r["guid"], "distance": r["_distance"]} for r in rows]
        except Exception:
            return []


def _rrf_merge(
    vector_guids: list[str], fts_guids: list[str]
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for rank, guid in enumerate(vector_guids):
        scores[guid] = scores.get(guid, 0) + 1.0 / (RRF_K + rank + 1)
    for rank, guid in enumerate(fts_guids):
        scores[guid] = scores.get(guid, 0) + 1.0 / (RRF_K + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
