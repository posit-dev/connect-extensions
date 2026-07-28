# Changelog

All notable changes to the Chat with Content extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.8] - 2026-07-17

### Added

- An in-app note explaining that the app runs as the signed-in viewer, reads
  content with their own permissions via the Visitor API Key, and stores no admin
  key. (#447)
- Clear, persistent error notifications when content can't be listed or opened
  from Connect, showing the reason instead of leaving the selector silently
  empty, plus a message when you have no content available to chat with. (#447)

### Changed

- The setup screen now shows only the step still missing rather than repeating
  both. (#447)
- Refreshed the default model names to Claude Sonnet 4.5. (#447)
- Skip the AWS Bedrock credential probe at startup when a chat provider is
  configured, and cap it with a timeout when it does run, so a slow or
  unreachable Bedrock endpoint can't delay or hang the app's startup. (#447)
- Show the actual error in the chat when a request fails, instead of a generic
  message. (#447)

### Fixed

- Guarded against content with a missing, malformed, or timezone-naive deployment
  time, which could previously leave the whole content list empty. (#446)
- Close a code block that truncation cut open, so the model reads the truncation
  note as a note rather than as more code. (#446)
- Handle a missing or misconfigured chat provider instead of crashing: an
  unconfigured provider shows the setup screen, and a configured one that can't
  start (a bad model name or missing API key) shows a readable error. (#447)
- Show a readable error if the selected content can't be read to summarize it,
  instead of silently doing nothing. (#447)
- Show a readable error when Connect gives no URL for the selected content, rather
  than failing with nothing shown. (#447)
- Show a clear error when your Connect session can't be read, instead of silently
  running with the wrong identity and failing later, and never fall back to listing
  the deployer's content as if it were yours. (#447)
- Name the real reason a session can't be read rather than showing setup steps that
  wouldn't fix it: being signed out, and the server having OAuth integrations
  disabled, are each reported as themselves. (#447)
- Don't summarize an unrelated page if the content frame redirects cross-origin
  (for example to an external login). (#447)
- Re-summarize when you switch to a different content item whose rendered HTML is
  byte-identical to the previous one, instead of leaving the earlier summary up. (#447)
- Clear the previous item's summary when you switch content, so the chat no longer
  shows a summary the model has already forgotten. (#447)
- Stream one reply at a time, so switching content or asking a question while a
  reply is still streaming no longer interleaves two replies, drops part of the
  new one, or sends the model a half-written conversation. (#447)
- Forget an exchange whose request failed, so a single failed reply no longer
  makes every later question fail until you switch content or reload. (#447)
- Cap the page content the browser sends, so selecting a very large report
  summarizes it instead of disconnecting the app. (#447)
- Stop generating a reply once you close or reload the page, instead of letting it
  run to completion unseen. (#447)
- Stop waiting on a reply that stalls, so a provider that goes quiet no longer
  leaves the app looking frozen with the chat input disabled. (#447)
- Convert the selected page outside the reactive work the server serializes, so
  opening a large report no longer pauses every other session on that worker. (#447)
- Finish answering a question you asked even if you switch content while it is
  streaming, instead of replacing the answer with a blank reply. (#447)
- Empty the chat when the selected content can't be read, so later answers can't be
  drawn from the item that is no longer on screen. (#447)
- Let a reload retry a summary whose request failed, instead of mistaking it for a
  repeat of the same page. (#447)
- Let the worker exit promptly when a credential probe is still hanging, so
  restarting the content isn't held up by it. (#447)
- Summarize a selection once even when its page loads more than once, instead of
  spending a second request to say the same thing. (#447)
- Truncated large content before sending it to the model so a big page can't
  overflow the context window. (#447)

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
