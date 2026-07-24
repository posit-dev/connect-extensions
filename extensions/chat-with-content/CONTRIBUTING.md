# Contributing to Chat with Content

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/)

## Setup

Run `uv sync` to install the app and test dependencies.

## Development

Run `uv run shiny run app.py` to start the app locally. It reads the same
`CHATLAS_CHAT_PROVIDER_MODEL` / API-key environment variables described in the
[README](./README.md).

## Tests

Run `uv run pytest`. The tests cover the pure helpers in `helpers.py`; the Shiny
app in `app.py` is kept thin over those functions so the logic can be tested
without a running session or any LLM / Connect calls. CI runs the same command.

## Bundle

The files sent in the deployment bundle are:

- `app.py`
- `helpers.py`
- `requirements.txt`

`pyproject.toml`, tests, and repo docs are not bundled.

## Changelog

Update the [CHANGELOG](./CHANGELOG.md) using the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, referencing the
PR number, and bump `extension.version` in `manifest.json` to trigger a release.
