# MCP Gateway

Single MCP endpoint for discovering and executing tools across all MCP servers on a Posit Connect instance.

## How it works

LLMs connect to one MCP endpoint (`/mcp`) and use two meta-tools:

- **`search_tools(query)`** — find tools by describing what you need in natural language
- **`call_tool(server_guid, tool_name, arguments)`** — execute a tool on a backend MCP server

The gateway discovers MCP servers via **watched tags** — admin-configured tags in Connect's tag system. Any content with a matching tag is automatically discovered, health-checked, and indexed.

## Architecture

```
LLM / Agent
    │
    ▼  MCP protocol (tools/list → search_tools, call_tool)
┌─────────────────────────────────────────┐
│  MCP Gateway Extension                  │
│  ├── /mcp          MCP endpoint         │
│  ├── /api/*        Admin REST API       │
│  ├── /             Registry UI          │
│  ├── Background indexer                 │
│  └── ColBERT semantic search (PLAID)    │
└──────────┬──────────────────────────────┘
           │  GET /v1/content?tag=...
           │  tools/list, tools/call
           ▼
┌─────────────────────────────────────────┐
│  Connect Instance                       │
│  ├── MCP Server A  /content/{guid-a}/   │
│  ├── MCP Server B  /content/{guid-b}/   │
│  └── MCP Server C  /content/{guid-c}/   │
└─────────────────────────────────────────┘
```

## Setup

### Prerequisites

- Posit Connect >= 2026.02.0
- Must be deployed by a Connect **administrator** (the extension's ephemeral API key needs `AuthPrivilegeViewApps` for full content access)

### Deploy

Deploy as a `python-fastapi` extension via the Connect dashboard or `rsconnect-python`.

### Configure

1. Open the gateway's URL in a browser (e.g., `/content/{guid}/` or its vanity URL)
2. Add one or more **watched tags** (e.g., `mcp-server`)
3. Tag your MCP servers in Connect with the same tag
4. The gateway discovers them on the next indexing cycle (default: 5 min)

### Connect an LLM

Point your MCP client at the gateway's MCP endpoint:

```
{CONNECT_URL}/content/{gateway-guid}/mcp
```

The LLM will see two tools: `search_tools` and `call_tool`.

## Local Development

Requires [just](https://github.com/casey/just) and [uv](https://github.com/astral-sh/uv). Node.js is required for UI development.

### Full setup

```bash
cd extensions/mcp-gateway

# Install Python deps and UI deps
just setup
```

This runs `uv venv .venv`, installs Python requirements, and runs `npm install` in `ui/`.

### Running locally with test servers

The gateway ships with two test MCP servers (math and weather). Open three terminals:

**Terminal 1 — math test server (port 8083)**
```bash
just serve-math
```

**Terminal 2 — weather test server (port 8084)**
```bash
just serve-weather
```

**Terminal 3 — gateway (port 8082, pre-connected to both test servers)**
```bash
just serve
```

Open http://localhost:8082 in a browser to see the registry UI.

The gateway is pre-wired to the test servers via the `MCP_GATEWAY_LOCAL_SERVERS` env var set inside the `serve` recipe. No tag configuration is needed for local testing.

### UI development (hot reload)

While the gateway is running (`just serve`), start the Vite dev server:

```bash
just ui-dev
```

This opens http://localhost:5173 with HMR. When ready to ship UI changes:

```bash
just ui-build
```

This outputs to `static/` (already committed in the repo).

### Download the ColBERT model (optional)

The gateway uses ColBERT for semantic search. Without the model it falls back to SQLite keyword search. To download (17M params, ~70 MB):

```bash
just download-model
```

The model is saved to `models/` (gitignored).

### Trigger a re-index

```bash
just reindex
```

### Inspect discovered servers and search tools

```bash
just servers
just search "run SQL query"
```

### Lint and format

```bash
just lint        # check only
just lint-fix    # auto-fix
```

### Run tests

```bash
just test
```

### Clean everything

```bash
just clean
```

Removes `.venv`, `ui/node_modules`, `static/assets`, `data/`, `__pycache__`, and cache dirs.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `CONNECT_SERVER` | (set by Connect) | Connect server URL |
| `CONNECT_API_KEY` | (set by Connect) | Extension's ephemeral API key |
| `CONNECT_VISITOR_API_KEY` | (set by Connect) | Visitor identity for tool execution |
| `MCP_GATEWAY_INDEX_INTERVAL` | `300` | Seconds between indexing cycles |
| `MCP_GATEWAY_DB_PATH` | `data/gateway.db` | Path to local SQLite database |
| `MCP_GATEWAY_LOCAL_SERVERS` | — | Comma-separated `name=url` pairs for local test servers (bypasses tag discovery) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Search

The gateway uses [mxbai-edge-colbert-v0-17m](https://huggingface.co/mixedbread-ai/mxbai-edge-colbert-v0-17m) (17M params, Apache 2.0) for semantic search via ColBERT/PLAID. This provides significantly better matching of short agent queries ("run SQL") to tool descriptions compared to keyword search.

Falls back to SQLite keyword search if PyLate is unavailable or the model hasn't been downloaded.
