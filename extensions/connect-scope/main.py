import json
import os

from cachetools import TTLCache, cached
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from posit import connect
from posit.connect.errors import ClientError

app = FastAPI()

client = connect.Client()

# Cache visitor clients per token with a 1-hour TTL
client_cache = TTLCache(maxsize=float("inf"), ttl=3600)


@cached(client_cache)
def get_visitor_client(token: str | None) -> connect.Client:
    """Create and cache an API client per session token with 1 hour TTL."""
    if token:
        return client.with_user_session_token(token)
    return client


@app.get("/api/visitor-auth")
async def integration_status(posit_connect_user_session_token: str = Header(None)):
    """Check whether the Visitor API OAuth integration is configured."""
    if os.getenv("RSTUDIO_PRODUCT") == "CONNECT":
        if not posit_connect_user_session_token:
            return {"authorized": False}
        try:
            get_visitor_client(posit_connect_user_session_token)
        except ClientError as err:
            if err.error_code == 212:
                return {"authorized": False}
            raise

    return {"authorized": True}


@app.get("/api/user")
async def get_current_user(posit_connect_user_session_token: str = Header(None)):
    visitor = get_visitor_client(posit_connect_user_session_token)
    return visitor.me


@app.get("/api/content")
async def list_content(posit_connect_user_session_token: str = Header(None)):
    visitor = get_visitor_client(posit_connect_user_session_token)
    return (
        content
        for content in visitor.content.find()
        if content["trace_collection_enabled"]
    )


@app.get("/api/content/{guid}/jobs")
async def list_jobs(guid: str, posit_connect_user_session_token: str = Header(None)):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        return list(visitor.content.get(guid).jobs)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/content/{guid}/jobs/{job_key}/traces")
async def get_traces(
    guid: str,
    job_key: str,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        response = visitor.get(f"v1/content/{guid}/jobs/{job_key}/traces")
        records = []
        for line in response.content.decode("utf-8").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # skip truncated or malformed trailing line
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", include_in_schema=False)
async def serve_index(request: Request):
    root_path = request.scope.get("root_path", "").rstrip("/")
    with open("dist/index.html") as f:
        content = f.read()
    script_tag = f'<script>window.__CONNECT_ROOT_PATH__ = "{root_path}";</script>'
    content = content.replace("</head>", f"  {script_tag}\n  </head>")
    return HTMLResponse(content)


app.mount("/", StaticFiles(directory="dist"), name="static")
