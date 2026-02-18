# Connect Scope

A Vue 3 + FastAPI extension for Posit Connect.

## Development

### Backend

```bash
uv sync
uv run fastapi dev main.py
```

### Frontend

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

### Build

```bash
npm run build
```

The built frontend is output to `dist/` and served as static files by FastAPI.
