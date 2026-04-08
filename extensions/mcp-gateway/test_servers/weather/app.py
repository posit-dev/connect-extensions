"""MCP server: weather tools (mock data)."""

import random

from fastmcp import FastMCP

mcp = FastMCP("Weather Tools")

_CITIES = {
    "new york": {"lat": 40.71, "lon": -74.01},
    "san francisco": {"lat": 37.77, "lon": -122.42},
    "london": {"lat": 51.51, "lon": -0.13},
    "tokyo": {"lat": 35.68, "lon": 139.69},
    "sydney": {"lat": -33.87, "lon": 151.21},
}


@mcp.tool()
def get_weather(city: str) -> dict:
    """Get the current weather for a city. Returns temperature, humidity, and conditions."""
    key = city.lower().strip()
    coords = _CITIES.get(key, {"lat": 0.0, "lon": 0.0})
    return {
        "city": city,
        "temperature_f": round(random.uniform(30, 95), 1),
        "humidity_pct": random.randint(20, 90),
        "conditions": random.choice(["sunny", "cloudy", "rainy", "partly cloudy"]),
        **coords,
    }


@mcp.tool()
def get_forecast(city: str, days: int = 3) -> list[dict]:
    """Get a multi-day weather forecast for a city."""
    return [
        {
            "day": i + 1,
            "high_f": round(random.uniform(50, 95), 1),
            "low_f": round(random.uniform(30, 70), 1),
            "conditions": random.choice(["sunny", "cloudy", "rainy", "partly cloudy"]),
        }
        for i in range(days)
    ]


app = mcp.http_app(stateless_http=True, json_response=True)
