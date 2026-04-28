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
        interval_seconds: int = 60,
    ) -> None:
        self.db = db
        self.lance_db = lance_db
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_run: str | None = None
        self._last_result: dict[str, Any] | None = None
        # Heal runs at most once per process, on the first indexing cycle.
        self._healed = False

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
        # Re-entrancy guard: a manual /reindex click while the background loop
        # is mid-cycle would otherwise produce concurrent _do_index runs, which
        # is exactly how the duplicate-row bug accumulates. Single-threaded
        # asyncio makes this check-then-set safe.
        if self._running:
            return {"skipped": "already running"}
        self._running = True
        try:
            return await asyncio.to_thread(self._do_index)
        finally:
            self._running = False
            self._last_run = datetime.now(timezone.utc).isoformat()

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

    def _do_index(self) -> dict[str, Any]:
        print("[indexer] Starting indexing cycle...")

        # Ensure model is loaded
        get_model()

        # One-time consistency check between SQLite and LanceDB. If a prior
        # process left the index corrupt (duplicates / orphans / missing), this
        # wipes both stores so the same cycle rebuilds from scratch. Set the
        # flag only on success so a partial failure retries next cycle instead
        # of being silently skipped.
        if not self._healed:
            self._heal_lance_duplicates()
            self._healed = True

        # Fetch all content from Connect
        client = Client()
        print(f"[indexer] Connected to: {client.cfg.url}")

        content_items = client.content.find(include=["owner", "tags", "vanity_url"])
        # Skip undeployed stubs: bundle_id is null for content that never had a
        # successful upload, and app_mode is "unknown" until a bundle is
        # promoted. Connect's own /v1/content endpoint returns these but they
        # 404 on open, so they must not enter the search index.
        items = [
            dict(item) for item in content_items
            if item.get("bundle_id") and item.get("app_mode") != "unknown"
        ]
        print(f"[indexer] Fetched {len(items)} deployable content items")

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

        # Process new and changed items. Order matters: embed first (pure
        # computation), then LanceDB delete+add, and only commit SQLite
        # checksums AFTER LanceDB succeeds. If the cycle crashes mid-way the
        # checksum is not updated, so next cycle re-classifies the item as
        # changed and retries — preventing "SQLite says current, LanceDB
        # missing vectors" drift.
        items_to_embed = new_items + changed_items
        if items_to_embed:
            texts = [content_to_text(item) for item, _ in items_to_embed]
            guids = [item["guid"] for item, _ in items_to_embed]
            print(f"[indexer] Encoding {len(texts)} documents...")
            vectors = encode(texts, show_progress=True)

            changed_guids = [item["guid"] for item, _ in changed_items]
            if changed_guids:
                self._lance_delete(changed_guids)

            records = [
                {"guid": guid, "vector": vec.tolist(), "text": text}
                for guid, vec, text in zip(guids, vectors, texts)
            ]
            self._lance_add(records)

            for item, checksum in items_to_embed:
                self.db.upsert_content(item, checksum)

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
        # Like _lance_delete, errors propagate. Swallowing them was how we
        # ended up with SQLite claiming items are indexed while LanceDB has
        # no vectors for them.
        if not records:
            return
        if TABLE_NAME in self.lance_db.table_names():
            table = self.lance_db.open_table(TABLE_NAME)
            table.add(records)
        else:
            self.lance_db.create_table(TABLE_NAME, data=records, schema=_LANCE_SCHEMA)

    def _lance_delete(self, guids: list[str]) -> None:
        # Let exceptions propagate: a failed delete followed by an add is how
        # duplicate rows accumulated in the first place. The cycle-level
        # handler in _loop() will log and we'll retry next interval.
        if not guids:
            return
        if TABLE_NAME not in self.lance_db.table_names():
            return
        table = self.lance_db.open_table(TABLE_NAME)
        guid_list = ", ".join(f"'{g}'" for g in guids)
        table.delete(f"guid IN ({guid_list})")

    def _heal_lance_duplicates(self) -> None:
        """Repair the index if SQLite and LanceDB are out of sync.

        Three ways to be corrupt:
          - duplicates: a guid has >1 vector row
          - orphans:    a vector row's guid is not in SQLite
          - missing:    a SQLite row has no vector (empty/dropped LanceDB)

        Any of those means vector search silently returns stale or incomplete
        results, so we wipe both stores and let the next cycle rebuild from the
        Connect API. The operation is idempotent — if it partially fails (drop
        succeeds, clear_all raises), the next call redoes whatever is needed.
        """
        sqlite_guids = set(self.db.get_checksums().keys())
        lance_has_table = TABLE_NAME in self.lance_db.table_names()

        duplicates = 0
        lance_guids: set[str] = set()
        if lance_has_table:
            try:
                table = self.lance_db.open_table(TABLE_NAME)
                rows = table.to_pandas()[["guid"]]
                guid_counts = rows["guid"].value_counts()
                duplicates = int((guid_counts > 1).sum())
                lance_guids = set(guid_counts.index.tolist())
            except Exception as e:
                print(f"[indexer] Heal: could not inspect LanceDB table: {e}")
                return

        orphans = len(lance_guids - sqlite_guids)
        missing = len(sqlite_guids - lance_guids)

        if duplicates == 0 and orphans == 0 and missing == 0:
            return

        print(
            f"[indexer] Detected corrupt index "
            f"({duplicates} duplicates, {orphans} orphans, {missing} missing) "
            f"— rebuilding from scratch"
        )
        if lance_has_table:
            self.lance_db.drop_table(TABLE_NAME)
        self.db.clear_all()


def _compute_checksum(item: dict[str, Any]) -> str:
    """Hash only the fields that affect embedding text or displayed metadata.

    Excludes volatile fields like ``bundle_id`` and ``last_deployed_time`` so a
    pure redeploy does not trigger a re-embed. The guid is the row identity and
    is intentionally NOT part of the checksum — a rename still flows through
    because ``title``/``name`` change.
    """
    owner = item.get("owner") or {}
    tags = item.get("tags") or []
    tag_names = sorted(t.get("name", "") for t in tags if t.get("name"))
    relevant = {
        "title": item.get("title"),
        "name": item.get("name"),
        "description": item.get("description"),
        "app_mode": item.get("app_mode"),
        "content_category": item.get("content_category"),
        "access_type": item.get("access_type"),
        "owner_username": owner.get("username"),
        "owner_first_name": owner.get("first_name"),
        "owner_last_name": owner.get("last_name"),
        "tags": tag_names,
        "vanity_url": item.get("vanity_url"),
        # Version fields feed content_to_text; omitting them would make a
        # runtime upgrade invisible to vector search.
        "r_version": item.get("r_version"),
        "py_version": item.get("py_version"),
        "quarto_version": item.get("quarto_version"),
    }
    serialized = json.dumps(relevant, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
