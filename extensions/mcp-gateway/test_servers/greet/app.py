import os
from urllib.parse import urlparse

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

mcp = FastMCP("My MCP Server")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

# Configure trusted host middleware for DNS rebinding protection.
# On Connect, derive allowed hosts from the CONNECT_SERVER environment variable.
middleware = []
connect_server = os.environ.get("CONNECT_SERVER", "")
if connect_server:
    parsed = urlparse(connect_server)
    host = (parsed.netloc or parsed.path).rstrip("/")
    if host:
        middleware.append(
            Middleware(TrustedHostMiddleware, allowed_hosts=[host])
        )

# Create the ASGI app for deployment.
# stateless_http: each request is independent (required for load-balanced deployments)
# json_response: return JSON instead of SSE streams
app = mcp.http_app(
    stateless_http=True,
    json_response=True,
    middleware=middleware,
)
