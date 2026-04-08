# Pins Data Viewer MCP App

FastMCP v3 MCP App server for browsing, exploring, and querying pin data on Posit Connect. Uses the `pins` Python SDK to list and search pins, then loads selected pin data into DuckDB for interactive column statistics, data preview, and SQL queries.

## Tools

| Tool | Visibility | Description |
|---|---|---|
| `browse_pins` | LLM + app | Open the pins data viewer, optionally with a pre-filled search query |
| `do_search` | app-only | Search for pins via the pins SDK |
| `load_pin` | app-only | Load a pin into DuckDB and return schema, stats, and 100-row preview |
| `query_pin` | app-only | Run a SQL query against the currently loaded pin (table name: `data`) |
| `analyze_pin_data` | LLM + app | Load a pin and return schema, summary stats, and 25-row sample for LLM analysis |

## Prerequisites

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A running Posit Connect instance with pins
- A Connect API key

## Setup

```bash
cd extensions/mcp-apps/pins-browser
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

Open http://localhost:8080. Click "browse_pins" to open the data viewer. The app UI lets you:
- Search for pins by name
- Select a pin to load it into DuckDB — see column types, min/max/mean, unique count, nulls
- Browse a 100-row data preview
- Run SQL queries against the loaded pin (`SELECT * FROM data WHERE ...`)
- Click "Chat with Data" to invoke `analyze_pin_data` and send schema + sample to the LLM

## Deploy to Posit Connect

Requires Posit Connect >= 2026.06.0 with MCP Apps support enabled.

```bash
rsconnect deploy fastapi \
  --server https://your-connect-server \
  --api-key YOUR_API_KEY \
  --entrypoint main:app \
  --title "Pins Data Viewer MCP App" \
  extensions/mcp-apps/pins-browser/
```

When deployed, set `CONNECT_SERVER` in content environment variables. The visitor API key is injected per-request via `Posit-Connect-User-Session-Token` — no `CONNECT_API_KEY` is needed in production.

## Architecture notes

- **DuckDB sessions**: `_pin_sessions` maps a per-user session key to `(pin_name, DataFrame)`. `load_pin` populates this; `query_pin` reads from it. Sessions are in-memory and lost on server restart.
- **Visitor scoping**: `_get_visitor_client()` uses the `Posit-Connect-User-Session-Token` header to create a visitor-scoped pins board, so pin searches respect the visiting user's access permissions.
- **SQL safety**: Queries run inside DuckDB against an in-memory DataFrame — no Connect data is modified. Results are capped at 1000 rows.
