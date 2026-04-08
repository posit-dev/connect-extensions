"""Test MCP server: math tools."""

from fastmcp import FastMCP

mcp = FastMCP("Math Tools")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


@mcp.tool()
def factorial(n: int) -> int:
    """Compute the factorial of a non-negative integer."""
    if n < 0:
        raise ValueError("n must be non-negative")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


app = mcp.http_app(stateless_http=True, json_response=True)
