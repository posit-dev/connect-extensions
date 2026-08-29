# Contributing to Publisher Command Center

## Prerequisites

- Python 3.9 or higher
- [Node.js](https://nodejs.org/en) 20 or higher
- [uv](https://docs.astral.sh/uv/)

It is recommended to use [nvm (Node Version Manager)](https://github.com/nvm-sh/nvm)
to manage Node.js versions.

## Setup

1. Run `uv sync` to install dependencies for the FastAPI server.
2. Run `npm install` to install frontend dependencies.

## Development

1. Run `uv run fastapi dev app.py` to start the FastAPI server.
2. Run the frontend development server with `npm run dev`.

## Tests

- Backend: `uv run pytest` runs the FastAPI API tests in `test_app.py`.
- Frontend: `npm test` runs the frontend unit tests with [Vitest](https://vitest.dev/).

Both suites also run in CI on every change.

## Deploy

Run `npm run build` to generate the frontend JS and CSS files in the `dist`
directory.

From there the required files to be sent in the bundle are:

- `app.py`
- `requirements.txt`
- `dist/**`

## Changelog

Update the [CHANGELOG](./CHANGELOG.md) using the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, referencing the
PR number, and bump `extension.version` in `manifest.json` to trigger a release.
