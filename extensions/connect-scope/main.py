from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from posit import connect

app = FastAPI()

client = connect.Client()


@app.get("/api/user")
async def get_current_user():
    return client.me


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
