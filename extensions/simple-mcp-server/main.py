import contextlib
import json
import pandas as pd
from sklearn.datasets import load_iris
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from posit.connect.client import Client as ConnectClient
import urllib

# --- FastMCP Server Initialization ---
mcp = FastMCP(
    name="SimpleDataServer",
    instructions="MCP server for dataset operations and Connect 'whoami' via FastAPI.",
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


# This tool is unable to be used in conjunction with the Simple Shiny Chat app 
# @mcp.tool()
# async def connect_whoami(context: Context) -> str:
#     """
#     Calls the Posit Connect /me endpoint using an API key from the Authorization header.
#     The Authorization header should be in the format: 'Key YOUR_API_KEY'.
#     """

#     # context.request is a starlette.requests.Request
#     http_request = context.request_context.request
#     if http_request is None:
#         raise ToolError(
#             "Request context not available. This tool requires an HTTP-based transport."
#         )

#     auth_header = http_request.headers.get("x-mcp-authorization")

#     if not auth_header:
#         raise ToolError("Authorization header is missing.")

#     parts = auth_header.split()
#     if len(parts) != 2 or parts[0].lower() != "key":
#         raise ToolError(
#             "Invalid Authorization header format. Expected 'Key YOUR_API_KEY'."
#         )

#     api_key = parts[1]

#     try:
#         connect_client = ConnectClient(api_key=api_key)
#         return json.dumps(connect_client.me)
#     except Exception as e:
#         raise ToolError(f"Error calling Connect API: {str(e)}")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="Simple MCP Server with FastAPI", lifespan=lifespan)
templates = Jinja2Templates(directory=".")


@app.get("/")
async def get_index_page(request: Request):
    """Serves the HTML index page using a Jinja2 template."""
    tools_info = []
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

        tools_info.append(
            {
                "name": tool_name,
                "description": tool_def.description or "No description available.",
                "parameters": parameters,
            }
        )
    endpoint = urllib.parse.urljoin(request.url._url, "mcp")
    return templates.TemplateResponse(
        "index.html.jinja",
        {
            "request": request,
            "server_name": mcp.name,
            "endpoint": endpoint,
            "tools": tools_info,
        },
    )


app.mount("/", mcp.streamable_http_app())


# --- Uvicorn Runner (for local development) ---
if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI server with MCP...")
    print(f"MCP Server Name: {mcp.name}")
    print("Registered MCP Tools:")
    for tool_name in mcp._tool_manager._tools:
        print(f"  - {tool_name}")

    uvicorn.run(app, host="127.0.0.1", port=8001)
