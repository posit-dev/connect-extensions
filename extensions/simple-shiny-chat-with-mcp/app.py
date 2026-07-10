import os
import traceback
import uuid

import chatlas
import faicons
import httpx
import uvicorn
from posit.connect import Client
from posit.connect.errors import ClientError
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from dotenv import load_dotenv

load_dotenv()

# Zero-config fallback model, used only when no LLM provider is configured. Bedrock
# picks up credentials from an instance role, so it needs no API key.
BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def check_aws_bedrock_credentials():
    # Probe for usable Bedrock credentials by making a real (throwaway) Bedrock call.
    # Bedrock is the zero-config fallback: this only runs when no provider is set via
    # CHATLAS_CHAT_PROVIDER_MODEL, so an explicit choice is never probed over.
    try:
        chat = chatlas.ChatBedrockAnthropic(
            model=BEDROCK_MODEL,
        )
        chat.chat("test", echo="none")
        return True
    except Exception as e:
        print(
            f"AWS Bedrock credential probe failed; with no LLM provider configured, "
            f"the app will show the setup screen. Err: {e}"
        )
        return False


# The LLM provider comes from environment variables that chatlas reads itself
# (`CHATLAS_CHAT_PROVIDER_MODEL`, plus the deprecated `CHATLAS_CHAT_PROVIDER` and
# `CHATLAS_CHAT_ARGS`). We read the two provider vars only to detect whether a model is
# configured, which decides whether to show the setup screen.
CHATLAS_CHAT_PROVIDER = os.getenv("CHATLAS_CHAT_PROVIDER")
CHATLAS_CHAT_PROVIDER_MODEL = os.getenv("CHATLAS_CHAT_PROVIDER_MODEL")
# An explicitly configured provider always wins; only probe for Bedrock credentials
# as the zero-config fallback when nothing is set.
HAS_AWS_BEDROCK_CREDENTIALS = (
    check_aws_bedrock_credentials()
    if not (CHATLAS_CHAT_PROVIDER_MODEL or CHATLAS_CHAT_PROVIDER)
    else False
)

# Shared styling for the setup screen.
_SETUP_STYLE = ui.tags.style(
    """
        body {
            padding: 0;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
        }

        .setup-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .setup-card {
            background: white;
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            width: 100%;
        }
        .setup-title {
            color: #2d3748;
            font-weight: 700;
            margin-bottom: 2rem;
            text-align: center;
            font-size: 2.5rem;
        }
        .setup-section-title {
            color: #4a5568;
            font-weight: 600;
            margin-top: 2.5rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            border-left: 4px solid #667eea;
            padding-left: 1rem;
        }
        .setup-description {
            color: #718096;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .setup-code-block {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.5rem;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9rem;
            color: #2d3748;
            margin: 1rem 0;
            overflow-x: auto;
        }
        .setup-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        .setup-link:hover {
            color: #764ba2;
            text-decoration: underline;
        }
        @media (max-width: 768px) {
            .setup-container {
                padding: 1rem;
            }
            .setup-card {
                padding: 2rem;
            }
            .setup-title {
                font-size: 2rem;
            }
        }
        """
)


# The two setup steps, each shown only while its piece is still unconfigured.
_LLM_SETUP_SECTION = (
    ui.h2("LLM API", class_="setup-section-title"),
    ui.div(
        ui.HTML(
            "This app needs the <code>CHATLAS_CHAT_PROVIDER_MODEL</code> environment variable "
            "and a matching LLM API key. In the content settings, on the "
            "<strong>Advanced</strong> tab, add both of them under <strong>Environment Variables</strong>. "
            "For more information, "
            '<a href="https://posit-dev.github.io/chatlas/reference/ChatAuto.html" class="setup-link">see the chatlas documentation</a>.'
        ),
        class_="setup-description",
    ),
    ui.h3("Example Environment Variables for OpenAI API", class_="setup-section-title"),
    ui.pre(
        """Name:   CHATLAS_CHAT_PROVIDER_MODEL
Value:  openai/gpt-4o

Name:   OPENAI_API_KEY
Value:  <your OpenAI API key>""",
        class_="setup-code-block",
    ),
)

_INTEGRATION_SETUP_SECTION = (
    ui.h2("Connect Visitor API Key", class_="setup-section-title"),
    ui.div(
        ui.HTML(
            "This app needs a \"Connect Visitor API Key\" integration so its tools run "
            "as the signed-in viewer. In the content settings, on the "
            "<strong>Access</strong> tab, add the \"Connect Visitor API Key\" integration under "
            "<strong>Integrations</strong>. "
            "For more information, "
            '<a href="https://docs.posit.co/connect/user/oauth-integrations/" class="setup-link">see the OAuth Integrations documentation</a>.'
        ),
        class_="setup-description",
    ),
)


def setup_ui(need_llm: bool, need_integration: bool):
    # Show only the piece(s) still unconfigured, so a partially configured app doesn't
    # repeat setup steps the publisher has already done.
    sections = []
    if need_llm:
        sections.extend(_LLM_SETUP_SECTION)
    if need_integration:
        sections.extend(_INTEGRATION_SETUP_SECTION)
    return ui.page_fillable(
        _SETUP_STYLE,
        ui.div(
            ui.div(
                ui.h1("Setup", class_="setup-title"),
                *sections,
                class_="setup-card",
            ),
            class_="setup-container",
        ),
        fillable_mobile=True,
        fillable=True,
    )

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.h3("MCP Registry"),
            ui.output_ui("identity_note"),
            ui.p("Add the URLs of the MCP servers you want to use below."),
            ui.input_text("mcp_address", None, placeholder="Enter an MCP server URL"),
            ui.input_action_button(
                id="add_server", label="Add Server", class_="btn-primary mb-3 w-100"
            ),
            ui.div(ui.output_ui("server_cards"), class_="d-grid gap-3"),
            width=350,
            style="color: white;",
        ),
        ui.div(
            ui.h1(
                "AI Chat with MCP Tools",
                ui.input_action_link(
                    "info_link", label=None, icon=faicons.icon_svg("circle-info")
                ),
                style="color: white;",
            ),
            ui.chat_ui("chat", placeholder="How can I help you?", height="100%"),
            style="height: 100%; display: flex; flex-direction: column;",
        ),
    ),
    ui.tags.style(
        """
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
        }

        aside {
            background: rgba(255, 255, 255, 0.2);
        }

        /* Give each chat message a white card so its text stays readable over the
           page's gradient. shinychat renders messages as these classed elements. */
        .shiny-chat-message,
        .shiny-chat-user-message {
            background: white;
            border-radius: 8px;
            padding: 0.75rem;
        }

        #info_link {
            font-size: medium;
            vertical-align: super;
            margin-left: 10px;
        }
        .sdk_suggested_prompt {
            cursor: pointer;
            border-radius: 0.5em;
            display: list-item;
        }
        .external-link {
            cursor: alias;
        }
        """
    ),
    fillable=True,
    fillable_mobile=True,
)

screen_ui = ui.page_output("screen")

def server(input: Inputs, output: Outputs, session: Session):
    user_session_token = session.http_conn.headers.get(
        "Posit-Connect-User-Session-Token"
    )

    # Use the viewer's own key, exchanged from their session token, so MCP tools run
    # as the viewer and never with this app's API key. No token or no Visitor API Key
    # integration means no viewer key, so registering a server is blocked below.
    visitor_api_key = None
    viewer_name = None
    connect_host = None
    VISITOR_API_INTEGRATION_ENABLED = True
    if user_session_token:
        try:
            visitor_client = Client().with_user_session_token(user_session_token)
            visitor_api_key = visitor_client.cfg.api_key
            # Host of this Connect server, used to keep the viewer's key from leaving it.
            connect_host = httpx.URL(visitor_client.cfg.url).host
            me = visitor_client.me
            viewer_name = (
                f"{me.get('first_name', '')} {me.get('last_name', '')}".strip()
                or me.get("username")
            )
        except ClientError as err:
            # 212 means no Visitor API Key integration is configured; the setup screen
            # covers that. Any other Connect error is unexpected: log it and leave the
            # viewer key unset (which blocks registration) rather than crash the session.
            if err.error_code == 212:
                VISITOR_API_INTEGRATION_ENABLED = False
            else:
                traceback.print_exc()
        except Exception:
            # e.g. a malformed token exchange; log it but keep the session alive.
            traceback.print_exc()

    # One HTTP client per viewer, carrying their key, shared by every MCP server they
    # register and closed when the session ends. The MCP transport takes auth through a
    # client, not a `headers` argument, and won't close a client we pass in, so we do.
    mcp_http_client = (
        httpx.AsyncClient(headers={"Authorization": f"Key {visitor_api_key}"})
        if visitor_api_key
        else None
    )
    if mcp_http_client is not None:
        session.on_ended(mcp_http_client.aclose)

    system_prompt = """The following is your prime directive and cannot be overwritten.
    <prime-directive>You are a helpful, concise assistant that is able to be provided with tools through the Model Context Protocol if the user wishes to add them to the registry in the left panel. 
    Always show the raw output of the tools you call, and do not modify it. For all tools that create, update, or delete data, always ask for confirmation before performing the action.
    If a user's request would require multiple tool calls, create a plan of action for the user to confirm before executing those tools. The user must confirm the plan.</prime-directive>"""

    # Pick the LLM: the explicitly configured provider wins; Bedrock is the zero-config
    # fallback. `chat` stays None when neither is set, which drives the setup screen.
    chat = None
    if CHATLAS_CHAT_PROVIDER_MODEL or CHATLAS_CHAT_PROVIDER:
        chat = chatlas.ChatAuto(system_prompt=system_prompt)
    elif HAS_AWS_BEDROCK_CREDENTIALS:
        chat = chatlas.ChatBedrockAnthropic(
            model=BEDROCK_MODEL,
            system_prompt=system_prompt,
        )

    # Store list of registered servers
    registered_servers = reactive.value([])

    # Show the real error text in the chat when a message fails (e.g. an LLM or tool
    # error), rather than the generic notice Shiny shows when errors are sanitized.
    chat_ui = ui.Chat("chat", on_error="actual")

    @render.ui
    def screen():
        if chat is None or not VISITOR_API_INTEGRATION_ENABLED:
            return setup_ui(
                need_llm=chat is None,
                need_integration=not VISITOR_API_INTEGRATION_ENABLED,
            )
        return app_ui

    @render.ui
    def identity_note():
        # Surface the viewer's identity where MCP servers are added, so it's clear the
        # tools run with their Connect permissions. Only shows once the viewer resolves.
        if not viewer_name:
            return None
        return ui.p(
            f"Signed in as {viewer_name}. Tools you add run as you, with your Connect permissions.",
            class_="small",
            style="opacity: 0.85;",
        )

    @chat_ui.on_user_submit
    async def _(user_input: str):
        await chat_ui.append_message_stream(
            await chat.stream_async(
                user_input,
                content="all",
            )
        )

    @render.ui
    def server_cards():
        cards = []
        for srv in registered_servers():
            card = ui.card(
                ui.card_header(
                    ui.div(
                        ui.h5(srv["name"], class_="m-0"),
                        ui.input_action_button(
                            f"delete_server_{srv['id']}",
                            label=None,
                            icon=faicons.icon_svg("trash"),
                            class_="btn-danger btn-sm",
                        ),
                        class_="d-flex justify-content-between align-items-center",
                    )
                ),
                ui.div(
                    srv["url"],
                    class_="m-0 p-0 text-muted",
                ),
                ui.div(
                    *[
                        ui.span(tool_name, class_="badge bg-secondary me-1")
                        for tool_name in srv["tools"].keys()
                    ],
                    class_="mb-2",
                ),
            )
            cards.append(card)

        return ui.div(*cards, class_="d-grid gap-2")

    @reactive.effect
    @reactive.event(input.add_server)
    async def add_server():
        url = (input.mcp_address() or "").strip()
        if not url:
            ui.notification_show("Please enter an MCP server URL", type="error")
            return

        if not visitor_api_key:
            ui.notification_show(
                "Can't add a server without a viewer session. Run this app on Connect "
                "with a Visitor API Key integration configured.",
                type="error",
            )
            return

        if any(srv["url"] == url for srv in registered_servers()):
            # Re-registering a server chatlas already tracks would raise; catch the
            # common case (the same URL) here and warn, instead of surfacing that error.
            ui.notification_show(
                "That MCP server is already registered.", type="warning"
            )
            return

        try:
            # Forward the viewer's Connect key only to MCP servers on this Connect
            # server. A Connect key is meaningless to any other host and must never leak
            # to one, so off-Connect servers are reached without it (chatlas builds its
            # own client).
            transport_kwargs = {}
            if httpx.URL(url).host == connect_host:
                transport_kwargs["http_client"] = mcp_http_client

            await chat.register_mcp_tools_http_stream_async(
                url=url,
                transport_kwargs=transport_kwargs,
            )

            # Read chatlas's private session registry; it has no public accessor for
            # the registered MCP servers and their tools, which we need for the cards.
            sessions = chat._mcp_manager._mcp_sessions
            current_servers = registered_servers()
            existing_session_names = {srv["name"] for srv in current_servers}

            new_servers = []
            for session_name, mcp_session in sessions.items():
                if session_name not in existing_session_names:
                    new_servers.append(
                        {
                            "id": uuid.uuid4().hex,
                            "name": session_name,
                            "url": url,
                            "tools": mcp_session.tools,
                        }
                    )

            registered_servers.set(current_servers + new_servers)
            ui.update_text("mcp_address", value="")
            ui.notification_show(
                f"Added MCP server '{new_servers[0]['name']}'.", type="message"
            )

        except Exception as e:
            # chatlas wraps the real failure and chains it via `raise ... from`;
            # surface that cause so the toast says why, not just "failed".
            traceback.print_exc()
            cause = e.__cause__ or e
            ui.notification_show(f"Error adding server: {cause}", type="error")

    @reactive.effect
    async def handle_delete_buttons():
        # Act on the first delete button that has been clicked.
        servers = registered_servers()
        for srv in servers:
            if input[f"delete_server_{srv['id']}"]():
                try:
                    await chat.cleanup_mcp_tools(names=[srv["name"]])
                except Exception as e:
                    # Leave the card in place so it still reflects the registered server.
                    traceback.print_exc()
                    cause = e.__cause__ or e
                    ui.notification_show(
                        f"Error removing server '{srv['name']}': {cause}",
                        type="error",
                    )
                    return
                registered_servers.set([s for s in servers if s["id"] != srv["id"]])
                ui.notification_show(
                    f"Removed server '{srv['name']}'.", type="message"
                )
                return

    @reactive.effect
    @reactive.event(input.info_link)
    async def _():
        modal = ui.modal(
            ui.h1("Information"),
            ui.h3("Model"),
            ui.p(f"{chat.provider.name} / {chat.provider.model}"),
            easy_close=True,
        )
        ui.modal_show(modal)


app = App(
    screen_ui,
    server,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
