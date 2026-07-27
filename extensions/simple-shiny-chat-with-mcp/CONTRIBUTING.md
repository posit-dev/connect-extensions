# Contributing to the Python Shiny: AI Chat with MCP Tools extension

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/)

## Setup

Run `uv sync` to install dependencies.

## Development

Run `uv run shiny run --reload app.py` to start the app locally on
`http://127.0.0.1:8000`.

Set an LLM provider first, or the app shows its setup screen instead of the chat.
It reads these from the environment (a local `.env` works, via `python-dotenv`):

```
CHATLAS_CHAT_PROVIDER_MODEL=openai/gpt-4o
OPENAI_API_KEY=<your OpenAI API key>
```

Adding MCP servers only works when the app runs on Connect: the viewer's identity
comes from a session token Connect injects, which is absent locally, so the
sidebar's "Add Server" is blocked. To test the MCP path end to end, deploy to
Connect (`rsconnect deploy shiny`) with a "Connect Visitor API Key" integration.

## Tool registration

The app defines no tools; it registers a server's tools with
`chat.register_mcp_tools_http_stream_async(...)`, then reads chatlas's private
session registry (`chat._mcp_manager._mcp_sessions`) to draw the server cards. That
registry has no public accessor, so watch it when bumping `chatlas`.

## Authentication

Tools run as the signed-in viewer, never as the app:

- The app reads the `Posit-Connect-User-Session-Token` header Connect injects for the
  viewer and exchanges it for the viewer's own Connect API key. This needs a "Connect
  Visitor API Key" integration on the content.
- When you register an MCP server on this same Connect server, the app forwards that
  key so the server's tools act as the viewer, with their permissions. The current
  `mcp` streamable-HTTP transport takes auth through a pre-built `httpx` client, not a
  `headers` argument, so the app builds one client per viewer and closes it when the
  session ends.
- The key is forwarded only to MCP servers on this Connect server. A Connect key is
  meaningless to another host and must not leak to one, so servers elsewhere are
  reached without it.

## Bundle

The files sent in the deployment bundle are:

- `app.py`
- `requirements.txt`

`pyproject.toml`, `uv.lock`, and repo docs are not bundled.

## Changelog

Update the [CHANGELOG](./CHANGELOG.md) using the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, referencing the
PR number, and bump `extension.version` in `manifest.json` to trigger a release.
