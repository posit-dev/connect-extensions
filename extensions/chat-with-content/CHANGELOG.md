# Changelog

All notable changes to the Chat with Content extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.8] - 2026-07-17

### Added

- Backend test suite (`test_helpers.py`) run in a dedicated CI workflow. (#433)
- An in-app note explaining that the app runs as the signed-in viewer, reads
  content with their own permissions via the Visitor API Key, and stores no admin
  key. (#433)
- Clear, persistent error notifications when content can't be listed or opened
  from Connect, showing the reason instead of leaving the selector silently
  empty, plus a message when you have no content available to chat with. (#433)

### Changed

- Rewrote the description and the README, and aligned the in-app setup screen
  with the MCP chat extension (only the still-missing step is shown). (#433)
- Refreshed the default model names to Claude Sonnet 4.5. (#433)
- Only probe AWS Bedrock credentials at startup when no chat provider is
  configured, avoiding an unnecessary live Bedrock call. (#433)
- Surfaced real chat errors in the UI (`on_error="actual"`). (#433)
- Trimmed the bundled manifest to the files the app needs to run. (#433)

### Fixed

- Guarded against content with no deployment time, a malformed deployment time,
  and a missing chat provider, which could previously crash the app or leave the
  whole content list empty. (#433)
- Show a clear error when the app can't verify your Connect session, instead of
  silently running with the wrong identity and failing later. (#433)
- Require the viewer's Connect session before listing content: when the app can't
  read a session token (for example if OAuth integrations are disabled on the
  server), it shows the setup screen instead of listing the deployer's content. (#433)
- Don't summarize an unrelated page if the content frame redirects cross-origin
  (for example to an external login). (#433)
- Truncated large content before sending it to the model so a big page can't
  overflow the context window. (#433)
- Removed a duplicate `chatlas` dependency pin. (#433)

## [0.0.7] - 2026-06-15

### Changed

- Constrained the Python runtime requirement to the current major version (`>=3.10.0` → `~=3.10`). (#376)

### Fixed

- Corrected a stale manifest checksum; no change to bundled files. (#376)

## [0.0.6] - 2026-05-08

### Changed

- Updated for the new settings panel. (#347)

## [0.0.5] - 2026-04-08

### Changed

- Added Azure OpenAI compatibility. (#331)

## [0.0.4] - 2026-01-16

### Changed

- Updated chatlas usage. (#310)

## [0.0.3] - 2025-12-09

### Changed

- Updated chatlas environment variable references. (#306)

## [0.0.2] - 2025-11-10

### Changed

- Switched to a more minimal `requirements.txt` to avoid strict pins. (#289)

## [0.0.1] - 2025-07-08

### Added

- Initial release. (#190)
