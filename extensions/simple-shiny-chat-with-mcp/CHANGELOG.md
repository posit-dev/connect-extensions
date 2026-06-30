# Changelog

All notable changes to the Shiny: AI Chat with MCP Tools extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.7] - 2026-06-29

### Fixed

- Forward only the viewer's own key to MCP servers; the app no longer falls back to forwarding its own Connect API key, and the unused `X-MCP-Authorization` header was dropped. (#418)

### Changed

- Retitled to "Shiny: AI Chat with MCP Tools", rewrote the description, and rewrote the README to the standardized template. (#418)
- The MCP sidebar now shows the signed-in viewer, so it's clear that tools run with their Connect permissions. (#418)
- Pinned dependencies: `chatlas` to a release (was git `main`), corrected `python-dotenv` (was `dotenv`), and reconciled the runtime to Python 3.11. (#418)
- Aligned the setup screen and README settings language with the FastAPI: MCP Server example, naming the Access, Integrations, and Environment Variables locations. (#418)

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
