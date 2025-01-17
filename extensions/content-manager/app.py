from http import client
from time import sleep
from fastapi import FastAPI, Header
from fastapi.staticfiles import StaticFiles
from posit import connect

app = FastAPI()

client = connect.Client()

@app.get("/api/contents")
async def contents(posit_connect_user_session_token: str = Header(None)):

    if posit_connect_user_session_token:
        viewer = client.with_user_session_token(posit_connect_user_session_token)
        viewer = viewer.me["guid"]
        return client.content.find(owner_guid=viewer)

    return client.me.content.find()


@app.get("/api/contents/{content_id}")
async def content(
    content_id: str, posit_connect_user_session_token: str = Header(None)
):
    if posit_connect_user_session_token:
        viewer = client.with_user_session_token(posit_connect_user_session_token)
        return viewer.content.get(content_id)

    return client.content.get(content_id)


@app.get("/api/contents/{content_id}/processes")
async def processes(
    content_id: str, posit_connect_user_session_token: str = Header(None)
):
    response = client.get("metrics/procs")
    processes = response.json()
    return [process for process in processes if process.get("app_guid") == content_id]


@app.delete("/api/contents/{content_id}/processes/{process_id}")
async def destroy_process(
    content_id: str,
    process_id: str,
    posit_connect_user_session_token: str = Header(None),
):
    content = client.content.get(content_id)
    job = content.jobs.find(process_id)
    if job:
        job.destroy()
        for _ in range(30):
            job = content.jobs.find(process_id)
            if job["status"] != 0:
                return
            sleep(1)

@app.get("/api/contents/{content_id}/author")
async def get_author(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    if posit_connect_user_session_token:
        viewer = client.with_user_session_token(posit_connect_user_session_token)
        content = viewer.content.get(content_id)
    else:
        content = client.content.get(content_id)

    return content.owner


@app.get("/api/contents/{content_id}/releases")
async def get_releases(
    content_id,
    posit_connect_user_session_token: str = Header(None),
):
    content = client.content.get(content_id)
    return content.bundles.find()


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
