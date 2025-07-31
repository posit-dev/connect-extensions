# Contributing to the Simple MCP Server Extension

## Local Development

For local testing and development:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server locally
python main.py
```

The server will start on `http://127.0.0.1:8001` with the MCP endpoint at `/mcp`.

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

The server supports Connect API key authentication for tools that interact with Connect services. API keys should be passed in the `x-mcp-authorization` header in the format:

```
x-mcp-authorization: Key YOUR_API_KEY
```
