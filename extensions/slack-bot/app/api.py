import re

from fastapi import FastAPI
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from app.config import settings
from app.responder import generate_response

# Initialize Slack app (started by main.py lifespan)
slack_app = AsyncApp(token=settings.slack_bot_token)


def create_socket_handler() -> AsyncSocketModeHandler:
    """Create the Socket Mode handler for Slack."""
    return AsyncSocketModeHandler(slack_app, settings.slack_app_token)


def strip_bot_mention(text: str) -> str:
    """Remove bot @-mention from message text."""
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()


# Slack event handlers

@slack_app.event("app_mention")
async def handle_mention(event, say, client):
    """Handle @-mentions in channels and threads."""
    thread_ts = event.get("thread_ts") or event["ts"]
    user_message = strip_bot_mention(event["text"])

    response = generate_response(user_message)
    await say(text=response, thread_ts=thread_ts)


@slack_app.event("message")
async def handle_dm(event, say, client):
    """Handle DMs to the bot."""
    # Only handle DMs
    if event.get("channel_type") != "im":
        return

    # Ignore bot messages and subtypes (edits, etc.)
    if event.get("bot_id") or event.get("subtype"):
        return

    user_message = event["text"]

    response = generate_response(user_message)
    await say(text=response)


# FastAPI app (just health check)
fastapi_app = FastAPI()


@fastapi_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
