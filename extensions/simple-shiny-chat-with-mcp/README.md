# Shiny: AI Chat with MCP Tools

## About this example

A [Shiny for Python](https://shiny.posit.co/py/) chat app that connects an LLM to
tools over the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP),
running on Posit Connect. Add the URL of an MCP server in the sidebar and the AI can
call that server's tools during the conversation.

The point it teaches: the tools run **as the signed-in viewer**, using their Connect
identity rather than a shared API key. It pairs with the
[FastAPI: MCP Server](../simple-mcp-server/README.md) example, which serves the
tools, but it works with any streamable HTTP MCP server.

## How it works

- The chat UI is built with Shiny, and [chatlas](https://posit-dev.github.io/chatlas/)
  drives the LLM (OpenAI, Anthropic, Google, AWS Bedrock, and others).
- Enter an MCP server URL in the sidebar and the app registers its tools. The LLM
  then calls them in conversation, shows the raw tool output, and asks for
  confirmation before any action that creates, updates, or deletes data.
- **Viewer identity:** the app reads the viewer's Connect session token and forwards
  the viewer's own credentials when it calls an MCP server, so the tools act as the
  viewer with their permissions, never as this app. The sidebar shows who you're
  signed in as. This needs a Visitor API Key integration (see Setup).
- Until an LLM provider and that integration are configured, the app shows a setup
  screen instead of the chat.

## Deploy

Deploy it straight from the Connect Gallery to get a copy running, then configure it
(below). To publish your own changes, deploy the directory with
[rsconnect-python](https://docs.posit.co/rsconnect-python/) (`rsconnect deploy shiny`)
or a git-backed deployment. Requires Connect 2025.04.0 or later with OAuth
Integrations enabled.

## Setup

After deploying, in the content's settings:

- **Choose an LLM** by setting `CHATLAS_CHAT_PROVIDER_MODEL` (for example
  `openai/gpt-4o`) plus the matching API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `GOOGLE_API_KEY`, ...) on the **Advanced** tab, under **Environment Variables**. See the
  [chatlas `ChatAuto` docs](https://posit-dev.github.io/chatlas/reference/ChatAuto.html)
  for provider/model strings. On AWS Bedrock with an instance role, credentials are
  detected automatically and no vars are needed. (The older `CHATLAS_CHAT_PROVIDER`
  and `CHATLAS_CHAT_ARGS` still work but are deprecated.)
- **Add a Visitor API Key integration** so tools run as the viewer: on the **Access**
  tab, add a "Connect Visitor API Key" integration under **Integrations**. See the
  [OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/).

## Customize it

- Point the sidebar at your own MCP servers (such as the paired
  [FastAPI: MCP Server](../simple-mcp-server/README.md)).
- Switch LLMs by changing `CHATLAS_CHAT_PROVIDER_MODEL`.
- Edit the assistant's behavior in the system prompt in `app.py`.

## Learn more

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [chatlas](https://posit-dev.github.io/chatlas/)
- [Shiny for Python chat](https://shiny.posit.co/py/components/display-messages/chat/)
- [Posit Connect OAuth integrations](https://docs.posit.co/connect/user/oauth-integrations/)
- [FastAPI: MCP Server](../simple-mcp-server/README.md), the paired tool server
