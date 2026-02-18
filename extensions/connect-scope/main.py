import json

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from posit import connect

app = FastAPI()

client = connect.Client()


@app.get("/api/user")
async def get_current_user():
    return client.me


@app.get("/api/content")
async def list_content():
    return (
        content
        for content in client.content.find()
        if content["trace_collection_enabled"]
    )


@app.get("/api/content/{guid}/jobs")
async def list_jobs(guid: str):
    try:
        return list(client.content.get(guid).jobs)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/content/{guid}/jobs/{job_key}/traces")   
async def get_traces(guid: str, job_key: str):
    try:
        response = client.get(f"v1/content/{guid}/jobs/{job_key}/traces")
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


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
