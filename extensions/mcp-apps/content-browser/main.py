"""Connect Content Browser MCP App Server — search and chat with static content.

Demonstrates MCP Apps with FastMCP v3 on Connect:
- Search tool queries Connect's /v1/search/content API (scoped to static content)
- Interactive UI displays top K results with content preview
- "Send to Chat" fetches raw HTML and sends it to the LLM for discussion
- Uses posit-sdk with user session token for visitor-scoped API access

When deployed to Connect, the Posit-Connect-User-Session-Token header is
used to exchange for a visitor API key so searches run as the visiting user.
Locally, falls back to the CONNECT_API_KEY environment variable.

Setup:
    pip install -r requirements.txt
    export CONNECT_SERVER=https://connect.example.com
    export CONNECT_API_KEY=your-api-key

Usage:
    python main.py                  # HTTP mode (port 3002)

Testing with basic-host:
    cd ../basic-host && npm install
    SERVERS='["http://localhost:3002/mcp"]' npm run start
"""

from __future__ import annotations

import asyncio
import base64
import contextvars
import json
import os
import secrets
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.tools.tool import ToolResult
from mcp.types import ImageContent, TextContent
from posit.connect import Client
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

HERE = Path(__file__).parent
RESOURCE_URI = "ui://content-browser/app"
CONNECT_SERVER = os.environ.get("CONNECT_SERVER", "").rstrip("/")
STATIC_TYPES = "jupyter-static,quarto-static,rmd-static,static"

# Context vars for the current request
_user_token_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_session_token", default=None
)
_server_base_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "server_base", default=""
)

# Lazy-initialized base client (uses CONNECT_SERVER + CONNECT_API_KEY env vars)
_base_client: Client | None = None

# Cache of visitor clients keyed by proxy session ID.
# Each entry maps sid -> (user_token, Client).
# TODO: add TTL-based expiry for production use.
_visitor_clients: dict[str, tuple[str, Client]] = {}


def _get_base_client() -> Client:
    global _base_client
    if _base_client is None:
        _base_client = Client()
    return _base_client


async def _get_visitor_client() -> Client:
    """Get a Client scoped to the visiting user, or fall back to the base client.

    Both search and content proxy use this same client, so search results are
    naturally scoped to content the user can view.  When running locally without
    a user session token the base client (CONNECT_API_KEY) is used instead —
    if that key belongs to an admin, search will return all content.
    """
    base = _get_base_client()
    token = _user_token_var.get()
    if token:
        try:
            return await asyncio.to_thread(base.with_user_session_token, token)
        except Exception:
            pass
    return base


async def _get_or_create_proxy_session() -> str:
    """Return a proxy session ID for the current user, creating one if needed."""
    token = _user_token_var.get() or ""
    # Reuse existing session for the same user token
    for sid, (t, _client) in _visitor_clients.items():
        if t == token:
            return sid
    client = await _get_visitor_client()
    sid = secrets.token_urlsafe(16)
    _visitor_clients[sid] = (token, client)
    return sid


mcp = FastMCP(
    name="content-browser-server",
    instructions=(
        "MCP server for browsing and chatting with static content on Posit Connect. "
        "Use search_content to open the content browser app. Optionally provide a "
        "query to pre-populate the search box. The user browses, searches, and "
        "previews content within the app. When the user clicks 'Chat with Content' "
        "in the app, the selected content is sent to you for discussion."
    ),
)


async def _search_connect(query: str, page_size: int = 10) -> dict:
    """Call Connect's /v1/search/content API, scoped to static content types."""
    client = await _get_visitor_client()
    full_query = f"type:{STATIC_TYPES} {query}".strip()
    params = {
        "q": full_query,
        "page_size": min(page_size, 500),
        "include": "owner,tags",
    }
    resp = await asyncio.to_thread(
        client.get, "v1/search/content", params=params
    )
    return resp.json()


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI),
    title="Open Content Browser",
    description=(
        "Open the content browser app to search and preview static content on "
        "Posit Connect. Optionally provide a query to pre-populate the search box. "
        "The user browses and searches within the app UI. No content data is "
        "returned to the conversation — use 'Chat with Content' in the app to "
        "send selected content to the LLM."
    ),
)
async def search_content(query: str = "") -> ToolResult:
    """Open the content browser, optionally with a pre-filled search query."""
    msg = "Content browser opened."
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
    title="Search Static Content",
    description=(
        "Search for static content items (reports, notebooks, documents) on Posit Connect. "
        "Results are scoped to static app modes: jupyter-static, quarto-static, rmd-static, static."
    ),
)
async def do_search(query: str = "", page_size: int = 10) -> ToolResult:
    """Search Connect for static content items (app-only)."""
    data = await _search_connect(query, page_size)

    sid = await _get_or_create_proxy_session()
    server_base = _server_base_var.get("")

    results = []
    for item in data.get("results", []):
        owner = item.get("owner") or {}
        content_url = item.get("content_url", "")

        # Build proxy URL: {server_base}/proxy/{sid}/content/{guid}/
        proxy_url = ""
        if content_url and server_base:
            parsed = urllib.parse.urlparse(content_url)
            proxy_url = f"{server_base}/proxy/{sid}{parsed.path}"

        results.append(
            {
                "guid": item["guid"],
                "name": item.get("name", ""),
                "title": item.get("title") or item.get("name", "Untitled"),
                "description": item.get("description", ""),
                "app_mode": item.get("app_mode", ""),
                "content_url": content_url,
                "proxy_url": proxy_url,
                "dashboard_url": item.get("dashboard_url", ""),
                "owner_username": owner.get("username", ""),
                "owner_first_name": owner.get("first_name", ""),
                "owner_last_name": owner.get("last_name", ""),
                "created_time": item.get("created_time", ""),
                "last_deployed_time": item.get("last_deployed_time", ""),
                "tags": [
                    {"name": t["name"], "id": t["id"]}
                    for t in item.get("tags", [])
                ],
            }
        )

    payload = {
        "total": data.get("total", 0),
        "results": results,
        "query": query,
    }
    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))],
    )


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI, visibility=["app"]),
    title="Fetch Content for Preview",
    description="Fetch a content item's HTML for srcdoc preview",
)
async def fetch_preview_html(
    content_url: str, proxy_url: str = ""
) -> ToolResult:
    """Fetch content HTML for srcdoc preview.

    When proxy_url is HTTPS, sub-resources can load from it directly (CSP allows
    HTTPS origins), so we just inject a <base href> — fast path.
    When proxy_url is HTTP (local dev), mixed content blocks sub-resource loading,
    so we inline all CSS, JS, and images server-side — slow but works everywhere.
    """
    client = await _get_visitor_client()
    try:
        resp = await asyncio.to_thread(
            client.session.get, content_url, allow_redirects=True, timeout=30
        )
        resp.raise_for_status()
    except Exception as exc:
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(exc), "content_url": content_url}),
                )
            ],
        )

    use_base_href = proxy_url.startswith("https://")

    if use_base_href:
        # Fast path: inject <base href> pointing to HTTPS proxy so browser
        # can load sub-resources directly (no mixed content issue).
        href = proxy_url if proxy_url.endswith("/") else proxy_url + "/"
        base_tag = f'<base href="{href}">'
        html = resp.text
        if "<head>" in html:
            html = html.replace("<head>", "<head>" + base_tag, 1)
        elif "<html>" in html:
            html = html.replace("<html>", "<html><head>" + base_tag + "</head>", 1)
        else:
            html = base_tag + html
    else:
        # Slow path: inline everything server-side to avoid mixed content.
        soup = BeautifulSoup(resp.text, "html.parser")

        # Inline CSS: <link rel="stylesheet" href="..."> → <style>...</style>
        for link in soup.find_all("link", rel="stylesheet", href=True):
            css_url = urllib.parse.urljoin(content_url, link["href"])
            try:
                css_resp = await asyncio.to_thread(
                    client.session.get, css_url, allow_redirects=True, timeout=15
                )
                if css_resp.status_code == 200:
                    style_tag = soup.new_tag("style")
                    style_tag.string = css_resp.text
                    link.replace_with(style_tag)
                else:
                    print(f"[preview] CSS {css_resp.status_code}: {css_url}")
            except Exception as exc:
                print(f"[preview] CSS error {css_url}: {exc}")

        # Inline JS: <script src="..."> → <script>...</script>
        for script in soup.find_all("script", src=True):
            js_url = urllib.parse.urljoin(content_url, script["src"])
            try:
                js_resp = await asyncio.to_thread(
                    client.session.get, js_url, allow_redirects=True, timeout=15
                )
                if js_resp.status_code == 200:
                    del script["src"]
                    script.string = js_resp.text
                else:
                    print(f"[preview] JS {js_resp.status_code}: {js_url}")
            except Exception as exc:
                print(f"[preview] JS error {js_url}: {exc}")

        # Inline images: <img src="..."> → <img src="data:...">
        for img in soup.find_all("img", src=True):
            if img["src"].startswith("data:"):
                continue
            img_url = urllib.parse.urljoin(content_url, img["src"])
            try:
                img_resp = await asyncio.to_thread(
                    client.session.get, img_url, allow_redirects=True, timeout=15
                )
                ctype = img_resp.headers.get("content-type", "image/png").split(";")[0]
                if img_resp.status_code == 200 and len(img_resp.content) < 2 * 1024 * 1024:
                    b64 = base64.b64encode(img_resp.content).decode("ascii")
                    img["src"] = f"data:{ctype};base64,{b64}"
                else:
                    print(
                        f"[preview] img skip {img_url}: "
                        f"status={img_resp.status_code} size={len(img_resp.content)}"
                    )
            except Exception as exc:
                print(f"[preview] img error {img_url}: {exc}")

        html = str(soup)

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps({"html": html, "content_url": content_url}),
            )
        ],
    )


@mcp.tool(
    app=AppConfig(resource_uri=RESOURCE_URI),
    title="Fetch Content for Analysis",
    description=(
        "Fetch a static content item from Posit Connect and extract its text "
        "as markdown plus up to 5 embedded images. Use this when asked to "
        "analyze or discuss a specific content item."
    ),
)
async def fetch_content_html(content_url: str) -> ToolResult:
    """Fetch content, extract main body text as markdown, and include images."""
    client = await _get_visitor_client()
    resp = await asyncio.to_thread(
        client.session.get, content_url, allow_redirects=True, timeout=30
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Strip noise elements globally
    for tag in soup.find_all(
        ["script", "style", "nav", "header", "footer", "noscript", "svg"]
    ):
        tag.decompose()
    for tag in soup.find_all(attrs={"role": "navigation"}):
        tag.decompose()

    # Find the main content area
    content_el = (
        soup.select_one("main")
        or soup.select_one("article")
        or soup.select_one("div#quarto-content")
        or soup.select_one("div.main-container")
        or soup.body
        or soup
    )

    # Remove sidebars and search widgets within content
    for sel in [
        ".sidebar", "#quarto-sidebar", "#quarto-margin-sidebar",
        ".quarto-search", ".quarto-title-banner",
    ]:
        for tag in content_el.select(sel):
            tag.decompose()

    # Collect image URLs before converting to markdown
    img_urls = []
    for img in content_el.find_all("img", src=True):
        abs_url = urllib.parse.urljoin(content_url, img["src"])
        img_urls.append(abs_url)

    markdown = md(str(content_el), heading_style="ATX")

    # Fetch images (first 5, max 2 MB each)
    image_items: list[ImageContent] = []
    image_errors: list[str] = []
    max_image_bytes = 2 * 1024 * 1024
    for url in img_urls[:5]:
        try:
            img_resp = await asyncio.to_thread(
                client.session.get, url, allow_redirects=True, timeout=15
            )
            ctype = img_resp.headers.get("content-type", "")
            if img_resp.status_code != 200:
                image_errors.append(f"{url}: HTTP {img_resp.status_code}")
            elif not ctype.startswith("image/"):
                image_errors.append(f"{url}: unexpected type {ctype}")
            elif len(img_resp.content) > max_image_bytes:
                image_errors.append(f"{url}: too large ({len(img_resp.content)} bytes)")
            else:
                image_items.append(
                    ImageContent(
                        type="image",
                        data=base64.b64encode(img_resp.content).decode("ascii"),
                        mimeType=ctype.split(";")[0],
                    )
                )
        except Exception as exc:
            image_errors.append(f"{url}: {exc}")

    if image_errors:
        print(f"[fetch_content_html] image fetch errors: {image_errors}")

    result_content: list[TextContent | ImageContent] = [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "content_url": content_url,
                    "markdown": markdown,
                    "image_count": len(image_items),
                    "image_errors": image_errors,
                }
            ),
        )
    ]
    result_content.extend(image_items)
    return ToolResult(content=result_content)


# Build CSP domains.
# resource_domains: CSS, JS, images, fonts (unpkg + Connect + local proxy)
# connect_domains: fetch/XHR from app JS
# frame_domains: nested iframes (direct iframe.src for HTTPS mode)
# base_uri_domains: allowed <base href> origins (proxy URL in srcdoc)
_local_server = f"http://localhost:{os.environ.get('PORT', '3002')}"
_content_origins = [d for d in [CONNECT_SERVER, _local_server] if d]
_csp_resource_domains = ["https://unpkg.com"] + _content_origins
_csp_connect_domains = _content_origins or None
_csp_frame_domains = _content_origins or None
_csp_base_uri_domains = _content_origins or None


@mcp.resource(
    RESOURCE_URI,
    name="Content Browser UI",
    description="Interactive content browser for searching and previewing static Connect content",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=_csp_resource_domains,
            connect_domains=_csp_connect_domains,
            frame_domains=_csp_frame_domains,
            base_uri_domains=_csp_base_uri_domains,
        )
    ),
)
async def content_browser_resource() -> str:
    """Serve the content browser UI from app.html."""
    return (HERE / "app.html").read_text()


# --- Middleware to capture user session token ---


class UserSessionMiddleware(BaseHTTPMiddleware):
    """Extract the Posit-Connect-User-Session-Token header and capture server base URL."""

    async def dispatch(self, request, call_next):
        token = request.headers.get("Posit-Connect-User-Session-Token")
        _user_token_var.set(token)
        _server_base_var.set(str(request.base_url).rstrip("/"))
        return await call_next(request)


# --- FastAPI wrapping ---

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
    title="Content Browser MCP Server",
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
  <p>Connect server: <code>{CONNECT_SERVER or "(not configured)"}</code></p>
  <div class="tools">
    <h2>Tools</h2>
    <div class="tool">
      <h3>search_content <span class="badge badge-ui">has UI</span></h3>
      <p>Search for static content items on Posit Connect (reports, notebooks, documents)</p>
    </div>
    <div class="tool">
      <h3>fetch_content_html <span class="badge badge-app">app-only</span></h3>
      <p>Fetch raw HTML of a content item for LLM discussion</p>
    </div>
  </div>
  <div class="tools">
    <h2>Connect to this server</h2>
    <pre>{{"mcpServers": {{
  "content-browser": {{
    "type": "streamable-http",
    "url": "{endpoint}"
  }}
}}}}</pre>
  </div>
</body>
</html>"""


# --- Content proxy: authenticated reverse proxy for iframe previews ---

_ALLOWED_PROXY_PREFIXES = ("content/",)


@app.get("/proxy/{sid}/{path:path}")
async def proxy_content(sid: str, path: str, request: Request):
    """Reverse-proxy a Connect content URL using the visitor's API key.

    The sid (session ID) maps to a cached visitor Client so that proxied
    requests are scoped to the user who initiated the search.  Sub-resources
    (CSS, JS, images) use relative URLs that naturally include the sid, so
    they are also authenticated.
    """
    entry = _visitor_clients.get(sid)
    if not entry:
        return Response(status_code=403, content="Invalid proxy session")

    if not any(path.startswith(p) for p in _ALLOWED_PROXY_PREFIXES):
        return Response(status_code=403, content="Forbidden path")

    _token, client = entry
    target_url = f"{CONNECT_SERVER}/{path}"
    if str(request.query_params):
        target_url += "?" + str(request.query_params)

    try:
        resp = await asyncio.to_thread(
            client.session.get, target_url, allow_redirects=True, timeout=30
        )
    except Exception as exc:
        print(f"[proxy] ERROR {target_url}: {exc}")
        return Response(status_code=502, content=f"Upstream error: {exc}")

    print(
        f"[proxy] {resp.status_code} {target_url} "
        f"type={resp.headers.get('content-type', '?')} "
        f"len={len(resp.content)}"
    )

    # Forward content-type and cache headers
    headers = {}
    for key in ("cache-control", "etag", "last-modified"):
        if key in resp.headers:
            headers[key] = resp.headers[key]

    content_type = resp.headers.get("content-type", "application/octet-stream")
    body = resp.content

    # Inject debug relay script into HTML responses so iframe console
    # output is forwarded to the parent app's debug panel via postMessage.
    if "text/html" in content_type:
        try:
            html_text = body.decode("utf-8", errors="replace")
            debug_script = (
                "<script>"
                "(function(){"
                "var p=window.parent;if(p===window)return;"
                "function s(l,a){try{p.postMessage({type:'__iframe_debug__',"
                "level:l,data:Array.from(a).map(function(x){"
                "return typeof x==='object'?JSON.stringify(x):String(x)"
                "}).join(' ')},'*')}catch(e){}}"
                "var _l=console.log,_w=console.warn,_e=console.error;"
                "console.log=function(){_l.apply(console,arguments);s('info',arguments)};"
                "console.warn=function(){_w.apply(console,arguments);s('warn',arguments)};"
                "console.error=function(){_e.apply(console,arguments);s('error',arguments)};"
                "window.addEventListener('error',function(e){"
                "s('error',['Uncaught: '+e.message+' '+(e.filename||'')+':'+(e.lineno||'')])});"
                "window.addEventListener('unhandledrejection',function(e){"
                "s('error',['Unhandled rejection: '+e.reason])});"
                "s('info',['iframe debug relay loaded: '+location.href])"
                "})();"
                "</script>"
            )
            if "</body>" in html_text:
                html_text = html_text.replace(
                    "</body>", debug_script + "</body>", 1
                )
            elif "</html>" in html_text:
                html_text = html_text.replace(
                    "</html>", debug_script + "</html>", 1
                )
            else:
                html_text += debug_script
            body = html_text.encode("utf-8")
        except Exception:
            pass  # If decode fails, serve original bytes

    return Response(
        content=body,
        status_code=resp.status_code,
        media_type=content_type,
        headers=headers,
    )


app.mount("/", mcp_app)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "3002"))
    print(f"Content Browser MCP Server listening on http://localhost:{port}")
    print(f"  MCP endpoint: http://localhost:{port}/mcp")
    print(f"  Index page:   http://localhost:{port}/")
    print(f"  Connect server: {CONNECT_SERVER or '(not configured)'}")
    uvicorn.run(app, host="0.0.0.0", port=port)
