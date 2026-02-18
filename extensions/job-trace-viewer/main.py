import json
import logging

logging.basicConfig(level=logging.INFO)

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from posit import connect

logger = logging.getLogger(__name__)

app = FastAPI()

client = connect.Client()
_api_base = client.cfg.url.rstrip("/")


def _connect_url(path: str) -> str:
    """Build a Connect API URL. client.cfg.url already points to /__api__."""
    return f"{_api_base}{path}"


@app.get("/api/content")
async def list_content():
    try:
        items = client.content.find()
        return [
            {
                "guid": item["guid"],
                "name": item["name"],
                "title": item.get("title") or item["name"],
                "description": item.get("description", ""),
                "app_mode": item.get("app_mode", ""),
                "created_time": item.get("created_time"),
                "last_deployed_time": item.get("last_deployed_time"),
                "dashboard_url": item.get("dashboard_url", ""),
            }
            for item in items
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/content/{guid}/jobs")
async def list_jobs(guid: str, request: Request):
    headers = _connect_headers(request)
    url = _connect_url(f"/v1/content/{guid}/jobs")
    logger.info("Fetching jobs: %s", url)
    async with httpx.AsyncClient() as http:
        try:
            response = await http.get(url, headers=headers)
            logger.info("Jobs response: %s", response.status_code)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Jobs error %s: %s", e.response.status_code, e.response.text)
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/content/{guid}/jobs/{key}/traces")
async def get_job_traces(guid: str, key: str, request: Request):
    headers = _connect_headers(request)
    url = _connect_url(f"/v1/content/{guid}/jobs/{key}/traces")
    params = {"limit": "0"}
    async with httpx.AsyncClient(timeout=30.0) as http:
        try:
            response = await http.get(url, headers=headers, params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            lines = [line for line in response.text.splitlines() if line.strip()]
            documents = []
            for line in lines:
                try:
                    documents.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return documents
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


def _connect_headers(request: Request) -> dict:
    headers: dict = {"Authorization": f"Key {client.cfg.api_key}"}
    session_token = request.headers.get("Posit-Connect-User-Session-Token")
    if session_token:
        headers["Posit-Connect-User-Session-Token"] = session_token
    return headers


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
