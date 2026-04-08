"""MCP protocol smoke test for the financial-chart server.

Validates both HTML delivery variants (inline and file) on the same server:
- 4 tools: show_chart_inline, show_chart_file, refresh_chart_inline, refresh_chart_file
- 2 resources: ui://financial-chart/inline, ui://financial-chart/file
- Both resources serve valid HTML with the ext-apps SDK
- Both show tools return 52-week financial data
- CSP metadata present on both resources
"""

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test():
    port = sys.argv[1] if len(sys.argv) > 1 else "3001"
    url = f"http://localhost:{port}/mcp"

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  Connected to MCP server")

            # --- Tools ---
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            expected_tools = {
                "show_chart_inline",
                "show_chart_file",
                "refresh_chart_inline",
                "refresh_chart_file",
            }
            assert names == expected_tools, f"Tool mismatch: got {names}, expected {expected_tools}"
            print(f"  Tools: {', '.join(sorted(names))}")

            # --- Resources ---
            resources = await session.list_resources()
            uris = {str(r.uri) for r in resources.resources}
            expected_uris = {
                "ui://financial-chart/inline",
                "ui://financial-chart/file",
            }
            assert uris == expected_uris, f"Resource mismatch: got {uris}, expected {expected_uris}"

            for r in resources.resources:
                assert r.mimeType == "text/html;profile=mcp-app", f"MIME mismatch on {r.uri}: {r.mimeType}"
                meta = r.meta or {}
                ui_meta = meta.get("ui", {})
                csp = ui_meta.get("csp", {})
                assert "https://unpkg.com" in csp.get("resourceDomains", []), f"Missing CSP on {r.uri}"
            print(f"  Resources: {', '.join(sorted(uris))} (both have correct MIME + CSP)")

            # --- Call both show tools ---
            for tool_name, expected_suffix in [
                ("show_chart_inline", "(Inline)"),
                ("show_chart_file", "(File)"),
            ]:
                result = await session.call_tool(tool_name, {})
                data = json.loads(result.content[0].text)
                assert expected_suffix in data["title"], f"{tool_name} title missing '{expected_suffix}': {data['title']}"
                assert len(data["timeSeries"]) == 52, f"{tool_name} expected 52 points, got {len(data['timeSeries'])}"
                print(f"  {tool_name}: {data['title']} ({len(data['timeSeries'])} points)")

            # --- Read both UI resources ---
            for uri in sorted(expected_uris):
                resource = await session.read_resource(uri)
                html = resource.contents[0].text
                assert "ext-apps" in html, f"{uri} missing ext-apps SDK"
                assert "new App(" in html, f"{uri} missing App constructor"
                variant = "inline" if "inline" in uri else "file"
                assert f"refresh_chart_{variant}" in html, f"{uri} missing correct refresh tool name"
                print(f"  {uri}: {len(html)} chars, has ext-apps SDK, correct refresh tool")

            print("\nAll tests passed.")


asyncio.run(test())
