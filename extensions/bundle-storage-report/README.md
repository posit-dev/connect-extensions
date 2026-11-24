# Bundle Storage Report

A Shiny for Python dashboard that shows which content on your Posit Connect
server uses the most bundle storage, with a focus on **pins**, where every
version is stored as a separate bundle. Administrators can then set a bundle
retention limit on many content items at once instead of one at a time.

## Features

**Reporting**

- Server-wide totals: total, inactive (reclaimable), and pin bundle storage.
- One row per content item: bundle count and total, active, and inactive
  storage.
- A **Pins only** switch (`content_category == "pin"`), a content type filter,
  a minimum inactive storage filter, and search by title or owner (press
  Enter to search).
- Sort by total storage, inactive storage, bundle count, or title.
- The table shows the top 100, 250, or 500 items of the current view. A note
  above it gives the full count and inactive total for everything that
  matches; **Export CSV** includes every matching item.
- The owner of each item, so you can contact publishers about moving very large
  pins to more suitable storage.
- Each item's current retention limit: a number, **Keep all** (`0`), or
  **Server default** (inherits
  [`Applications.BundleRetentionLimit`](https://docs.posit.co/connect/admin/appendix/configuration/#Applications.BundleRetentionLimit)).
- A chart of the ten items with the most inactive storage in the current view.
- **Export CSV** of the current view, with exact byte counts.

**Actions**

- Choose a limit (keep N inactive bundles, keep all, or use the server
  default) and apply it to either the **selected rows** or **all items matching
  the filters**, for example every pin with more than 1 GB of inactive
  bundles. The app asks for confirmation first, and for 100 or more items you
  type the item count to confirm. Updates run 8 at a time with a progress bar.
- The **Selected items** card links each selected item to its page in the
  Connect dashboard, where you can adjust its retention limit by hand.

Lowering a retention limit lets Connect delete older inactive bundles, so
those versions (for pins, older pin versions) can no longer be restored. The
active bundle is always kept. Storage totals go down once Connect's bundle
cleanup has removed the bundles.

## Requirements

- Posit Connect **2026.10.0** or later (per-content `bundle_retention_limit`).
- The **OAuth Integrations** feature, with a *Connect Visitor API Key*
  integration.
- Viewers must have the **Administrator** role. Other viewers see a message
  instead of the report.

## Setup

1. Install the extension from the Connect Gallery.
2. In the content's settings, open the **Runtime** tab (**Access** before
   Connect 2026.08.0) and add the **Connect Visitor API Key** integration under
   **Integrations**. See
   [Obtaining a Visitor API Key](https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key).
3. Limit access to administrators (recommended).

The app always acts as the signed-in viewer, never with the publisher's API
key, so every change is made with the viewer's own permissions and appears
under their name in the Connect audit log.

## How it works

| Purpose | Connect API |
| --- | --- |
| Server totals | `GET /v1/system/storage` |
| Storage per item | `GET /v1/content/storage` (paginated) |
| Category, owner, retention limit, URL | `GET /v1/content?include=owner` |
| Set the retention limit | `PATCH /v1/content/{guid}` with `bundle_retention_limit` |

The storage endpoints require the `system:storage` permission, which only the
Administrator role has by default.

### Large servers

The report is built for servers with thousands of content items:

- Storage pages are fetched 500 at a time, several in parallel, alongside the
  content list. Only the fields the report needs are kept in memory.
- Loading runs in a background task, so the page stays responsive and shows
  a loading message.
- The loaded data is cached for the whole app process (10 minutes by default)
  and shared by all administrator sessions. **Reload from Connect** fetches
  fresh data. Set the `CACHE_TTL_SECONDS` environment variable to change how
  long the cache lasts.
- Filtering, sorting, and totals run on the server. The browser only receives
  the rows shown in the table.
- After a bulk change, the app updates the cached retention limits directly
  instead of reloading every item. Storage totals go down later, after Connect's
  bundle cleanup runs; use **Reload from Connect** to see them.

## Local development

```bash
uv sync
export CONNECT_SERVER=https://connect.example.com
export CONNECT_API_KEY=<an administrator's API key>
uv run shiny run --reload app.py
uv run pytest
```

Outside Connect, the app uses `CONNECT_SERVER` and `CONNECT_API_KEY`. On
Connect, it uses only the Visitor API Key integration.
