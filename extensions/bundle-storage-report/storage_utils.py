"""Connect API calls and data shaping for the Bundle Storage Report.

Kept separate from the Shiny UI so the logic can be unit tested without a
Connect server.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable, Optional

import pandas as pd

# Columns of the report table, in display order.
COLUMNS = [
    "title",
    "type",
    "owner",
    "bundles",
    "total_mb",
    "active_mb",
    "inactive_mb",
    "retention_limit",
    "guid",
    "dashboard_url",
]

# Large pages and a few parallel requests keep a 10k-item server to a handful
# of round trips. If Connect caps page_size lower, total_pages still tells us
# how many pages to fetch.
STORAGE_PAGE_SIZE = 500
MAX_WORKERS = 6

# Only these fields of each content item are kept, so a 10k-item content
# list does not stay in memory at full size.
CONTENT_FIELDS = (
    "guid",
    "name",
    "title",
    "app_mode",
    "content_category",
    "bundle_retention_limit",
    "dashboard_url",
)


# --------------------------------------------------------------------------- #
# Connect API
# --------------------------------------------------------------------------- #
def fetch_server_storage(client) -> dict[str, Any]:
    """Server-wide bundle totals from GET /v1/system/storage."""
    return client.get("v1/system/storage").json().get("bundles", {})


def _storage_page(client, page: int) -> dict[str, Any]:
    return client.get(
        "v1/content/storage",
        params={"page_number": page, "page_size": STORAGE_PAGE_SIZE},
    ).json()


def fetch_content_storage(client) -> list[dict[str, Any]]:
    """Every page of GET /v1/content/storage, fetching pages 2..n in parallel."""
    first = _storage_page(client, 1)
    results: list[dict[str, Any]] = list(first.get("results", []))
    total_pages = int(first.get("total_pages") or 1)
    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            pages = pool.map(
                lambda n: _storage_page(client, n), range(2, total_pages + 1)
            )
            for body in pages:
                results.extend(body.get("results", []))
    return results


def _trim_content(item: dict[str, Any]) -> dict[str, Any]:
    out = {k: item.get(k) for k in CONTENT_FIELDS}
    owner = item.get("owner") or {}
    out["owner"] = {
        k: owner.get(k) for k in ("username", "first_name", "last_name")
    } if owner else None
    return out


def fetch_content(client) -> list[dict[str, Any]]:
    """GET /v1/content with owners, trimmed to the fields the report uses."""
    return [
        _trim_content(c)
        for c in client.get("v1/content", params={"include": "owner"}).json()
    ]


def load_all(client) -> tuple[dict[str, Any], pd.DataFrame]:
    """Fetch the three API sources concurrently and build the report."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        totals = pool.submit(fetch_server_storage, client)
        storage = pool.submit(fetch_content_storage, client)
        content = pool.submit(fetch_content, client)
        return totals.result(), build_report(storage.result(), content.result())


class ReportCache:
    """Process-wide cache of the last load, shared by every session.

    Only administrators get past the app's role check, and every administrator
    sees the same server-wide data, so sharing is safe. It saves each new
    session from reloading thousands of items.
    """

    def __init__(self, ttl_seconds: float = 600):
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self._value: Optional[tuple[dict[str, Any], pd.DataFrame]] = None
        self._loaded_at = 0.0

    def get(self, client, force: bool = False):
        """Return (totals, report, loaded_at), loading if stale or forced."""
        with self._lock:
            fresh = time.time() - self._loaded_at < self.ttl
            if self._value is None or force or not fresh:
                self._value = load_all(client)
                self._loaded_at = time.time()
            return (*self._value, self._loaded_at)

    def update_retention(self, guids: Iterable[str], label: str) -> None:
        """Record a retention change without reloading the whole server."""
        with self._lock:
            if self._value is not None:
                totals, df = self._value
                df = df.copy()
                df.loc[df["guid"].isin(list(guids)), "retention_limit"] = label
                self._value = (totals, df)

    def current(self):
        with self._lock:
            return None if self._value is None else (*self._value, self._loaded_at)


def set_retention_limit(client, guid: str, limit: Optional[int]) -> None:
    """PATCH one item's bundle_retention_limit. None reverts to the server default."""
    client.patch(f"v1/content/{guid}", json={"bundle_retention_limit": limit})


# --------------------------------------------------------------------------- #
# Shaping
# --------------------------------------------------------------------------- #
def to_mb(n: Optional[int]) -> float:
    return round((n or 0) / 1_000_000, 1)


def format_bytes(n: Optional[int]) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1000 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1000
    return f"{n:,.1f} TB"


def content_type_label(item: dict[str, Any]) -> str:
    """'pin', 'plot', 'site', 'mcp' when categorized, otherwise the app_mode."""
    return item.get("content_category") or item.get("app_mode") or "unknown"


def owner_label(item: dict[str, Any], fallback: Optional[str] = None) -> str:
    owner = item.get("owner") or {}
    name = f"{owner.get('first_name') or ''} {owner.get('last_name') or ''}".strip()
    username = owner.get("username") or fallback
    if name and username:
        return f"{name} ({username})"
    return name or username or "(deleted user)"


def retention_label(limit: Optional[int]) -> str:
    if limit is None:
        return "Server default"
    if limit == 0:
        return "Keep all"
    return str(limit)


def build_report(
    storage: Iterable[dict[str, Any]], content: Iterable[dict[str, Any]]
) -> pd.DataFrame:
    """Join storage aggregates with content metadata into one row per item.

    Content without any bundles appears with zero bytes; storage rows for items
    the content list did not return (unlikely) still appear using the storage
    endpoint's own name and owner.
    """
    storage_by_guid = {s["content_guid"]: s for s in storage}
    content_by_guid = {c["guid"]: c for c in content}

    rows = []
    for guid in content_by_guid.keys() | storage_by_guid.keys():
        c = content_by_guid.get(guid, {})
        s = storage_by_guid.get(guid, {})
        b = s.get("bundles") or {}
        rows.append(
            {
                "title": c.get("title")
                or c.get("name")
                or s.get("content_title")
                or s.get("content_name")
                or guid,
                "type": content_type_label(c or {"app_mode": s.get("app_mode")}),
                "owner": owner_label(c, fallback=s.get("owner_username")),
                "bundles": int(b.get("count") or 0),
                "total_mb": to_mb(b.get("bytes_total")),
                "active_mb": to_mb(b.get("bytes_active")),
                "inactive_mb": to_mb(b.get("bytes_inactive")),
                "retention_limit": retention_label(c.get("bundle_retention_limit")),
                "guid": guid,
                "dashboard_url": c.get("dashboard_url") or "",
                # Raw bytes kept for exact totals and sorting; not displayed.
                "_bytes_total": int(b.get("bytes_total") or 0),
                "_bytes_inactive": int(b.get("bytes_inactive") or 0),
            }
        )

    df = pd.DataFrame(rows, columns=COLUMNS + ["_bytes_total", "_bytes_inactive"])
    return df.sort_values("_bytes_total", ascending=False, kind="stable").reset_index(
        drop=True
    )


def filter_report(
    df: pd.DataFrame,
    pins_only: bool = False,
    types: Optional[list[str]] = None,
    search: str = "",
    sort_by: str = "_bytes_total",
    min_inactive_mb: float = 0,
) -> pd.DataFrame:
    out = df
    if pins_only:
        out = out[out["type"] == "pin"]
    elif types:
        out = out[out["type"].isin(types)]
    if min_inactive_mb:
        out = out[out["_bytes_inactive"] >= min_inactive_mb * 1_000_000]
    if search:
        s = search.strip().lower()
        out = out[
            out["title"].str.lower().str.contains(s, regex=False)
            | out["owner"].str.lower().str.contains(s, regex=False)
        ]
    ascending = sort_by == "title"
    return out.sort_values(sort_by, ascending=ascending, kind="stable").reset_index(
        drop=True
    )


def to_csv(df: pd.DataFrame) -> str:
    out = df.drop(columns=["_bytes_total", "_bytes_inactive"]).copy()
    out.insert(out.columns.get_loc("total_mb"), "total_bytes", df["_bytes_total"])
    out.insert(out.columns.get_loc("inactive_mb"), "inactive_bytes", df["_bytes_inactive"])
    return out.to_csv(index=False)
