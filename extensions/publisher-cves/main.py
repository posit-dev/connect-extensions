from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from posit import connect

app = FastAPI()

client = connect.Client()

@app.get("/api/packages/{guid}")
async def get_packages(guid: str):
    try:
        content = client.content.get(guid)
        packages = list(content.packages)
        return packages
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Content not found or error fetching packages: {str(e)}")
    
@app.get("/api/vulns")
async def get_vulnerabilities():
    import httpx
    import asyncio
    
    repositories = ["pypi", "cran"]
    results = {}
    
    async def fetch_repo_vulns(repo):
        async with httpx.AsyncClient() as client:
            url = f"https://packagemanager.posit.co/__api__/repos/{repo}/vulns"
            response = await client.get(url)
            response.raise_for_status()
            return repo, response.json()
    
    tasks = [fetch_repo_vulns(repo) for repo in repositories]
    for repo, data in await asyncio.gather(*tasks):
        results[repo] = data
        
    return results

app.mount("/", StaticFiles(directory="dist", html=True), name="static")
