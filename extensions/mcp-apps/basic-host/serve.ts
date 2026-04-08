#!/usr/bin/env npx tsx
/**
 * HTTP servers for the MCP Apps basic-host:
 * - Host server (port 8080): serves the host UI + Connect proxy
 * - Sandbox server (port 8081): serves sandbox.html with CSP headers
 *
 * Running on separate ports ensures proper origin isolation for security
 * (the MCP Apps spec requires the sandbox to be on a different origin).
 *
 * Usage:
 *   # Local MCP server only
 *   SERVERS='["http://localhost:3001/mcp"]' npm run start
 *
 *   # Local + Connect-hosted MCP server (proxied to avoid CORS)
 *   CONNECT_SERVERS='[{"url":"https://connect.example.com/content/abc123/mcp","apiKey":"YOUR_KEY","name":"My Server"}]' npm run start
 *
 *   # Both together
 *   SERVERS='["http://localhost:3001/mcp"]' \
 *   CONNECT_SERVERS='[{"url":"https://connect.example.com/content/abc123/mcp","apiKey":"YOUR_KEY"}]' \
 *   npm run start
 */

import express from "express";
import cors from "cors";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import type { McpUiResourceCsp } from "@modelcontextprotocol/ext-apps";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const HOST_PORT = parseInt(process.env.HOST_PORT || "8080", 10);
const SANDBOX_PORT = parseInt(process.env.SANDBOX_PORT || "8081", 10);
const DIRECTORY = join(__dirname, "dist");
const SERVERS: string[] = process.env.SERVERS
  ? JSON.parse(process.env.SERVERS)
  : ["http://localhost:3001/mcp"];

// Connect-hosted MCP servers that need auth proxying
interface ConnectServer {
  url: string;
  apiKey: string;
  name?: string;
}
const CONNECT_SERVERS: ConnectServer[] = process.env.CONNECT_SERVERS
  ? JSON.parse(process.env.CONNECT_SERVERS)
  : [];

// ============ Host Server (port 8080) ============
const hostApp = express();
hostApp.use(cors());

// Don't serve sandbox.html from the host port
hostApp.use((req, res, next) => {
  if (req.path === "/sandbox.html") {
    res.status(404).send("Sandbox is served on a different port");
    return;
  }
  next();
});

hostApp.use(express.static(DIRECTORY));

// API endpoint to get full server config (local + Connect-proxied)
hostApp.get("/api/servers", (_req, res) => {
  const servers: Array<{
    url: string;
    source: "local" | "connect";
    name?: string;
    connectUrl?: string;
  }> = [];

  // Local servers — connected directly from the browser
  for (const url of SERVERS) {
    servers.push({ url, source: "local" });
  }

  // Connect servers — proxied through this host to handle auth + CORS
  CONNECT_SERVERS.forEach((cs, i) => {
    servers.push({
      url: `/connect-proxy/${i}/mcp`,
      source: "connect",
      name: cs.name,
      connectUrl: cs.url,
    });
  });

  res.json(servers);
});

// ============ Connect Proxy ============
// Proxies MCP requests to Connect-hosted servers, injecting the API key.
// This avoids browser CORS issues since the browser talks to localhost and
// we forward server-side with the Authorization header.

// Parse raw body for forwarding (JSON + SSE)
hostApp.use("/connect-proxy", express.raw({ type: "*/*", limit: "10mb" }));

hostApp.all("/connect-proxy/:index/*path", async (req, res) => {
  const index = parseInt(req.params.index, 10);
  const cs = CONNECT_SERVERS[index];
  if (!cs) {
    res.status(404).json({ error: `No Connect server at index ${index}` });
    return;
  }

  // Build the target URL: cs.url is the full MCP endpoint (e.g. .../content/{guid}/mcp)
  // The wildcard captures the path suffix after /connect-proxy/{index}/
  // Use the parent of cs.url as base so "mcp" suffix resolves to the same endpoint
  const suffix = req.params.path || "";
  const base = new URL(cs.url);
  const parentPath = base.pathname.replace(/\/[^/]*$/, "/");
  const targetUrl = new URL(parentPath + suffix, base.origin);
  // Preserve query string
  targetUrl.search = new URL(req.url, "http://localhost").search;

  // Forward headers, injecting auth
  const forwardHeaders: Record<string, string> = {};
  const passthroughHeaders = [
    "content-type",
    "accept",
    "mcp-protocol-version",
    "mcp-session-id",
    "last-event-id",
  ];
  for (const h of passthroughHeaders) {
    const val = req.headers[h];
    if (val) forwardHeaders[h] = Array.isArray(val) ? val[0] : val;
  }
  forwardHeaders["authorization"] = `Key ${cs.apiKey}`;

  try {
    const upstream = await fetch(targetUrl.toString(), {
      method: req.method,
      headers: forwardHeaders,
      body: ["GET", "HEAD", "DELETE"].includes(req.method)
        ? undefined
        : req.body,
      // @ts-expect-error Node 18+ fetch supports duplex
      duplex: "half",
    });

    // Forward status + response headers
    res.status(upstream.status);
    const responseHeaders = [
      "content-type",
      "mcp-session-id",
      "cache-control",
    ];
    for (const h of responseHeaders) {
      const val = upstream.headers.get(h);
      if (val) res.setHeader(h, val);
    }

    // Stream the body back (supports SSE streaming)
    if (upstream.body) {
      const reader = upstream.body.getReader();
      const pump = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            res.end();
            return;
          }
          res.write(value);
        }
      };
      pump().catch(() => res.end());
    } else {
      res.end();
    }
  } catch (err) {
    console.error(`[Proxy] Error forwarding to ${targetUrl}:`, err);
    res.status(502).json({ error: "Proxy error", details: String(err) });
  }
});

hostApp.get("/", (_req, res) => {
  res.redirect("/index.html");
});

// ============ Sandbox Server (port 8081) ============
const sandboxApp = express();
sandboxApp.use(cors());

/**
 * Validate CSP domain entries to prevent injection attacks.
 * Rejects entries containing characters that could break out of CSP directives.
 */
function sanitizeCspDomains(domains?: string[]): string[] {
  if (!domains) return [];
  return domains.filter((d) => typeof d === "string" && !/[;\r\n'" ]/.test(d));
}

function buildCspHeader(csp?: McpUiResourceCsp): string {
  const resourceDomains = sanitizeCspDomains(csp?.resourceDomains).join(" ");
  const connectDomains = sanitizeCspDomains(csp?.connectDomains).join(" ");
  const frameDomains = sanitizeCspDomains(csp?.frameDomains).join(" ") || null;
  const baseUriDomains =
    sanitizeCspDomains(csp?.baseUriDomains).join(" ") || null;

  const directives = [
    "default-src 'self' 'unsafe-inline'",
    `script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data: ${resourceDomains}`.trim(),
    `style-src 'self' 'unsafe-inline' blob: data: ${resourceDomains}`.trim(),
    `img-src 'self' data: blob: ${resourceDomains}`.trim(),
    `font-src 'self' data: blob: ${resourceDomains}`.trim(),
    `connect-src 'self' ${connectDomains}`.trim(),
    `worker-src 'self' blob: ${resourceDomains}`.trim(),
    frameDomains ? `frame-src blob: ${frameDomains}` : "frame-src blob:",
    "object-src 'none'",
    baseUriDomains ? `base-uri ${baseUriDomains}` : "base-uri 'none'",
  ];

  return directives.join("; ");
}

// Serve sandbox.html with CSP from query params
sandboxApp.get(["/", "/sandbox.html"], (req, res) => {
  let cspConfig: McpUiResourceCsp | undefined;
  if (typeof req.query.csp === "string") {
    try {
      cspConfig = JSON.parse(req.query.csp);
    } catch (e) {
      console.warn("[Sandbox] Invalid CSP query param:", e);
    }
  }

  const cspHeader = buildCspHeader(cspConfig);
  res.setHeader("Content-Security-Policy", cspHeader);
  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");

  res.sendFile(join(DIRECTORY, "sandbox.html"));
});

// Serve built assets (JS chunks referenced by sandbox.html after Vite build)
sandboxApp.use("/assets", express.static(join(DIRECTORY, "assets")));

sandboxApp.use((_req, res) => {
  res.status(404).send("Only sandbox.html and its assets are served on this port");
});

// ============ Start both servers ============
hostApp.listen(HOST_PORT, () => {
  console.log(`Host server:    http://localhost:${HOST_PORT}`);
});

sandboxApp.listen(SANDBOX_PORT, () => {
  console.log(`Sandbox server: http://localhost:${SANDBOX_PORT}`);
  console.log(`\nLocal servers: ${SERVERS.join(", ") || "(none)"}`);
  if (CONNECT_SERVERS.length > 0) {
    console.log(`Connect servers (proxied):`);
    CONNECT_SERVERS.forEach((cs, i) => {
      console.log(`  [${i}] ${cs.name || cs.url} → /connect-proxy/${i}/mcp`);
    });
  }
  console.log("\nPress Ctrl+C to stop\n");
});
