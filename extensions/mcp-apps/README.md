# MCP Apps Examples

Example MCP App servers demonstrating the MCP Apps pattern on Posit Connect. Each server uses FastMCP v3 with `@mcp.tool(app=AppConfig(...))` to link tools to `ui://` resources rendered in sandboxed iframes by the host.

## Examples

### [financial-chart/](./financial-chart/)

FastMCP v3 MCP App server with an interactive financial chart UI. Demonstrates:
- `@mcp.tool(app=AppConfig(...))` for tool-UI linking
- Two HTML delivery mechanisms: inline Python string and file on disk
- App-only tools (`visibility=["app"]`) hidden from the LLM, callable from the UI
- CSP metadata for CDN-loaded `@modelcontextprotocol/ext-apps` SDK

### [content-browser/](./content-browser/)

MCP App server for searching and chatting with static Connect content. Demonstrates:
- Visitor-scoped API access via `Posit-Connect-User-Session-Token`
- Authenticated content proxy for iframe previews
- Mixed HTTPS/HTTP content inlining strategies

### [pins-browser/](./pins-browser/)

MCP App server for browsing and querying pin data. Demonstrates:
- DuckDB integration for in-app SQL queries
- Per-user session state for loaded pin data
- `analyze_pin_data` tool for LLM-side data discussion

### [basic-host/](./basic-host/)

TypeScript ad-hoc host for local testing. Connects to MCP servers via StreamableHTTP, discovers `ui://` resources, and renders MCP App UIs in sandboxed iframes. Supports both local and Connect-hosted servers.

## Quick start

```bash
# From extensions/mcp-apps/

# Install all deps
just install

# Start financial-chart server (port 3001) + basic-host (port 8080) together
just dev

# Open http://localhost:8080
```

Or step by step:

```bash
# Terminal 1: Start the MCP server
cd financial-chart
uv venv && uv pip install -r requirements.txt
python main.py

# Terminal 2: Start the host
cd basic-host
npm install
SERVERS='["http://localhost:3001/mcp"]' npm run start

# Open http://localhost:8080
```

## Testing with external hosts

### Claude Desktop

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

### VS Code / Positron

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

## Run the smoke test

```bash
just test
```

Starts the financial-chart server, runs the MCP protocol smoke test, then cleans up.

## Architecture

```
Host (Claude / VS Code / basic-host)
  → tools/call "show_chart_inline"
  → resources/read "ui://financial-chart/inline"
  → render HTML in sandboxed iframe
  → forward tool result to UI via postMessage
  → UI renders interactive chart
  → user clicks → app.sendMessage() → message appears in chat
  → user clicks refresh → app.callServerTool("refresh_chart_inline") → new data
```

See [basic-host/README.md](./basic-host/README.md) for the full host architecture and Connect proxy flow.
