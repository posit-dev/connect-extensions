"""Connect Pins Data Viewer MCP App Server — browse, explore, and query pin data.

Demonstrates MCP Apps with FastMCP v3 on Connect:
- Browse and search pins on Posit Connect via the pins Python SDK
- Load pin data into DuckDB for interactive exploration
- View column metadata, summary statistics, and data preview
- Run SQL queries against pin data
- Uses posit-sdk with user session token for visitor-scoped API access

Setup:
    pip install -r requirements.txt
    export CONNECT_SERVER=https://connect.example.com
    export CONNECT_API_KEY=your-api-key

Usage:
    python main.py                  # HTTP mode (port 3002)
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import os
import urllib.parse
from pathlib import Path

import duckdb
import pandas as pd
from pins import board_connect

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent
from posit.connect import Client
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

HERE = Path(__file__).parent
RESOURCE_URI = "ui://pins-browser/app"
CONNECT_SERVER = os.environ.get("CONNECT_SERVER", "").rstrip("/")

# Context var for the current request's user session token
_user_token_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_session_token", default=None
)

# Lazy-initialized base client (uses CONNECT_SERVER + CONNECT_API_KEY env vars)
_base_client: Client | None = None

# Lazy-initialized pins board
_board = None

# Pin data sessions: session_key -> (pin_name, DataFrame)
_pin_sessions: dict[str, tuple[str, pd.DataFrame]] = {}


def _get_base_client() -> Client:
    global _base_client
    if _base_client is None:
        _base_client = Client()
    return _base_client


async def _get_visitor_client() -> Client:
    """Get a Client scoped to the visiting user, or fall back to the base client."""
    base = _get_base_client()
    token = _user_token_var.get()
    if token:
        try:
            return await asyncio.to_thread(base.with_user_session_token, token)
        except Exception:
            pass
    return base


def _get_board():
    """Get a cached pins board connected to the Connect server."""
    global _board
    if _board is None:
        _board = board_connect()
    return _board


def _session_key() -> str:
    """Key for per-user pin data sessions."""
    return _user_token_var.get() or "__default__"


def _df_to_json(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-safe list of dicts."""
    return json.loads(
        df.to_json(orient="records", date_format="iso", default_handler=str)
    )


def _is_numeric_type(dtype_str: str) -> bool:
    """Check if a DuckDB type string is numeric."""
    numeric_keywords = [
        "INT",
        "FLOAT",
        "DOUBLE",
        "DECIMAL",
        "NUMERIC",
        "BIGINT",
        "SMALLINT",
        "TINYINT",
        "REAL",
        "HUGEINT",
    ]
    upper = dtype_str.upper()
    return any(kw in upper for kw in numeric_keywords)


mcp = FastMCP(
    name="pins-data-viewer",
    instructions=(
        "MCP server for browsing and exploring pin data on Posit Connect. "
        "Use browse_pins to open the pins data viewer app. Optionally provide a "
        "query to pre-populate the search box. The user browses and explores "
        "pin data within the app. When the user clicks 'Chat with Data', "
        "use the analyze_pin_data tool to retrieve and analyze the data."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI),
    title="Open Pins Data Viewer",
    description=(
        "Open the pins data viewer app to browse and explore pin data on "
        "Posit Connect. Optionally provide a query to pre-populate the search."
    ),
)
async def browse_pins(query: str = "") -> ToolResult:
    """Open the pins data viewer, optionally with a pre-filled search query."""
    msg = "Pins data viewer opened."
    if query:
        msg += f" Searching for: {query}"
    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps({"action": "open", "query": query, "message": msg}),
            )
        ],
    )


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI, visibility=["app"]),
    title="Search Pins",
    description="Search for pins on Posit Connect.",
)
async def do_search(query: str = "") -> ToolResult:
    """Search for pins using the pins SDK (app-only)."""

    def _search():
        board = _get_board()
        raw = board.pin_search(query) if query else board.pin_list()

        # Newer pins versions return a DataFrame
        if isinstance(raw, pd.DataFrame):
            return raw.to_dict(orient="records")

        # Older versions return a list of pin name strings
        if isinstance(raw, list) and raw and isinstance(raw[0], str):
            results = []
            for name in raw[:25]:
                try:
                    meta = board.pin_meta(name)
                    results.append(
                        {
                            "name": name,
                            "title": getattr(meta, "title", "") or name,
                            "description": getattr(meta, "description", "") or "",
                            "type": getattr(meta, "type", "unknown") or "unknown",
                        }
                    )
                except Exception:
                    results.append({"name": name, "title": name, "type": "unknown"})
            return results

        return []

    try:
        results = await asyncio.to_thread(_search)
    except Exception as exc:
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(exc), "results": []}),
                )
            ]
        )

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(
                    {"results": results, "total": len(results), "query": query},
                    default=str,
                ),
            )
        ]
    )


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI, visibility=["app"]),
    title="Load Pin Data",
    description="Load a pin's data into DuckDB and return schema, stats, and preview.",
)
async def load_pin(pin_name: str) -> ToolResult:
    """Load pin data and return metadata, column info, stats, and preview rows."""

    def _load():
        board = _get_board()
        meta = board.pin_meta(pin_name)
        data = board.pin_read(pin_name)

        if not isinstance(data, pd.DataFrame):
            raise ValueError(
                f"Pin '{pin_name}' is not tabular data "
                f"(got {type(data).__name__}). "
                "Only tabular pins (CSV, Arrow, Parquet) are supported."
            )

        df = data

        # Store in session for subsequent queries
        _pin_sessions[_session_key()] = (pin_name, df)

        # Analyse with DuckDB
        conn = duckdb.connect()
        conn.register("data", df)

        schema_df = conn.execute("DESCRIBE data").fetchdf()
        row_count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

        columns: list[dict] = []
        for _, row in schema_df.iterrows():
            col_name = row["column_name"]
            col_type = row["column_type"]
            numeric = _is_numeric_type(col_type)

            if numeric:
                stat_df = conn.execute(
                    f"""
                    SELECT
                        MIN("{col_name}") AS min_val,
                        MAX("{col_name}") AS max_val,
                        ROUND(AVG("{col_name}")::DOUBLE, 4) AS mean_val,
                        ROUND(MEDIAN("{col_name}")::DOUBLE, 4) AS median_val,
                        ROUND(STDDEV("{col_name}")::DOUBLE, 4) AS stddev_val,
                        COUNT(DISTINCT "{col_name}") AS unique_count,
                        COUNT(*) - COUNT("{col_name}") AS null_count
                    FROM data
                    """
                ).fetchdf()
            else:
                stat_df = conn.execute(
                    f"""
                    SELECT
                        COUNT(DISTINCT "{col_name}") AS unique_count,
                        COUNT(*) - COUNT("{col_name}") AS null_count
                    FROM data
                    """
                ).fetchdf()

            stat_row = stat_df.iloc[0].to_dict()
            columns.append(
                {
                    "name": col_name,
                    "type": col_type,
                    "is_numeric": numeric,
                    **{
                        k: (None if pd.isna(v) else v)
                        for k, v in stat_row.items()
                    },
                }
            )

        preview_df = conn.execute("SELECT * FROM data LIMIT 100").fetchdf()
        conn.close()

        return {
            "pin_name": pin_name,
            "title": getattr(meta, "title", "") or pin_name,
            "description": getattr(meta, "description", "") or "",
            "pin_type": getattr(meta, "type", "unknown") or "unknown",
            "row_count": row_count,
            "col_count": len(df.columns),
            "columns": columns,
            "preview_columns": preview_df.columns.tolist(),
            "preview_rows": _df_to_json(preview_df),
        }

    try:
        result = await asyncio.to_thread(_load)
    except Exception as exc:
        return ToolResult(
            content=[
                TextContent(type="text", text=json.dumps({"error": str(exc)}))
            ]
        )

    return ToolResult(
        content=[
            TextContent(type="text", text=json.dumps(result, default=str))
        ]
    )


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI, visibility=["app"]),
    title="Query Pin Data",
    description=(
        "Run a SQL query against the currently loaded pin data. "
        "The table is named 'data'."
    ),
)
async def query_pin(sql: str) -> ToolResult:
    """Execute a SQL query against the loaded pin data (app-only)."""
    key = _session_key()
    if key not in _pin_sessions:
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps({"error": "No pin loaded. Select a pin first."}),
                )
            ]
        )

    _pin_name, df = _pin_sessions[key]

    def _run_query():
        conn = duckdb.connect()
        conn.register("data", df)
        result_df = conn.execute(sql).fetchdf()
        conn.close()

        total = len(result_df)
        truncated = total > 1000
        if truncated:
            result_df = result_df.head(1000)

        return {
            "columns": result_df.columns.tolist(),
            "rows": _df_to_json(result_df),
            "row_count": min(total, 1000),
            "total_rows": total,
            "truncated": truncated,
        }

    try:
        result = await asyncio.to_thread(_run_query)
    except Exception as exc:
        return ToolResult(
            content=[
                TextContent(type="text", text=json.dumps({"error": str(exc)}))
            ]
        )

    return ToolResult(
        content=[
            TextContent(type="text", text=json.dumps(result, default=str))
        ]
    )


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI),
    title="Analyze Pin Data",
    description=(
        "Analyze a pin's data from Posit Connect. Returns schema, summary "
        "statistics, and a sample of the data for discussion. Use this when "
        "asked to analyze or discuss a specific pin."
    ),
)
async def analyze_pin_data(pin_name: str) -> ToolResult:
    """Load pin data and return a summary for LLM analysis."""

    def _analyze():
        board = _get_board()
        meta = board.pin_meta(pin_name)
        data = board.pin_read(pin_name)

        if not isinstance(data, pd.DataFrame):
            return {
                "pin_name": pin_name,
                "error": f"Not tabular data (type: {type(data).__name__})",
            }

        df = data
        conn = duckdb.connect()
        conn.register("data", df)

        schema = conn.execute("DESCRIBE data").fetchdf()
        sample = conn.execute("SELECT * FROM data LIMIT 25").fetchdf()
        conn.close()

        describe = df.describe(include="all")

        return {
            "pin_name": pin_name,
            "title": getattr(meta, "title", "") or pin_name,
            "description": getattr(meta, "description", "") or "",
            "pin_type": getattr(meta, "type", "unknown") or "unknown",
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "schema": _df_to_json(schema),
            "summary_statistics": _df_to_json(describe.reset_index()),
            "sample_rows": _df_to_json(sample),
        }

    try:
        result = await asyncio.to_thread(_analyze)
    except Exception as exc:
        return ToolResult(
            content=[
                TextContent(type="text", text=json.dumps({"error": str(exc)}))
            ]
        )

    return ToolResult(
        content=[
            TextContent(type="text", text=json.dumps(result, default=str))
        ]
    )


# ---------------------------------------------------------------------------
# Resource (UI)
# ---------------------------------------------------------------------------

_local_server = f"http://localhost:{os.environ.get('PORT', '3002')}"
_csp_resource_domains = ["https://unpkg.com"]
_csp_connect_domains = [d for d in [CONNECT_SERVER, _local_server] if d] or None


@mcp.resource(
    RESOURCE_URI,
    name="Pins Data Viewer UI",
    description="Interactive data viewer for exploring pin data on Posit Connect",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=_csp_resource_domains,
            connect_domains=_csp_connect_domains,
        )
    ),
)
async def pins_browser_resource() -> str:
    """Serve the pins data viewer UI from app.html."""
    return (HERE / "app.html").read_text()


# ---------------------------------------------------------------------------
# Middleware & FastAPI setup
# ---------------------------------------------------------------------------


class UserSessionMiddleware(BaseHTTPMiddleware):
    """Extract the Posit-Connect-User-Session-Token header."""

    async def dispatch(self, request, call_next):
        token = request.headers.get("Posit-Connect-User-Session-Token")
        _user_token_var.set(token)
        return await call_next(request)


cors_middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
            "Posit-Connect-User-Session-Token",
        ],
        expose_headers=["mcp-session-id"],
    )
]

mcp_app = mcp.http_app(path="/mcp", stateless_http=True, middleware=cors_middleware)
app = FastAPI(
    title="Pins Data Viewer MCP Server",
    lifespan=mcp_app.lifespan,
)
app.add_middleware(UserSessionMiddleware)


@app.get("/", response_class=HTMLResponse)
async def get_index_page(request: Request):
    endpoint = urllib.parse.urljoin(str(request.url), "mcp")
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{mcp.name}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; }}
    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
    pre {{ background: #f0f0f0; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
    .tool {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem; margin-bottom: 0.75rem; }}
    .tool h3 {{ margin: 0 0 0.5rem 0; }}
    .tool p {{ margin: 0; color: #666; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; margin-left: 0.5rem; }}
    .badge-ui {{ background: #e8f5e9; color: #2e7d32; }}
  </style>
</head>
<body>
  <h1>{mcp.name}</h1>
  <p>MCP endpoint: <code>{endpoint}</code></p>
  <p>Connect server: <code>{CONNECT_SERVER or "(not configured)"}</code></p>
  <h2>Tools</h2>
  <div class="tool">
    <h3>browse_pins <span class="badge badge-ui">has UI</span></h3>
    <p>Browse and explore pin data on Posit Connect</p>
  </div>
  <div class="tool">
    <h3>analyze_pin_data</h3>
    <p>Analyze a pin's data (schema, stats, sample) for LLM discussion</p>
  </div>
  <h2>Connect to this server</h2>
  <pre>{{"mcpServers": {{
  "pins-viewer": {{
    "type": "streamable-http",
    "url": "{endpoint}"
  }}
}}}}</pre>
</body>
</html>"""


app.mount("/", mcp_app)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "3002"))
    print(f"Pins Data Viewer MCP Server listening on http://localhost:{port}")
    print(f"  MCP endpoint: http://localhost:{port}/mcp")
    print(f"  Connect server: {CONNECT_SERVER or '(not configured)'}")
    uvicorn.run(app, host="0.0.0.0", port=port)
