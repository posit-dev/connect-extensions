from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/api/vulns")
async def get_vulnerabilities():
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get("https://packagemanager.posit.co/__api__/repos/pypi/vulns")
        response.raise_for_status()
        return response.json()

app.mount("/", StaticFiles(directory="dist", html=True), name="static")
