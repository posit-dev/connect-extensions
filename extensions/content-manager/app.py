from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/contents")
async def contents():
    from posit import connect

    client = connect.Client()
    return client.me.content.find()

@app.get("/contents/{content_id}")
async def content(content_id: str):
    print(content_id)
    return {}

app.mount("/", StaticFiles(directory="dist", html=True), name="static")
