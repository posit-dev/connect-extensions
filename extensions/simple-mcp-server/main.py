import contextlib
import json
import traceback
import urllib.parse

import pandas as pd
from cachetools import TTLCache, cached
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from posit import connect
from posit.connect.errors import ClientError
from sklearn.datasets import load_iris

# --- Connect Client Initialization ---
client = connect.Client()

# Cache one Connect client per viewer session token (1h TTL) so repeated tool
# calls from the same viewer don't re-exchange the token on every request. Bounded so
# a long-running server with many distinct viewers can't grow the cache without limit;
# the least-recently-used client is evicted past the cap.
client_cache = TTLCache(maxsize=1024, ttl=3600)


@cached(client_cache)
def get_visitor_client(token: str | None) -> connect.Client:
    """Return a Connect client scoped to the viewer's session token (cached)."""
    if token:
        return client.with_user_session_token(token)
    else:
        return client


# --- FastMCP Server Initialization ---
mcp = FastMCP(
    name="MCP Server",
    instructions="MCP server for dataset operations and Connect 'whoami' via FastAPI.",
    streamable_http_path="/mcp",
    stateless_http=True,
    # Connect terminates and authenticates requests in front of this app, and the
    # served host varies per deployment, so disable the SDK's default DNS-rebinding
    # Host check that would otherwise reject the Connect host.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)

# --- Datasets ---
# Simple in-memory datasets for demonstration
_datasets_store = {
    "iris": lambda: pd.DataFrame(data=load_iris(as_frame=True).frame),
    "sample_data": lambda: pd.DataFrame(
        {"A": [1, 2, 3, 4, 5], "B": [5, 4, 3, 2, 1], "C": ["x", "y", "x", "z", "y"]}
    ),
}


# --- MCP Tool Implementations ---
@mcp.tool()
def list_known_datasets() -> str:
    """Lists available dataset names."""
    return str(list(_datasets_store.keys()))


@mcp.tool()
def calculate_summary_statistics(dataset_name: str) -> str:
    """
    Calculates summary statistics for a specified dataset.
    Returns the summary as a string or an error.
    """
    if dataset_name not in _datasets_store:
        raise ToolError(f"Dataset '{dataset_name}' not found.")
    try:
        df = _datasets_store[dataset_name]()
        summary = df.describe(include="all").to_string()
        return summary
    except Exception as e:
        raise ToolError(f"Error processing dataset '{dataset_name}': {str(e)}")


@mcp.tool()
async def connect_whoami(context: Context) -> str:
    """
    Calls the Posit Connect /me endpoint using the visitor's session token.
    This tool requires a "Connect Visitor API Key" integration to be configured.
    """
    # The underlying Starlette request, where Connect's injected headers live.
    http_request = context.request_context.request
    if http_request is None:
        raise ToolError(
            "Request context not available. This tool requires an HTTP-based transport."
        )

    # Connect injects this header on every request from a logged-in viewer. Reading
    # it (instead of a stored API key) is what lets the tool act as the viewer: the
    # AI assistant calls connect_whoami and Connect answers for whoever is using it.
    session_token = http_request.headers.get("posit-connect-user-session-token")

    if not session_token:
        raise ToolError(
            "Session token not available. This tool must be called from content running on Posit Connect."
        )

    try:
        visitor_client = get_visitor_client(session_token)
        return json.dumps(visitor_client.me)
    except ClientError as e:
        if e.error_code == 212:
            raise ToolError(
                'No "Connect Visitor API Key" integration configured. In the content '
                'settings, on the "Access" tab, add a "Connect Visitor API Key" '
                'integration under "Integrations".'
            )
        raise ToolError(f"Error calling Connect API: {str(e)}")
    except Exception as e:
        raise ToolError(f"Error calling Connect API: {str(e)}")


async def get_tools_info():
    # List the registered tools through the SDK's public API to render them on
    # the landing page.
    tools = []
    for tool in await mcp.list_tools():
        schema = tool.inputSchema or {}
        parameters = {}
        for prop_name, prop in schema.get("properties", {}).items():
            parameters[prop_name] = {
                "type": prop.get("type", ""),
                "required": False,
            }

        for required_prop_name in schema.get("required", []):
            if required_prop_name in parameters:
                parameters[required_prop_name]["required"] = True

        tools.append(
            {
                "name": tool.name,
                "description": tool.description or "No description available.",
                "parameters": parameters,
            }
        )
    return tools


mcp_app = mcp.streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Run the MCP session manager for the mounted streamable-HTTP app.
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="MCP Server", lifespan=lifespan)
templates = Jinja2Templates(directory=".")


@app.get("/")
async def get_index_page(request: Request):
    """Serves the HTML index page using a Jinja2 template."""
    tools = await get_tools_info()
    endpoint = urllib.parse.urljoin(request.url._url, "mcp")

    # Look up who is viewing the page from the session token Connect injects (the
    # same lookup connect_whoami does), so the page can greet them by name and show
    # that tools run as the viewer, with no API key. Stays None off Connect, or when
    # no Visitor API Key integration is configured.
    viewer_name = None
    session_token = request.headers.get("posit-connect-user-session-token")
    if session_token:
        try:
            me = get_visitor_client(session_token).me
            # Prefer the viewer's display name; fall back to username, since not
            # every Connect user has a first and last name set.
            display_name = f"{me.get('first_name', '')} {me.get('last_name', '')}".strip()
            viewer_name = display_name or me.get("username")
        except ClientError as e:
            # 212 means no Visitor API Key integration is configured; that's the
            # expected case here, and the page's info box already explains how to add
            # it, so just leave the greeting off. Log any other Connect error so the
            # missing greeting has a visible cause.
            if e.error_code != 212:
                traceback.print_exc()
        except Exception:
            # e.g. a malformed token exchange; log it and leave the greeting off.
            traceback.print_exc()

    return templates.TemplateResponse(
        request,
        "index.html.jinja",
        {
            "title": "MCP Server",
            "endpoint": endpoint,
            "tools": tools,
            "viewer_name": viewer_name,
        },
    )


app.mount("/", mcp_app)


# --- Uvicorn Runner (for local development) ---
if __name__ == "__main__":
    import asyncio

    import uvicorn

    print("Starting FastAPI server with MCP...")
    print(f"MCP Server Name: {mcp.name}")
    print("Registered MCP Tools:")
    for tool in asyncio.run(mcp.list_tools()):
        print(f"  - {tool.name}")

    uvicorn.run(app, host="127.0.0.1", port=8001)
