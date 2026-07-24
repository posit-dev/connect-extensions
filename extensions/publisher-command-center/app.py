import asyncio
import os
from typing import Optional

from cachetools import TTLCache, cached
from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from posit import connect
from posit.connect.errors import ClientError

# Base client. Used only to exchange each viewer's session token into a
# viewer-scoped client; its own credentials are never used to read or manage content.
client = connect.Client()

app = FastAPI()

# Cache the per-viewer client by session token (1h TTL) so repeated requests in a
# session reuse one client instead of re-exchanging the token every call.
client_cache = TTLCache(maxsize=float("inf"), ttl=3600)


@cached(client_cache)
def _build_visitor_client(token: Optional[str]) -> connect.Client:
    return client.with_user_session_token(token) if token else client


def _connect_http_error(err: ClientError) -> HTTPException:
    # Error 212 means no Visitor API Key integration is configured; the frontend
    # treats 424 as "needs setup" and shows the integration prompt. Any other
    # Connect error is an upstream failure the caller can't fix, so surface a 502
    # with Connect's message rather than a raw 500.
    if err.error_code == 212:
        return HTTPException(
            status_code=424,
            detail="A Connect Visitor API Key integration is required.",
        )
    return HTTPException(
        status_code=502, detail=f"Connect API error: {err.error_message}"
    )


# Anything not already turned into an HTTPException (a network failure, an
# unexpected SDK error) becomes a 502 with a curated message; the real error is
# logged for the publisher rather than shown to the viewer.
@app.exception_handler(Exception)
async def _unexpected_error(request, exc):
    print(f"Unexpected error handling {request.url.path}: {exc}")
    return JSONResponse(
        status_code=502, content={"detail": "Connect API error. Please try again."}
    )


def _running_on_connect() -> bool:
    return "CONNECT" in (os.getenv("POSIT_PRODUCT"), os.getenv("RSTUDIO_PRODUCT"))


# The viewer-scoped client. On Connect with no session token there's no viewer to
# act as, so require setup instead of falling back to the base client (which would
# read and manage content as the deployer).
def get_visitor_client(token: Optional[str]) -> connect.Client:
    if _running_on_connect() and not token:
        raise HTTPException(
            status_code=424,
            detail="A Connect Visitor API Key integration is required.",
        )
    try:
        return _build_visitor_client(token)
    except ClientError as err:
        raise _connect_http_error(err)


# The bootstrap authorization check. On Connect the app is authorized only if the
# viewer's session token exchanges into a client; no token or a missing integration
# (error 212) means not authorized, so the frontend shows the setup instructions.
@app.get("/api/visitor-auth")
def integration_status(posit_connect_user_session_token: str = Header(None)):
    if _running_on_connect():
        if not posit_connect_user_session_token:
            return {"authorized": False}
        try:
            _build_visitor_client(posit_connect_user_session_token)
        except ClientError as err:
            if err.error_code == 212:
                return {"authorized": False}
            raise _connect_http_error(err)

    return {"authorized": True}


# The signed-in viewer, so the UI can show whose identity the app is acting as.
@app.get("/api/user")
def get_user(posit_connect_user_session_token: str = Header(None)):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        return visitor.me
    except ClientError as err:
        raise _connect_http_error(err)


@app.get("/api/contents")
async def contents(posit_connect_user_session_token: str = Header(None)):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        all_content = visitor.content.find()
    except ClientError as err:
        raise _connect_http_error(err)
    contents = [c for c in all_content if c.app_role in ["owner", "editor"]]

    # Each item's running-process count needs its own jobs call. posit-sdk is
    # synchronous, so run those blocking calls in threads and gather them
    # concurrently rather than one at a time in series. A failure on one item
    # yields None (not 0) so it doesn't fail the whole listing and the UI can tell
    # "couldn't determine" apart from a genuine "0 running".
    async def active_jobs(content):
        try:
            jobs = await asyncio.to_thread(lambda: list(content.jobs))
            return [job for job in jobs if job["status"] == 0]
        except Exception as err:
            print(f"Couldn't read jobs for {content.get('guid')}: {err}")
            return None

    results = await asyncio.gather(*(active_jobs(c) for c in contents))
    for content, jobs in zip(contents, results):
        content["active_jobs"] = jobs

    return contents


@app.get("/api/contents/{content_id}")
def content(
    content_id: str, posit_connect_user_session_token: str = Header(None)
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        return visitor.content.get(content_id)
    except ClientError as err:
        raise _connect_http_error(err)


@app.patch("/api/contents/{content_id}/lock")
def lock_content(
    content_id: str,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        content = visitor.content.get(content_id)
        content.update(locked=not content.locked)
    except ClientError as err:
        raise _connect_http_error(err)
    return content


@app.patch("/api/contents/{content_id}/rename")
def rename_content(
    content_id: str,
    title: str = Body(..., embed=True),
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        content = visitor.content.get(content_id)
        content.update(title=title)
    except ClientError as err:
        raise _connect_http_error(err)
    return content


@app.get("/api/contents/{content_id}/processes")
def get_content_processes(
    content_id: str, posit_connect_user_session_token: str = Header(None)
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        # Fetching the content first asserts the viewer can access it.
        content = visitor.content.get(content_id)
        return [job for job in content.jobs if job["status"] == 0]
    except ClientError as err:
        raise _connect_http_error(err)


@app.delete("/api/contents/{content_id}")
def delete_content(
    content_id: str,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        visitor.content.get(content_id).delete()
    except ClientError as err:
        raise _connect_http_error(err)


@app.delete("/api/contents/{content_id}/processes/{process_id}")
async def destroy_process(
    content_id: str,
    process_id: str,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        content = visitor.content.get(content_id)
        job = content.jobs.find(process_id)
        if not job:
            return  # already gone; nothing to stop
        job.destroy()
        # Poll briefly until the job is no longer active before returning.
        for _ in range(30):
            job = content.jobs.find(process_id)
            if job["status"] != 0:
                return
            await asyncio.sleep(1)
    except ClientError as err:
        raise _connect_http_error(err)
    # Still running after the wait: report it instead of a false success.
    raise HTTPException(
        status_code=504, detail="The process didn't stop in time. Please try again."
    )


@app.get("/api/contents/{content_id}/author")
def get_author(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        return visitor.content.get(content_id).owner
    except ClientError as err:
        raise _connect_http_error(err)


@app.get("/api/contents/{content_id}/releases")
def get_releases(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    visitor = get_visitor_client(posit_connect_user_session_token)
    try:
        return visitor.content.get(content_id).bundles.find()
    except ClientError as err:
        raise _connect_http_error(err)


# check_dir=False so importing this module (e.g. for the backend tests) doesn't
# require the built frontend; on Connect the bundle always includes dist/.
app.mount("/", StaticFiles(directory="dist", html=True, check_dir=False), name="static")
