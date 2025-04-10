from http import client
import asyncio
from fastapi import FastAPI, Header
from fastapi.staticfiles import StaticFiles
from posit import connect

from cachetools import TTLCache, cached

client = connect.Client()

app = FastAPI()

# Create cache with TTL=1hour and unlimited size
client_cache = TTLCache(maxsize=float("inf"), ttl=3600)


@cached(client_cache)
def get_visitor_client(token: str | None) -> connect.Client:
    """Create and cache API client per token with 1 hour TTL"""
    if token:
        return client.with_user_session_token(token)
    else:
        return client


@app.get("/api/contents")
async def contents(posit_connect_user_session_token: str = Header(None)):
    visitor = get_visitor_client(posit_connect_user_session_token)

    response = client.get("metrics/procs")
    processes = response.json()

    contents = visitor.me.content.find()
    for content in contents:
        content["processes"] = [
            process for process in processes if content["guid"] == process["app_guid"]
        ]

    return contents


@app.get("/api/contents/{content_id}")
async def content(
    content_id: str, posit_connect_user_session_token: str = Header(None)
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    return visitor.content.get(content_id)


@app.get("/api/contents/{content_id}/processes")
async def get_content_processes(
    content_id: str, posit_connect_user_session_token: str = Header(None)
):
    visitor = get_visitor_client(posit_connect_user_session_token)

    # Assert the viewer has access to the content
    assert visitor.content.get(content_id)

    response = client.get("metrics/procs")
    processes = response.json()

    return [process for process in processes if process.get("app_guid") == content_id]


@app.delete("/api/contents/{content_id}/processes/{process_id}")
async def destroy_process(
    content_id: str,
    process_id: str,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)

    content = visitor.content.get(content_id)
    job = content.jobs.find(process_id)
    if job:
        job.destroy()
        for _ in range(30):
            job = content.jobs.find(process_id)
            if job["status"] != 0:
                return
            await asyncio.sleep(1)


@app.get("/api/contents/{content_id}/author")
async def get_author(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    content = visitor.content.get(content_id)
    return content.owner


@app.get("/api/contents/{content_id}/releases")
async def get_releases(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    content = visitor.content.get(content_id)
    return content.bundles.find()


@app.get("/api/contents/{content_id}/metrics")
async def get_metrics(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    content = visitor.content.get(content_id)
    metrics = visitor.metrics.usage.find(content_guid=content["guid"])
    return metrics


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
