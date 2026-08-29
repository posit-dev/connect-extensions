import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from shiny.express import wrap_express_app

from api import fastapi_app, create_socket_handler

# Wrap the Shiny Express app for mounting
chat_ui_path = Path(__file__).parent / "chat_ui.py"
shiny_app = wrap_express_app(chat_ui_path)


@asynccontextmanager
async def lifespan(app):
    """Start Slack Socket Mode handler on startup."""
    handler = create_socket_handler()
    asyncio.create_task(handler.start_async())
    print("Slack bot started!")

    yield

    await handler.close_async()


routes = [
    Mount("/api", app=fastapi_app),
    Mount("/", app=shiny_app),
]

app = Starlette(routes=routes, lifespan=lifespan)
