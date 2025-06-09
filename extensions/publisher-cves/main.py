from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

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
