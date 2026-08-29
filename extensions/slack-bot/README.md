# Slack Bot

A basic Slack bot using Socket Mode with a web chat interface. 

The bot here just mirrors back your last word as a question, to demonstrate that it's a good listener. Customize the behavior in `app/responder.py` to do whatever you'd like.

## Routes

- `/` - Web chat interface (Shiny)
- `/api/health` - Health check endpoint

## Slack App Setup

1. Create a new app at https://api.slack.com/apps (From scratch)

2. **Enable Socket Mode**
   - Settings → Socket Mode → Enable
   - Create an App-Level Token with `connections:write` scope
   - Save this token as `SLACK_APP_TOKEN` (starts with `xapp-`)

3. **Add Bot Token Scopes** (OAuth & Permissions → Scopes → Bot Token Scopes)
   - `app_mentions:read` - receive @-mention events
   - `chat:write` - send messages
   - `im:history` - receive DM messages
   - `im:read` - access DM channel info
   - `im:write` - send DMs

4. **Subscribe to Events** (Event Subscriptions → Subscribe to bot events)
   - `app_mention` - when someone @-mentions the bot
   - `message.im` - DMs to the bot

5. **Install to Workspace**
   - OAuth & Permissions → Install to Workspace
   - Copy the Bot User OAuth Token as `SLACK_BOT_TOKEN` (starts with `xoxb-`)

## Running Locally

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your tokens

# Run
uv run uvicorn app.main:app --reload
```

## Deploying to Posit Connect

Set `min_processes` to 1 in the runtime settings so the app stays running and listens for Slack messages. Otherwise, the app will go idle and stop responding to Slack.

## Usage

**Web chat:**
- Open http://localhost:8000 in your browser

**Slack:**
- Mention the bot in a channel: `@bot I feel sad` → `Sad?`
- DM the bot: `My dog is sick` → `Sick?`
