import contextlib
import json
import os
import urllib

import pandas as pd
from cachetools import TTLCache, cached
from fastapi import FastAPI, Request, Header, Body
from fastapi.templating import Jinja2Templates
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from posit import connect
from posit.connect.errors import ClientError
from sklearn.datasets import load_iris

# --- Connect Client Initialization ---
client = connect.Client()

# Create cache with TTL=1hour for visitor clients
client_cache = TTLCache(maxsize=float("inf"), ttl=3600)


@cached(client_cache)
def get_visitor_client(token: str | None) -> connect.Client:
    """Create and cache API client per token with 1 hour TTL"""
    if token:
        return client.with_user_session_token(token)
    else:
        return client

# --- FastMCP Server Initialization ---
mcp = FastMCP(
    name="Simple MCP Server",
    instructions="MCP server for dataset operations and Connect 'whoami' via FastAPI.",
    stateless_http=True,
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
    This tool requires a Visitor API Key integration to be configured.
    """
    # context.request is a starlette.requests.Request
    http_request = context.request_context.request
    if http_request is None:
        raise ToolError(
            "Request context not available. This tool requires an HTTP-based transport."
        )

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
                "No Visitor API Key integration configured. Please add a Connect integration in the content settings."
            )
        raise ToolError(f"Error calling Connect API: {str(e)}")
    except Exception as e:
        raise ToolError(f"Error calling Connect API: {str(e)}")


def get_tools_info():
    tools = []
    for tool_name, tool_def in mcp._tool_manager._tools.items():
        parameters = {}
        for prop_name, prop in tool_def.parameters["properties"].items():
            parameters[prop_name] = {
                "name": prop["title"],
                "type": prop["type"],
                "required": False,
            }

        if "required" in tool_def.parameters:
            for required_prop_name in tool_def.parameters["required"]:
                if required_prop_name in parameters:
                    parameters[required_prop_name]["required"] = True

        tools.append(
            {
                "name": tool_name,
                "description": tool_def.description or "No description available.",
                "parameters": parameters,
            }
        )
    return tools


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(title="Simple MCP Server with FastAPI", lifespan=mcp_app.lifespan)
templates = Jinja2Templates(directory=".")


@app.get("/")
async def get_index_page(request: Request):
    """Serves the HTML index page using a Jinja2 template."""
    tools = get_tools_info()
    endpoint = urllib.parse.urljoin(request.url._url, "mcp")
    return templates.TemplateResponse(
        "index.html.jinja",
        {
            "request": request,
            "server_name": mcp.name,
            "endpoint": endpoint,
            "tools": tools,
        },
    )


# --- Visitor Integration API Endpoints ---
@app.get("/api/visitor-auth")
async def integration_status(posit_connect_user_session_token: str = Header(None)):
    """
    Check if a Visitor API Key integration is configured.
    Returns authorized=False if no integration is set up.
    """
    if os.getenv("RSTUDIO_PRODUCT") == "CONNECT":
        if not posit_connect_user_session_token:
            return {"authorized": False}
        try:
            get_visitor_client(posit_connect_user_session_token)
        except ClientError as err:
            if err.error_code == 212:
                return {"authorized": False}
            raise

    return {"authorized": True}


@app.put("/api/visitor-auth")
async def set_integration(integration_guid: str = Body(..., embed=True)):
    """Associate a Visitor API Key integration with this content."""
    if os.getenv("RSTUDIO_PRODUCT") == "CONNECT":
        content_guid = os.getenv("CONNECT_CONTENT_GUID")
        content = client.content.get(content_guid)
        content.oauth.associations.update(integration_guid)
    else:
        raise ClientError(
            error_code=400,
            message="This endpoint is only available when running on Posit Connect.",
        )
    return {"status": "success"}


@app.get("/api/integrations")
async def get_integrations():
    """Get available Connect Visitor API Key integrations."""
    integrations = client.oauth.integrations.find()
    # Filter for Connect integrations with Admin or Publisher max role
    eligible_integrations = [
        i
        for i in integrations
        if i["template"] == "connect"
        and i["config"]["max_role"] in ("Admin", "Publisher")
    ]
    return eligible_integrations[0] if eligible_integrations else None


app.mount("/", mcp_app)


# --- Uvicorn Runner (for local development) ---
if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI server with MCP...")
    print(f"MCP Server Name: {mcp.name}")
    print("Registered MCP Tools:")
    for tool_name in mcp._tool_manager._tools:
        print(f"  - {tool_name}")

    uvicorn.run(app, host="127.0.0.1", port=8001)
