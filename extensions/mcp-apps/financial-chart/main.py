"""Financial Chart MCP App Server — interactive time series visualization.

Demonstrates MCP Apps with FastMCP v3 on Connect, using two different
HTML delivery mechanisms on the same server:
- Inline: UI HTML embedded as a Python string in the resource handler
- File: UI HTML served from a separate chart.html file on disk

Both produce the same interactive chart, letting you validate that the host
correctly renders UIs delivered either way.

Other patterns shown:
- Tool linked to a ui:// resource via AppConfig
- App-only tools (hidden from model, callable from UI via callServerTool)
- CSP metadata for CDN-loaded ext-apps SDK
- Stateless HTTP mode (required for Connect deployment)
- FastAPI wrapping with CORS for streamable HTTP transport
- Index page with server info and endpoint URL

Setup:
    pip install -r requirements.txt

Usage:
    python main.py                  # HTTP mode (port 3001)

Testing with basic-host:
    cd ../basic-host && npm install
    SERVERS='["http://localhost:3001/mcp"]' npm run start
"""

from __future__ import annotations

import json
import math
import os
import random
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

HERE = Path(__file__).parent
RESOURCE_INLINE = "ui://financial-chart/inline"
RESOURCE_FILE = "ui://financial-chart/file"

mcp = FastMCP(
    name="financial-chart-server",
    instructions=(
        "MCP server for displaying interactive 2025 financial time series charts. "
        "Use show_chart_inline or show_chart_file to display the chart — both "
        "produce the same interactive UI but demonstrate different HTML delivery "
        "mechanisms (inline string vs file on disk). The UI supports toggling "
        "revenue/expenses/profit series, refreshing data, and clicking points to "
        "send details back to the conversation."
    ),
)


def generate_financial_data() -> list[dict]:
    """Generate 52 weeks of simulated financial data."""
    weeks = 52
    data = []
    base_revenue = 100000
    base_expenses = 70000

    for week in range(1, weeks + 1):
        date = datetime(2025, 1, 1) + timedelta(weeks=week - 1)
        date_str = date.strftime("%Y-%m-%d")

        seasonal_factor = 1 + 0.3 * math.sin((week / 52) * math.pi * 2)
        random_factor = 0.8 + random.random() * 0.4

        revenue = round(base_revenue * seasonal_factor * random_factor)
        expenses = round(base_expenses * (0.9 + random.random() * 0.2))
        profit = revenue - expenses

        data.append(
            {
                "date": date_str,
                "revenue": revenue,
                "expenses": expenses,
                "profit": profit,
            }
        )

        base_revenue += 500
        base_expenses += 300

    return data


def _chart_tool_result(title: str | None = None) -> ToolResult:
    """Build a ToolResult with generated financial data."""
    data = generate_financial_data()
    result = {"timeSeries": data}
    if title:
        result["title"] = title
    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(result))],
    )


# ---------------------------------------------------------------------------
# Inline variant: HTML embedded as a Python string
# ---------------------------------------------------------------------------


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_INLINE),
    title="Show Chart (Inline HTML)",
    description="Display the financial chart using UI HTML embedded in the server code",
)
async def show_chart_inline() -> ToolResult:
    """Show the chart — inline HTML delivery."""
    return _chart_tool_result("2025 Financial Performance (Inline)")


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_INLINE, visibility=["app"]),
    title="Refresh Inline Chart Data",
    description="Generate new random financial data for the inline chart",
)
async def refresh_chart_inline() -> ToolResult:
    """Refresh data for inline chart (app-only, called from UI refresh button)."""
    return _chart_tool_result()


@mcp.resource(
    RESOURCE_INLINE,
    name="Financial Chart UI (Inline)",
    description="Interactive financial chart — HTML embedded in server",
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
async def chart_inline_resource() -> str:
    """Serve the chart UI from an embedded Python string."""
    return CHART_HTML_INLINE


# ---------------------------------------------------------------------------
# File variant: HTML served from chart.html on disk
# ---------------------------------------------------------------------------


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_FILE),
    title="Show Chart (File HTML)",
    description="Display the financial chart using UI HTML served from a file on disk",
)
async def show_chart_file() -> ToolResult:
    """Show the chart — file HTML delivery."""
    return _chart_tool_result("2025 Financial Performance (File)")


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_FILE, visibility=["app"]),
    title="Refresh File Chart Data",
    description="Generate new random financial data for the file chart",
)
async def refresh_chart_file() -> ToolResult:
    """Refresh data for file chart (app-only, called from UI refresh button)."""
    return _chart_tool_result()


@mcp.resource(
    RESOURCE_FILE,
    name="Financial Chart UI (File)",
    description="Interactive financial chart — HTML served from chart.html",
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
async def chart_file_resource() -> str:
    """Serve the chart UI from chart.html on disk."""
    return (HERE / "chart.html").read_text()


# --- FastAPI wrapping ---

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["mcp-session-id"],
    )
]

mcp_app = mcp.http_app(path="/mcp", stateless_http=True, middleware=middleware)
app = FastAPI(
    title="Financial Chart MCP Server",
    lifespan=mcp_app.lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def get_index_page(request: Request):
    endpoint = urllib.parse.urljoin(str(request.url), "mcp")
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{mcp.name}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ color: #1a1a2e; }}
    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
    pre {{ background: #f0f0f0; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
    .endpoint {{ font-size: 1.1em; margin: 1rem 0; }}
    .tools {{ margin-top: 1.5rem; }}
    .tool {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem; margin-bottom: 0.75rem; }}
    .tool h3 {{ margin: 0 0 0.5rem 0; color: #2d3748; }}
    .tool p {{ margin: 0; color: #666; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; margin-left: 0.5rem; }}
    .badge-ui {{ background: #e8f5e9; color: #2e7d32; }}
    .badge-app {{ background: #fff3e0; color: #e65100; }}
  </style>
</head>
<body>
  <h1>{mcp.name}</h1>
  <p class="endpoint">MCP endpoint: <code>{endpoint}</code></p>
  <div class="tools">
    <h2>Tools</h2>
    <div class="tool">
      <h3>show_chart_inline <span class="badge badge-ui">has UI</span></h3>
      <p>Display the financial chart (HTML embedded in server code)</p>
    </div>
    <div class="tool">
      <h3>show_chart_file <span class="badge badge-ui">has UI</span></h3>
      <p>Display the financial chart (HTML served from chart.html file)</p>
    </div>
    <div class="tool">
      <h3>refresh_chart_inline <span class="badge badge-app">app-only</span></h3>
      <p>Refresh data for inline chart (called from UI refresh button)</p>
    </div>
    <div class="tool">
      <h3>refresh_chart_file <span class="badge badge-app">app-only</span></h3>
      <p>Refresh data for file chart (called from UI refresh button)</p>
    </div>
  </div>
  <div class="tools">
    <h2>Connect to this server</h2>
    <pre>{{"mcpServers": {{
  "financial-chart": {{
    "type": "streamable-http",
    "url": "{endpoint}"
  }}
}}}}</pre>
  </div>
</body>
</html>"""


app.mount("/", mcp_app)


# --- Embedded chart UI (inline variant) ---
# Identical to chart.html except the refresh tool name is refresh_chart_inline.

CHART_HTML_INLINE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <title>Financial Chart</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
      background: var(--color-background-primary, #ffffff);
      color: var(--color-text-primary, #000000);
    }

    .container { padding: 20px; max-width: 1200px; margin: 0 auto; }

    .header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 20px; flex-wrap: wrap; gap: 12px;
    }

    h1 {
      font-size: var(--font-heading-lg-size, 24px);
      font-weight: var(--font-weight-semibold, 600);
    }

    .controls { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
    .checkbox-group { display: flex; gap: 12px; align-items: center; }

    .checkbox-label {
      display: flex; align-items: center; gap: 6px; cursor: pointer;
      font-size: var(--font-text-sm-size, 14px);
      color: var(--color-text-secondary, #666666);
    }

    .refresh-btn {
      padding: 8px 16px;
      background: var(--color-background-secondary, #f0f0f0);
      border: 1px solid var(--color-border-primary, #d0d0d0);
      border-radius: var(--border-radius-md, 6px);
      cursor: pointer; font-size: var(--font-text-sm-size, 14px);
      color: var(--color-text-primary, #000000);
      transition: background 0.2s;
    }
    .refresh-btn:hover { background: var(--color-background-tertiary, #e0e0e0); }
    .refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .chart-container {
      background: var(--color-background-secondary, #f9f9f9);
      border: 1px solid var(--color-border-primary, #e0e0e0);
      border-radius: var(--border-radius-lg, 8px);
      padding: 20px; position: relative; overflow: hidden;
    }

    .chart { width: 100%; height: 400px; position: relative; cursor: crosshair; }
    canvas { display: block; width: 100%; height: 100%; }

    .tooltip {
      position: absolute;
      background: var(--color-background-primary, #ffffff);
      border: 1px solid var(--color-border-primary, #d0d0d0);
      border-radius: var(--border-radius-sm, 4px);
      padding: 8px 12px; font-size: var(--font-text-sm-size, 14px);
      pointer-events: none; display: none; z-index: 10;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .tooltip.visible { display: block; }

    .status {
      margin-top: 16px; padding: 12px;
      background: var(--color-background-tertiary, #f0f0f0);
      border-radius: var(--border-radius-md, 6px);
      font-size: var(--font-text-sm-size, 14px);
      color: var(--color-text-secondary, #666666);
      font-family: var(--font-mono, "Courier New", monospace);
      display: none;
    }
    .status.visible { display: block; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 id="title">Financial Chart</h1>
      <div class="controls">
        <div class="checkbox-group">
          <label class="checkbox-label">
            <input type="checkbox" id="cb-revenue" checked>
            <span style="color: #3b82f6;">&#9679; Revenue</span>
          </label>
          <label class="checkbox-label">
            <input type="checkbox" id="cb-expenses" checked>
            <span style="color: #ef4444;">&#9679; Expenses</span>
          </label>
          <label class="checkbox-label">
            <input type="checkbox" id="cb-profit" checked>
            <span style="color: #10b981;">&#9679; Profit</span>
          </label>
        </div>
        <button class="refresh-btn" id="refresh-btn">&#8635; Refresh Data</button>
      </div>
    </div>

    <div class="chart-container">
      <div class="chart">
        <canvas id="chart-canvas"></canvas>
        <div class="tooltip" id="tooltip"></div>
      </div>
    </div>

    <div class="status" id="status"></div>
  </div>

  <script type="module">
    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@1.0.1/app-with-deps";

    // --- State ---
    const COLORS = { revenue: "#3b82f6", expenses: "#ef4444", profit: "#10b981" };
    let chartData = [];
    let visibleSeries = new Set(["revenue", "expenses", "profit"]);
    let chartTitle = "Financial Chart";

    // --- DOM ---
    const canvas = document.getElementById("chart-canvas");
    const ctx2d = canvas.getContext("2d");
    const tooltip = document.getElementById("tooltip");
    const titleEl = document.getElementById("title");
    const statusEl = document.getElementById("status");
    const refreshBtn = document.getElementById("refresh-btn");

    // --- MCP App ---
    const app = new App({ name: "financial-chart", version: "1.0.0" });

    // Parse chart data from a tool result
    function applyToolResult(result) {
      const textContent = (result.content || [])
        .filter(c => c.type === "text")
        .map(c => c.text)
        .join("");
      if (!textContent) return;
      try {
        const parsed = JSON.parse(textContent);
        if (parsed.title) { chartTitle = parsed.title; titleEl.textContent = chartTitle; }
        if (parsed.timeSeries) { chartData = parsed.timeSeries; renderChart(); }
      } catch (e) {
        console.error("Failed to parse tool result:", e);
      }
    }

    // Handle tool result from host-initiated tool calls
    app.ontoolresult = (result) => {
      console.log("Tool result received:", result);
      applyToolResult(result);
    };

    // Handle host context changes (theme, safe area)
    app.onhostcontextchanged = (hostCtx) => {
      if (hostCtx.theme) {
        document.documentElement.setAttribute("data-theme", hostCtx.theme);
      }
      if (hostCtx.safeAreaInsets) {
        const { top, right, bottom, left } = hostCtx.safeAreaInsets;
        document.body.style.padding = top + "px " + right + "px " + bottom + "px " + left + "px";
      }
      if (chartData.length > 0) renderChart();
    };

    app.onteardown = async () => ({ });

    // --- Canvas chart rendering ---
    function setupCanvas() {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx2d.scale(dpr, dpr);
    }

    function renderChart() {
      if (!chartData.length) return;
      setupCanvas();

      const rect = canvas.getBoundingClientRect();
      const w = rect.width, h = rect.height;
      const pad = { top: 20, right: 20, bottom: 40, left: 60 };
      const cw = w - pad.left - pad.right;
      const ch = h - pad.top - pad.bottom;

      ctx2d.clearRect(0, 0, w, h);

      // Compute scale from visible series
      const vals = [];
      chartData.forEach(d => {
        if (visibleSeries.has("revenue")) vals.push(d.revenue);
        if (visibleSeries.has("expenses")) vals.push(d.expenses);
        if (visibleSeries.has("profit")) vals.push(d.profit);
      });
      if (!vals.length) return;

      const minV = Math.min(...vals, 0);
      const maxV = Math.max(...vals);
      const range = maxV - minV || 1;

      // Axes
      const borderColor = getComputedStyle(document.body).getPropertyValue("--color-border-primary") || "#d0d0d0";
      const textColor = getComputedStyle(document.body).getPropertyValue("--color-text-secondary") || "#666666";

      ctx2d.strokeStyle = borderColor;
      ctx2d.lineWidth = 1;
      ctx2d.beginPath();
      ctx2d.moveTo(pad.left, pad.top);
      ctx2d.lineTo(pad.left, h - pad.bottom);
      ctx2d.lineTo(w - pad.right, h - pad.bottom);
      ctx2d.stroke();

      // Y labels
      ctx2d.fillStyle = textColor;
      ctx2d.font = "12px sans-serif";
      ctx2d.textAlign = "right";
      ctx2d.textBaseline = "middle";
      for (let i = 0; i <= 5; i++) {
        const v = minV + (range / 5) * i;
        const y = h - pad.bottom - (ch / 5) * i;
        ctx2d.fillText("$" + Math.round(v / 1000) + "k", pad.left - 10, y);
      }

      // X labels
      ctx2d.textAlign = "center";
      ctx2d.textBaseline = "top";
      for (let i = 0; i < chartData.length; i += 4) {
        const x = pad.left + (cw / (chartData.length - 1)) * i;
        const dt = new Date(chartData[i].date);
        ctx2d.fillText((dt.getMonth() + 1) + "/" + dt.getDate(), x, h - pad.bottom + 10);
      }

      // Draw series
      function drawLine(key, color) {
        if (!visibleSeries.has(key)) return;
        ctx2d.strokeStyle = color;
        ctx2d.lineWidth = 2;
        ctx2d.beginPath();
        chartData.forEach((d, i) => {
          const x = pad.left + (cw / (chartData.length - 1)) * i;
          const y = h - pad.bottom - ((d[key] - minV) / range) * ch;
          i === 0 ? ctx2d.moveTo(x, y) : ctx2d.lineTo(x, y);
        });
        ctx2d.stroke();

        // Points
        chartData.forEach((d, i) => {
          const x = pad.left + (cw / (chartData.length - 1)) * i;
          const y = h - pad.bottom - ((d[key] - minV) / range) * ch;
          ctx2d.fillStyle = color;
          ctx2d.beginPath();
          ctx2d.arc(x, y, 3, 0, Math.PI * 2);
          ctx2d.fill();
        });
      }

      drawLine("revenue", COLORS.revenue);
      drawLine("expenses", COLORS.expenses);
      drawLine("profit", COLORS.profit);
    }

    // --- Interaction: find closest point ---
    function findClosest(mx, my) {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width, h = rect.height;
      const pad = { top: 20, right: 20, bottom: 40, left: 60 };
      const cw = w - pad.left - pad.right;
      const ch = h - pad.top - pad.bottom;

      const vals = [];
      chartData.forEach(d => {
        if (visibleSeries.has("revenue")) vals.push(d.revenue);
        if (visibleSeries.has("expenses")) vals.push(d.expenses);
        if (visibleSeries.has("profit")) vals.push(d.profit);
      });
      const minV = Math.min(...vals, 0);
      const maxV = Math.max(...vals);
      const range = maxV - minV || 1;

      let best = null;
      chartData.forEach((d, i) => {
        const x = pad.left + (cw / (chartData.length - 1)) * i;
        ["revenue", "expenses", "profit"].forEach(key => {
          if (!visibleSeries.has(key)) return;
          const y = h - pad.bottom - ((d[key] - minV) / range) * ch;
          const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2);
          if (!best || dist < best.dist) best = { i, key, dist };
        });
      });
      return best;
    }

    // Tooltip on hover
    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      const closest = findClosest(e.clientX - rect.left, e.clientY - rect.top);
      if (closest && closest.dist < 20) {
        const pt = chartData[closest.i];
        tooltip.innerHTML =
          "<div><strong>" + closest.key.charAt(0).toUpperCase() + closest.key.slice(1) + "</strong></div>" +
          "<div>" + pt.date + "</div>" +
          "<div>$" + pt[closest.key].toLocaleString() + "</div>";
        tooltip.style.left = (e.clientX - rect.left + 15) + "px";
        tooltip.style.top = (e.clientY - rect.top + 15) + "px";
        tooltip.classList.add("visible");
      } else {
        tooltip.classList.remove("visible");
      }
    });

    canvas.addEventListener("mouseleave", () => tooltip.classList.remove("visible"));

    // Click to send message back to chat
    canvas.addEventListener("click", async (e) => {
      const rect = canvas.getBoundingClientRect();
      const closest = findClosest(e.clientX - rect.left, e.clientY - rect.top);
      if (!closest || closest.dist >= 20) return;

      const pt = chartData[closest.i];
      const label = closest.key.charAt(0).toUpperCase() + closest.key.slice(1);
      const value = "$" + pt[closest.key].toLocaleString();

      statusEl.innerHTML = "<strong>Clicked:</strong> " + pt.date + " | " + label + " | " + value;
      statusEl.classList.add("visible");

      await app.sendMessage({
        role: "user",
        content: [{ type: "text", text: "You clicked on " + label + " for " + pt.date + ": " + value }]
      });
      await app.sendLog({ level: "info", data: "Chart clicked: " + pt.date + ", " + label + ", " + value });
    });

    // Checkbox toggles
    ["revenue", "expenses", "profit"].forEach(key => {
      document.getElementById("cb-" + key).addEventListener("change", (e) => {
        e.target.checked ? visibleSeries.add(key) : visibleSeries.delete(key);
        renderChart();
      });
    });

    // Refresh button calls app-only tool (inline variant)
    refreshBtn.addEventListener("click", async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing...";
      try {
        const result = await app.callServerTool({ name: "refresh_chart_inline", arguments: {} });
        applyToolResult(result);
      } catch (err) {
        console.error("Refresh failed:", err);
        await app.sendLog({ level: "error", data: "Refresh failed: " + err });
      } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "\\u21BB Refresh Data";
      }
    });

    // Resize
    window.addEventListener("resize", () => { if (chartData.length) renderChart(); });

    // Connect to host
    await app.connect();
    console.log("Financial Chart MCP App initialized (inline variant)");
  </script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "3001"))
    print(f"Financial Chart MCP Server listening on http://localhost:{port}")
    print(f"  MCP endpoint: http://localhost:{port}/mcp")
    print(f"  Index page:   http://localhost:{port}/")
    uvicorn.run(app, host="0.0.0.0", port=port)
