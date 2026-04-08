# Financial Chart MCP App

FastMCP v3 MCP App server that displays an interactive financial time series chart. Demonstrates core MCP Apps patterns:

- `@mcp.tool(app=AppConfig(...))` — tool linked to a `ui://` resource
- Two HTML delivery mechanisms: inline Python string (`RESOURCE_INLINE`) and file on disk (`RESOURCE_FILE`)
- App-only tools (`visibility=["app"]`) callable from the UI but hidden from the LLM
- CSP metadata for CDN-loaded `@modelcontextprotocol/ext-apps` SDK
- Stateless HTTP mode required for Connect deployment

## Tools

| Tool | Visibility | Description |
|---|---|---|
| `show_chart_inline` | LLM + app | Open chart — HTML delivered inline from Python string |
| `show_chart_file` | LLM + app | Open chart — HTML delivered from `chart.html` on disk |
| `refresh_chart_inline` | app-only | Regenerate random data for inline chart (called by UI refresh button) |
| `refresh_chart_file` | app-only | Regenerate random data for file chart (called by UI refresh button) |

## Prerequisites

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Setup

```bash
cd extensions/mcp-apps/financial-chart
uv venv
uv pip install -r requirements.txt
```

Or with pip:

```bash
pip install -r requirements.txt
```

## Run locally

```bash
python main.py
# Server listening at http://localhost:3001
# MCP endpoint: http://localhost:3001/mcp
```

Set `PORT` to use a different port:

```bash
PORT=4001 python main.py
```

Open http://localhost:3001 to see the index page with endpoint info.

## Test with basic-host

`basic-host` is the local MCP Apps host included in this collection. Run in a separate terminal:

```bash
cd extensions/mcp-apps/basic-host
npm install
SERVERS='["http://localhost:3001/mcp"]' npm run start
```

Open http://localhost:8080. Click "show_chart_inline" or "show_chart_file" to render the chart in a sandboxed iframe. The chart supports:
- Toggle revenue / expenses / profit series
- Hover for tooltips
- Click a data point → sends a message back to the host chat
- Refresh button → calls `refresh_chart_inline` / `refresh_chart_file` via `app.callServerTool`

Or use the top-level `justfile` from `extensions/mcp-apps/`:

```bash
cd extensions/mcp-apps
just dev   # starts both server and host together
```

## Test with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "financial-chart": {
      "type": "streamable-http",
      "url": "http://localhost:3001/mcp"
    }
  }
}
```

## Test with VS Code / Positron

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "financial-chart": {
      "type": "streamable-http",
      "url": "http://localhost:3001/mcp"
    }
  }
}
```

## Run the MCP protocol smoke test

```bash
cd extensions/mcp-apps
just test
```

This starts the server, runs `financial-chart/test_server.py` against it, then kills the server.

## Deploy to Posit Connect

Requires Posit Connect >= 2026.06.0 with MCP Apps support enabled.

```bash
rsconnect deploy fastapi \
  --server https://your-connect-server \
  --api-key YOUR_API_KEY \
  --entrypoint main:app \
  --title "Financial Chart MCP App" \
  extensions/mcp-apps/financial-chart/
```

The deployed MCP endpoint will be at:
```
https://your-connect-server/content/{guid}/mcp
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `3001` | HTTP server port |
