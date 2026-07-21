# Contributing to the FastAPI: MCP Server extension

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/)

## Setup

Run `uv sync` to install dependencies.

## Development

Run `uv run python main.py` to start the server locally on
`http://127.0.0.1:8001`, with the MCP endpoint at `/mcp`.

## Tool Development

### Adding New Tools

To add new MCP tools, use the `@mcp.tool()` decorator:

```python
@mcp.tool()
def your_new_tool(parameter: str) -> str:
    """
    Description of what your tool does.

    Args:
        parameter: Description of the parameter

    Returns:
        Description of the return value
    """
    # Your tool implementation
    return "result"
```

### Error Handling

Use `ToolError` for proper error handling:

```python
from mcp.server.fastmcp.exceptions import ToolError

@mcp.tool()
def example_tool(input_value: str) -> str:
    if not input_value:
        raise ToolError("Input value cannot be empty")
    return f"Processed: {input_value}"
```

## Authentication

There are two distinct layers, and only the first is something a client sets:

- **Reaching the content** (transport): an MCP client authenticates to Connect with a
  Connect API key in the standard `Authorization` header (`Authorization: Key
  YOUR_API_KEY`). This is how the request reaches the deployed server.
- **Acting as the viewer** (tools like `connect_whoami`): the tool reads the
  `Posit-Connect-User-Session-Token` header that Connect injects automatically for the
  logged-in viewer and exchanges it for a viewer-scoped client. There is no header to
  set for this, and it requires a Visitor API Key integration on the content.

## Bundle

The files sent in the deployment bundle are:

- `main.py`
- `index.html.jinja`
- `requirements.txt`

`pyproject.toml`, `uv.lock`, and repo docs are not bundled.

## Changelog

Update the [CHANGELOG](./CHANGELOG.md) using the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, referencing the
PR number, and bump `extension.version` in `manifest.json` to trigger a release.
