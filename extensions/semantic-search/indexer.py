"""Background indexer for Posit Connect content metadata.

Runs on a configurable interval to:
1. Fetch all content metadata from Connect API
2. Detect changes via SHA-256 checksums
3. Embed new/changed items with MiniLM
4. Store in LanceDB (vectors) and SQLite (metadata + FTS5)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import lancedb
import pyarrow as pa
from posit.connect import Client

from database import Database
from embeddings import content_to_text, encode, get_model

TABLE_NAME = "content"

_LANCE_SCHEMA = pa.schema([
    pa.field("guid", pa.utf8()),
    pa.field("vector", pa.list_(pa.float32(), 384)),
    pa.field("text", pa.utf8()),
])


class Indexer:
    def __init__(
        self,
        db: Database,
        lance_db: lancedb.DBConnection,
        interval_seconds: int = 1800,
    ) -> None:
        self.db = db
        self.lance_db = lance_db
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_run: str | None = None
        self._last_result: dict[str, Any] | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())
        print(f"[indexer] Background indexer started (interval={self.interval_seconds}s)")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            print("[indexer] Background indexer stopped")

    async def run_once(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._sync_index)

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "last_run": self._last_run,
            "last_result": self._last_result,
            "content_count": self.db.content_count(),
            "interval_seconds": self.interval_seconds,
        }

    async def _loop(self) -> None:
        await asyncio.sleep(2)
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[indexer] Error during indexing cycle: {e}")
            await asyncio.sleep(self.interval_seconds)

    def _sync_index(self) -> dict[str, Any]:
        self._running = True
        try:
            return self._do_index()
        finally:
            self._running = False
            self._last_run = datetime.now(timezone.utc).isoformat()

    def _do_index(self) -> dict[str, Any]:
        print("[indexer] Starting indexing cycle...")

        # Ensure model is loaded
        get_model()

        # Fetch all content from Connect
        client = Client()
        print(f"[indexer] Connected to: {client.cfg.url}")

        content_items = client.content.find(include=["owner", "tags", "vanity_url"])
        items = [dict(item) for item in content_items]
        print(f"[indexer] Fetched {len(items)} content items")

        # Detect changes
        existing_checksums = self.db.get_checksums()
        api_guids = set()
        new_items = []
        changed_items = []
        unchanged_count = 0

        for item in items:
            guid = item["guid"]
            api_guids.add(guid)
            checksum = _compute_checksum(item)

            if guid not in existing_checksums:
                new_items.append((item, checksum))
            elif existing_checksums[guid] != checksum:
                changed_items.append((item, checksum))
            else:
                unchanged_count += 1

        removed_guids = set(existing_checksums.keys()) - api_guids

        print(
            f"[indexer] New: {len(new_items)}, Changed: {len(changed_items)}, "
            f"Unchanged: {unchanged_count}, Removed: {len(removed_guids)}"
        )

        if not new_items and not changed_items and not removed_guids:
            print("[indexer] No changes detected, skipping")
            result = {"new": 0, "changed": 0, "removed": 0, "unchanged": unchanged_count}
            self._last_result = result
            return result

        # Remove deleted content
        for guid in removed_guids:
            self.db.delete_content(guid)
        if removed_guids:
            self._lance_delete(list(removed_guids))

        # Process new and changed items
        items_to_embed = new_items + changed_items
        if items_to_embed:
            # Update SQLite
            for item, checksum in items_to_embed:
                self.db.upsert_content(item, checksum)

            # Embed and upsert into LanceDB
            texts = [content_to_text(item) for item, _ in items_to_embed]
            guids = [item["guid"] for item, _ in items_to_embed]
            print(f"[indexer] Encoding {len(texts)} documents...")
            vectors = encode(texts, show_progress=True)

            # Delete old vectors for changed items
            changed_guids = [item["guid"] for item, _ in changed_items]
            if changed_guids:
                self._lance_delete(changed_guids)

            # Add new vectors
            records = [
                {"guid": guid, "vector": vec.tolist(), "text": text}
                for guid, vec, text in zip(guids, vectors, texts)
            ]
            self._lance_add(records)

        # Rebuild FTS5 index
        fts_count = self.db.rebuild_fts()
        print(f"[indexer] FTS5 index rebuilt with {fts_count} documents")

        result = {
            "new": len(new_items),
            "changed": len(changed_items),
            "removed": len(removed_guids),
            "unchanged": unchanged_count,
        }
        self._last_result = result
        print(f"[indexer] Indexing cycle complete: {result}")
        return result

    def _lance_add(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        try:
            if TABLE_NAME in self.lance_db.table_names():
                table = self.lance_db.open_table(TABLE_NAME)
                table.add(records)
            else:
                self.lance_db.create_table(TABLE_NAME, data=records, schema=_LANCE_SCHEMA)
        except Exception as e:
            print(f"[indexer] LanceDB add error: {e}")

    def _lance_delete(self, guids: list[str]) -> None:
        if not guids:
            return
        try:
            if TABLE_NAME not in self.lance_db.table_names():
                return
            table = self.lance_db.open_table(TABLE_NAME)
            guid_list = ", ".join(f"'{g}'" for g in guids)
            table.delete(f"guid IN ({guid_list})")
        except Exception as e:
            print(f"[indexer] LanceDB delete error: {e}")


def _compute_checksum(item: dict[str, Any]) -> str:
    serialized = json.dumps(item, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
