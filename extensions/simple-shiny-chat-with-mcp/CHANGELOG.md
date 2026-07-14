# Changelog

All notable changes to the Python Shiny: AI Chat with MCP Tools extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.7] - 2026-07-14

### Fixed

- Forward only the viewer's own key to MCP servers; the app no longer falls back to forwarding its own Connect API key, and the unused `X-MCP-Authorization` header was dropped. (#418)
- Forward the viewer's Connect key only to MCP servers on this Connect server, matched by full origin (scheme, host, and port) so it can't leak to another origin entered in the sidebar; off-Connect servers are still reachable, just without it. (#418)
- Pass the MCP auth header through a pre-built `httpx` client so registration works with the current `mcp` transport, which no longer accepts a `headers` argument. Give that client the MCP SDK's own defaults (a 30s timeout with a 300s read, and redirect following); without them tool calls timed out after 5s and a trailing-slash URL failed to register. (#418)
- Close each viewer's MCP server connections when their session ends, so their background tasks and open connections don't leak across sessions. (#418)
- Surface the underlying cause when adding an MCP server fails, instead of a generic "failed to register" message. (#418)
- Show the actual error text in the chat when a message fails, instead of a generic sanitized notice. (#418)
- Report removing a server as successful only when it actually succeeds, name the server in add/remove messages, and warn instead of doing nothing visible when the same MCP server URL is added twice. (#418)
- Apply the assistant's system prompt on AWS Bedrock too (it was only applied to other providers), and make the LLM-provider selection unambiguous: an explicitly configured `CHATLAS_CHAT_PROVIDER_MODEL` now takes precedence over auto-detected Bedrock credentials (Bedrock previously overrode it), Bedrock is probed only as the zero-config fallback, and the setup screen can't disagree with whether a model is configured. (#418)
- Reject a blank MCP server URL with a clear message instead of a confusing registration error. (#418)
- Keep the session alive when resolving the viewer fails for an unexpected reason (anything other than a missing integration); log it and continue instead of raising. (#418)
- Restore the white background behind chat messages so text stays readable over the page's gradient; a newer `shinychat` renamed the message elements, so the old CSS selector no longer matched. (#418)

### Changed

- Retitled to "Python Shiny: AI Chat with MCP Tools", rewrote the description, and rewrote the README to the standardized template. (#418)
- The MCP sidebar now shows the signed-in viewer, so it's clear that tools run with their Connect permissions. (#418)
- Pinned dependencies: `chatlas` to a release (was git `main`), corrected `python-dotenv` (was `dotenv`), and reconciled the runtime to Python 3.11. (#418)
- Aligned the setup screen and README settings language with the FastAPI: MCP Server example, naming the Access, Integrations, and Environment Variables locations. (#418)
- The setup screen now shows only the step still unconfigured (the LLM provider, the Visitor API Key integration, or both), instead of repeating both steps whenever either is missing. (#418)
- The info modal now shows the provider and model cleanly, instead of dumping the provider's internal object state. (#418)
- Dropped the unused `nest-asyncio` dependency. (#418)

## [0.0.6] - 2026-06-15

### Changed

- Constrained the Python runtime requirement to the current major version (`>=3.10` → `~=3.10`). (#376)

### Fixed

- Corrected a stale manifest checksum; no change to bundled files. (#376)

## [0.0.5] - 2026-05-08

### Changed

- Updated for the new settings panel. (#347)

## [0.0.4] - 2025-12-09

### Changed

- Updated chatlas environment variable references. (#306)

## [0.0.3] - 2025-11-10

### Changed

- Switched to a more minimal `requirements.txt` to avoid strict pins. (#289)

## [0.0.2] - 2025-07-08

### Changed

- Updated setup and description text. (#229)

## [0.0.1] - 2025-07-08

### Added

- Initial release. (#179)
