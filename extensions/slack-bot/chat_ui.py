import os

from shiny.express import ui
from shinychat.express import Chat
from slack_sdk import WebClient

from responder import generate_response

# Check for Slack tokens
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
slack_app_token = os.environ.get("SLACK_APP_TOKEN")
slack_configured = bool(slack_bot_token and slack_app_token)

# Get bot name if configured
bot_name = None
if slack_configured:
    try:
        client = WebClient(token=slack_bot_token)
        auth_response = client.auth_test()
        bot_name = auth_response.get("user")
    except Exception:
        pass

ui.page_opts(fillable=True, title="Slack Bot")

with ui.sidebar(width=350):
    ui.h3("Slack Bot")

    ui.markdown(
        """
This is a basic Slack bot with a web chat interface.

The bot mirrors back your last word as a question, demonstrating
that it's a good listener. Customize the behavior in
`responder.py` to do whatever you'd like.

**Usage:**
- Chat here in the web interface
- @mention the bot in Slack
- DM the bot directly
"""
    )

    if slack_configured:
        status_text = f"Slack connected as @{bot_name}" if bot_name else "Slack connected"
        ui.div(
            ui.tags.span(status_text, style="color: green; font-weight: bold;"),
            style="margin: 1em 0; padding: 0.5em; background: #e8f5e9; border-radius: 4px;",
        )
    else:
        ui.div(
            ui.markdown(
                """
**Slack not configured**

Set these environment variables:
- `SLACK_BOT_TOKEN` (xoxb-...)
- `SLACK_APP_TOKEN` (xapp-...)
"""
            ),
            style="margin: 1em 0; padding: 0.5em; background: #ffebee; border-radius: 4px;",
        )

    ui.HTML(
        """
<details>
<summary style="cursor: pointer; font-weight: bold; margin-top: 1em;">Posit Connect</summary>
<p style="margin-top: 0.5em;">Set <code>min_processes</code> to 1 in runtime settings so the app stays running and listens for Slack messages.</p>
</details>

<details>
<summary style="cursor: pointer; font-weight: bold; margin-top: 1em;">Slack App Setup</summary>

<ol style="padding-left: 1.2em; margin-top: 0.5em;">
<li><p>Create a new app at <a href="https://api.slack.com/apps" target="_blank">api.slack.com/apps</a> (From scratch)</p></li>

<li><p><strong>Enable Socket Mode</strong></p>
<ul>
<li>Settings → Socket Mode → Enable</li>
<li>Create an App-Level Token with <code>connections:write</code> scope</li>
<li>Save as <code>SLACK_APP_TOKEN</code> (starts with <code>xapp-</code>)</li>
</ul></li>

<li><p><strong>Add Bot Token Scopes</strong> (OAuth & Permissions → Bot Token Scopes)</p>
<ul>
<li><code>app_mentions:read</code></li>
<li><code>chat:write</code></li>
<li><code>im:history</code></li>
<li><code>im:read</code></li>
<li><code>im:write</code></li>
</ul></li>

<li><p><strong>Subscribe to Events</strong> (Event Subscriptions → Subscribe to bot events)</p>
<ul>
<li><code>app_mention</code></li>
<li><code>message.im</code></li>
</ul></li>

<li><p><strong>Install to Workspace</strong></p>
<ul>
<li>OAuth & Permissions → Install to Workspace</li>
<li>Copy Bot User OAuth Token as <code>SLACK_BOT_TOKEN</code> (starts with <code>xoxb-</code>)</li>
</ul></li>
</ol>
</details>
"""
    )

chat = Chat(id="chat")

chat.ui(
    messages=[
        {"content": "Hello! How can I help you?", "role": "assistant"},
    ],
)


@chat.on_user_submit
async def handle_user_input(user_input: str):
    response = generate_response(user_input)
    await chat.append_message(response)
