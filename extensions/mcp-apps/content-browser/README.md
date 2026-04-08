# Content Browser MCP App

FastMCP v3 MCP App server for searching and chatting with static content on Posit Connect. Searches Jupyter, Quarto, R Markdown, and other static content types via Connect's `/v1/search/content` API, then lets users browse results and send selected content to the LLM for discussion.

Uses visitor-scoped API access: when deployed on Connect, the `Posit-Connect-User-Session-Token` header is exchanged for a visitor API key so searches are scoped to what the visiting user can see.

## Tools

| Tool | Visibility | Description |
|---|---|---|
| `search_content` | LLM + app | Open the content browser, optionally with a pre-filled query |
| `do_search` | app-only | Execute a search against Connect's `/v1/search/content` API |
| `fetch_preview_html` | app-only | Fetch content HTML for in-app iframe preview |
| `fetch_content_html` | LLM + app | Fetch and extract content as markdown + images for LLM analysis |

## Prerequisites

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A running Posit Connect instance with static content
- A Connect API key

## Setup

```bash
cd extensions/mcp-apps/content-browser
uv venv
uv pip install -r requirements.txt
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `CONNECT_SERVER` | Yes | Connect server URL, e.g. `https://connect.example.com` |
| `CONNECT_API_KEY` | Yes (local) | Connect API key. On Connect this comes from the visitor session token. |
| `PORT` | No (default `3002`) | HTTP server port |

## Run locally

```bash
export CONNECT_SERVER=https://connect.example.com
export CONNECT_API_KEY=your-api-key
python main.py
# Server listening at http://localhost:3002
# MCP endpoint: http://localhost:3002/mcp
```

Open http://localhost:3002 to see the index page with endpoint info and tool descriptions.

## Test with basic-host

```bash
cd extensions/mcp-apps/basic-host
npm install
SERVERS='["http://localhost:3002/mcp"]' npm run start
```

Open http://localhost:8080. Click "search_content" to open the content browser. The app UI lets you:
- Search for static content items
- Preview content in an iframe (proxied through the server to avoid CORS)
- Click "Chat with Content" to fetch the full HTML and send it to the LLM for discussion

Or point Claude Desktop or VS Code at `http://localhost:3002/mcp`.

## Deploy to Posit Connect

Requires Posit Connect >= 2026.06.0 with MCP Apps support enabled.

```bash
rsconnect deploy fastapi \
  --server https://your-connect-server \
  --api-key YOUR_API_KEY \
  --entrypoint main:app \
  --title "Content Browser MCP App" \
  extensions/mcp-apps/content-browser/
```

When deployed, set the `CONNECT_SERVER` environment variable in the content settings to the Connect server URL. The visitor API key is injected automatically per-request via the `Posit-Connect-User-Session-Token` header — no `CONNECT_API_KEY` env var is needed in production.

## Architecture notes

- **Visitor scoping**: `_get_visitor_client()` exchanges the per-request `Posit-Connect-User-Session-Token` for a visitor `posit.connect.Client`. Search results and content proxy fetches are scoped to what the visiting user can see.
- **Content proxy**: `/proxy/{sid}/{path}` is an authenticated reverse proxy for iframe previews, keyed by a per-user session ID. Sub-resources (CSS, JS, images) load naturally via relative URLs through the same proxy path.
- **HTTPS vs HTTP inlining**: When the proxy URL is HTTPS, `fetch_preview_html` injects a `<base href>` and lets the browser load sub-resources directly. On HTTP (local dev), it inlines all CSS, JS, and images server-side to avoid mixed content blocks.
