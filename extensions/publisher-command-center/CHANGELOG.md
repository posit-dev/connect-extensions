# Changelog

All notable changes to the Publisher Command Center extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.9] - 2026-07-17

### Added

- Backend test suite (`test_app.py`) and frontend test suite (`vitest`), both run
  in CI. (#434)
- A "how this works" panel showing that the app acts as the signed-in viewer via
  a Connect Visitor API Key, with no admin key stored. (#434)
- Set `category` to `extension` and rewrote the description and README. (#434)
- Clear error notifications when a write action (lock, rename, delete, or stop
  process) fails, instead of failing silently. (#434)
- Error messages now include the reason reported by Connect (both failed actions
  and failed loads), so the user sees why something failed, not just that it did. (#434)

### Changed

- Return proper HTTP errors from the API (424 when a Visitor API Key integration
  is required, 502 for upstream Connect failures or any other unexpected error)
  instead of raw 500s. (#434)
- Corrected the declared Python requirement to `~=3.9` (from `~=3.8`), matching
  what the code and dependencies actually need. (#434)
- Run the synchronous API endpoints as sync `def` so FastAPI executes them in a
  threadpool; the content detail page's parallel requests now run concurrently
  instead of serializing on the event loop. (#434)
- Require the viewer's Connect session to read or manage content. On Connect, a
  request with no session token now gets the setup prompt (424) instead of falling
  back to the app's own credentials, so the app only ever acts as the signed-in
  viewer. (#434)
- Standardized user-facing error messages on "Couldn't ..." wording. (#434)
- Restyled the setup screen as a centered card and trimmed its copy to match the
  other Connect extensions' setup screens; the admin prerequisite and Max Role
  requirement now live in the README. (#434)

### Fixed

- Removed the N+1 in `GET /api/contents`: each item's running-process count is now
  fetched concurrently rather than one at a time in series. (#434)
- Fixed dead async error handling across the frontend: models now return their
  load promise, and components surface load failures instead of swallowing them. (#434)
- Guarded date formatting against null/invalid values so a missing timestamp no
  longer crashes the view. (#434)
- Report a clear error when stopping a process doesn't take effect, instead of
  reporting success while the process keeps running. (#434)
- Show a clear error, with the reason, if the app can't determine authorization
  at startup, instead of rendering a blank page. (#434)
- A single content item whose running-process count can't be read no longer
  fails the whole list; that item shows a placeholder instead. (#434)
- Don't report a failed stop-process when only the follow-up refresh failed. (#434)
- Set `rel="noopener"` on links that open in a new tab. (#434)
- Read the rename dialog's title from its own input at submit time, so a reused
  dialog can't submit a stale guid or an empty title. (#434)

### Removed

- The one-click integration button and its `GET /api/integrations` and
  `PUT /api/visitor-auth` endpoints. The setup screen now gives manual instructions
  for adding the Connect Visitor API Key integration on the Access tab, matching the
  other Connect extensions and never attaching an integration with the app's own
  credentials. (#434)
- Deleted the non-functional Metrics feature (it was unreferenced, depended on an
  undeclared Chart.js global, and rendered hardcoded data) and its API endpoint. (#434)
- Removed stray `console.log`s and dead imports. (#434)

## [0.0.8] - 2026-06-09

### Fixed

- Replaced the `token: str | None` type hint with `Optional[str]` so it no longer requires Python 3.10 at runtime, matching the declared `~=3.8` minimum.
