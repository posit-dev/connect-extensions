# Contributing to Publisher CVEs

## Prerequisites

- Python 3.11 or higher
- [Node.js](https://nodejs.org/en) 20 or higher
- [uv](https://docs.astral.sh/uv/)

It is recommended to use [nvm (Node Version Manager)](https://github.com/nvm-sh/nvm)
to manage Node.js versions.

## Setup

1. Run `uv sync` to install dependencies for the FastAPI server.
2. Run `npm install` to install frontend dependencies.

## Development

1. Run `uv run fastapi dev main.py` to start the FastAPI server.
2. Run the frontend development server with `npm run dev`.

## Deploy

Run `npm run build` to generate the frontend JS and CSS files in the `dist`
directory.

From there the required files to be sent in the bundle are:

- `main.py',
- 'requirements.txt'
- `dist/**`
