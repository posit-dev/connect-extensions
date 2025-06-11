from contextlib import AsyncExitStack
from typing import Any, Optional, Callable

import chatlas
from chatlas import Chat
import mcp
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MCPClient:
    def __init__(self, llm: Chat):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm: Chat = llm
        self.tools = {}

    async def register_tools(self, server_url: str, headers: Optional[dict[str, str]] = None):
        """
        Connect to an MCP server.

        Arguments
        ---------
        server_url
            URL for mcp server
        headers
            Optional headers to include in the request to the MCP server.
        """
        self.server_url = server_url
        transport = await self.exit_stack.enter_async_context(streamablehttp_client(server_url, headers=headers))
        self.streamablehttp, self.write = transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.streamablehttp, self.write)
        )
        assert isinstance(self.session, ClientSession)

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        self_session = self.session

        def register_mcp_tool(chat: chatlas.Chat, mcp_tool):
            async def _call(**args: Any) -> Any:
                result = await self_session.call_tool(mcp_tool.name, args)
                if result.content[0].type == "text":
                    return result.content[0].text
                else:
                    raise RuntimeError(f"Unexpected content type: {result.content[0].type}")

            tool = RawChatlasTool(
                name=mcp_tool.name,
                fn=_call,
                description=mcp_tool.description,
                input_schema=mcp_tool.inputSchema,
            )
            chat._tools[tool.name] = tool
            self.tools[mcp_tool.name] = mcp_tool

        for tool in tools:
            register_mcp_tool(self.llm, tool)

    async def cleanup(self):
        """Clean up resources."""
        for tool_name in self.tools.keys():
            if tool_name in self.llm._tools:
                del self.llm._tools[tool_name]
        await self.exit_stack.aclose()


class RawChatlasTool(chatlas.Tool):
    def __init__(
        self, *, name: str, fn: Callable, description: str, input_schema: Any, model=None
    ):
        super().__init__(fn, model=model)

        self._chatlas_tool = chatlas.Tool(fn)

        # Override the name, description, and input_schema
        self.name = name
        self.description = description
        self.schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": input_schema,
            },
        }
