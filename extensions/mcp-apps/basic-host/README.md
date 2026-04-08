# MCP Apps Basic Host

Ad-hoc MCP Apps host for local testing. Connects to MCP servers via streamable HTTP,
discovers tools and `ui://` resources, and renders MCP App UIs in sandboxed iframes
following the MCP Apps specification.

Supports both **local** MCP servers and **Connect-hosted** MCP servers (with API key
auth proxying to avoid browser CORS issues).

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Host (port 8080)                               │
│  index.html                                     │
│  - Connects to MCP servers (local + Connect)    │
│  - Lists tools, calls tools                     │
│  - Creates sandboxed iframe per app             │
│  - Uses AppBridge for host <-> app comms        │
│                                                 │
│  serve.ts                                       │
│  - Serves host UI + sandbox                     │
│  - Proxies Connect MCP requests with API key    │
│  - /connect-proxy/{i}/mcp -> Connect server     │
└──────┬──────────┬───────────────┬───────────────┘
       │          │               │
       ▼          ▼               ▼
┌──────────┐ ┌────────────┐ ┌──────────────────┐
│  Local   │ │  Sandbox   │ │  Connect Server  │
│  MCP     │ │  :8081     │ │  (remote)        │
│  Server  │ │  CSP +     │ │                  │
│  :3001   │ │  blob      │ │  Auth: API key   │
│  (direct │ │  iframe    │ │  injected by     │
│  from    │ │  relay     │ │  proxy in        │
│  browser)│ │            │ │  serve.ts        │
└──────────┘ └────────────┘ └──────────────────┘
```

## Setup

```bash
npm install
```

## Run (local MCP server)

Start your MCP server first (e.g., the financial-chart example):

```bash
cd ../financial-chart
pip install -r requirements.txt
python main.py
```

Then start the host:

```bash
SERVERS='["http://localhost:3001/mcp"]' npm run start
```

Open http://localhost:8080 in your browser.

## Run (Connect-hosted MCP server)

Connect to an MCP server deployed on Posit Connect. The host proxies requests
through `serve.ts` to inject the API key and avoid CORS issues.

```bash
CONNECT_SERVERS='[{"url":"https://connect.example.com/content/{guid}/mcp","apiKey":"YOUR_API_KEY","name":"My Server"}]' npm run start
```

Or combine local and Connect servers:

```bash
SERVERS='["http://localhost:3001/mcp"]' \
CONNECT_SERVERS='[{"url":"https://connect.example.com/content/{guid}/mcp","apiKey":"YOUR_KEY"}]' \
npm run start
```

You can also add Connect servers at runtime via the "+ Add Connect Server" form in the UI.
This uses direct browser connections with the `Authorization: Key` header (requires CORS
to be configured on Connect to allow the MCP headers).

## How it works

1. **Server discovery**: Fetches server config from `/api/servers`, connects via StreamableHTTP
2. **Tool listing**: Calls `tools/list` and `resources/list` on each server
3. **Tool call**: When you click a tool button, calls the tool and checks for `ui://` resources
4. **UI rendering**: If the tool has a `ui://` resource:
   - Reads the resource via `resources/read`
   - Creates a sandboxed iframe pointing to the sandbox server (different origin)
   - Creates an `AppBridge` to manage host <-> app communication
   - Sends the HTML to the sandbox, which loads it in an inner iframe
   - Forwards tool input and results to the app via postMessage
5. **App communication**: The app can:
   - Call `sendMessage` to send messages back to the host
   - Call `callServerTool` to invoke app-only tools on the server
   - Call `sendLog` for debug logging
   - Request size changes and display mode changes

## Connect proxy flow

When using `CONNECT_SERVERS`, the proxy flow is:

```
Browser                  serve.ts                    Connect
  |                        |                           |
  |-- POST /connect-proxy/0/mcp -->                    |
  |                        |-- POST /content/{guid}/mcp -->
  |                        |   + Authorization: Key XX |
  |                        |                           |
  |                        |<-- 200 + mcp-session-id --|
  |<-- 200 + mcp-session-id -|                         |
```

The proxy:
- Forwards all MCP headers (`mcp-protocol-version`, `mcp-session-id`)
- Injects the `Authorization: Key` header
- Streams responses (supports SSE for tool progress)
- Avoids CORS issues since the browser only talks to localhost

## CORS considerations

**Local servers**: No CORS issues (same machine, different ports — CORS handled by the MCP server's own middleware).

**Connect servers via proxy**: No CORS issues (browser talks to localhost:8080, proxy talks to Connect server-side).

**Connect servers via direct browser connection** (the "+ Add Connect Server" form): Requires Connect's CORS to allow:
- The `mcp-protocol-version` and `mcp-session-id` request headers
- The `mcp-session-id` response header
- The origin `http://localhost:8080`

Connect auto-includes localhost origins by default, but the MCP-specific headers may need to be added to `CORS.AllowHeaders` in Connect's configuration.

## Key SDK modules used

- `@modelcontextprotocol/sdk/client` — MCP client, StreamableHTTP transport
- `@modelcontextprotocol/ext-apps/app-bridge` — AppBridge, PostMessageTransport, CSP utilities
