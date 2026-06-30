# Changelog

All notable changes to the FastAPI: MCP Server extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.7] - 2026-06-29

### Changed

- Retitled to "FastAPI: MCP Server", rewrote the README and description, and reframed the example so its three tools read as starting points you swap for your own. (#417)
- The landing page now greets the signed-in viewer by name, resolved from their Connect session token (the same identity the `connect_whoami` tool returns). (#417)
- Regenerated `requirements.txt` to resolve from the minimum supported Python (3.11) rather than a single 3.14 lock, for broader install compatibility. (#417)

### Fixed

- Corrected the documented auth model: `connect_whoami` resolves the viewer from the injected session token rather than API-key authentication, and dropped the unused `x-mcp-authorization` header from the docs. (#417)

## [0.0.6] - 2026-06-15

### Changed

- Constrained the Python runtime requirement to the current major version (`>=3.11` → `~=3.11`). (#376)

## [0.0.5] - 2026-06-11

### Changed

- Switched to with-connect for integration tests. (#355)

## [0.0.4] - 2026-05-04

### Fixed

- Fixed deprecation warnings. (#349)

## [0.0.3] - 2026-02-03

### Changed

- Switched to the visitor API integration and added stateless HTTP support. (#312)

## [0.0.2] - 2025-07-08

### Changed

- Updated setup and description text. (#229)

## [0.0.1] - 2025-07-08

### Added

- Initial release. (#179)
