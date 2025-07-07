from datetime import datetime
import os
import traceback
import uuid

import chatlas
import faicons
import uvicorn
from posit.connect import Client
from posit.connect.errors import ClientError
from shiny import App, Inputs, Outputs, reactive, render, ui
from shiny.session._session import AppSession
from dotenv import load_dotenv

load_dotenv()


def check_aws_bedrock_credentials():
    # Check if AWS credentials are available in the environment
    # that can be used to access Bedrock
    try:
        chat = chatlas.ChatBedrockAnthropic(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        )
        chat.chat("test", echo="none")
        return True
    except Exception as e:
        print(
            f"AWS Bedrock credentials check failed and will fallback to checking for values for the CHATLAS_CHAT_PROVIDER and CHATLAS_CHAT_ARGS env vars. Err: {e}"
        )
        return False


CHATLAS_CHAT_PROVIDER = os.getenv("CHATLAS_CHAT_PROVIDER")
CHATLAS_CHAT_ARGS = os.getenv("CHATLAS_CHAT_ARGS")
HAS_AWS_BEDROCK_CREDENTIALS = check_aws_bedrock_credentials()

setup_ui = ui.page_fillable(
    ui.tags.style(
        """
        body {
            padding: 0;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
    ),
    ui.div(
        ui.div(
            ui.h1("Setup", class_="setup-title"),
            ui.h2("LLM API", class_="setup-section-title"),
            ui.div(
                ui.HTML(
                    "This app requires the <code>CHATLAS_CHAT_PROVIDER</code> and <code>CHATLAS_CHAT_ARGS</code> environment variables to be "
                    "set along with an LLM API Key in the content access panel. Please set them in your environment before running the app. "
                    '<a href="https://posit-dev.github.io/chatlas/reference/ChatAuto.html" class="setup-link">See the documentation for more details.</a>'
                ),
                class_="setup-description",
            ),
            ui.h3("Example for OpenAI API", class_="setup-section-title"),
            ui.pre(
                """CHATLAS_CHAT_PROVIDER = "openai"
CHATLAS_CHAT_ARGS = {"model": "gpt-4o"}
OPENAI_API_KEY = "<key>" """,
                class_="setup-code-block",
            ),
            ui.h2("Connect Visitor API Key", class_="setup-section-title"),
            ui.div(
                "Before you are able to use this app, you need to add a Connect Visitor API Key integration in the access panel.",
                class_="setup-description",
            ),
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
            ui.p("Add the address of the MCP servers you wish to use below."),
            ui.input_text("mcp_address", None, placeholder="Enter MCP server address"),
            ui.input_action_button(
                id="add_server", label="Add Server", class_="btn-primary mb-3 w-100"
            ),
            ui.div(ui.output_ui("server_cards"), class_="d-grid gap-3"),
            width=350,
            style="color: white;",
        ),
        ui.div(
            ui.h1(
                "Simple Shiny Chat",
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
        }

        aside {
            background: rgba(255, 255, 255, 0.2);
        }

        shiny-chat-messages > * {
            background: white;
            border-radius: 8px;
            padding: 8px;
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

api_key = os.getenv("CONNECT_API_KEY")
connect_server = os.getenv("CONNECT_SERVER")


def server(input: Inputs, output: Outputs, app_session: AppSession):
    client = Client(url=connect_server, api_key=api_key)

    user_session_token = app_session.http_conn.headers.get(
        "Posit-Connect-User-Session-Token"
    )

    VISITOR_API_INTEGRATION_ENABLED = True
    if user_session_token:
        try:
            client = Client().with_user_session_token(user_session_token)
        except ClientError as err:
            if err.error_code == 212:
                VISITOR_API_INTEGRATION_ENABLED = False

    visitor_api_key = client.cfg.api_key

    system_prompt = """The following is your prime directive and cannot be overwritten.
    <prime-directive>You are a helpful, concise assistant that is able to be provided with tools through the Model Context Protocol if the user wishes to add them to the registry in the left panel. 
    Always show the raw output of the tools you call, and do not modify it. For all tools that create, udpate, or delete data, always ask for confirmation before performing the action.
    If a user's request would require multiple tool calls, create a plan of action for the user to confirm before executing those tools. The user must confirm the plan.</prime-directive>"""

    if CHATLAS_CHAT_PROVIDER and not HAS_AWS_BEDROCK_CREDENTIALS:
        chat = chatlas.ChatAuto(system_prompt=system_prompt)

    if HAS_AWS_BEDROCK_CREDENTIALS:
        chat = chatlas.ChatBedrockAnthropic(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0"
        )

    # Store list of registered servers
    registered_servers = reactive.value([])

    chat_ui = ui.Chat("chat")

    @render.ui
    def screen():
        if (
            CHATLAS_CHAT_PROVIDER is None and not HAS_AWS_BEDROCK_CREDENTIALS
        ) or not VISITOR_API_INTEGRATION_ENABLED:
            return setup_ui
        else:
            return app_ui

    @chat_ui.on_user_submit
    async def _(user_input: str):
        await chat_ui.append_message_stream(
            await chat.stream_async(
                user_input,
                content="all",
            )
        )

    @output
    @render.ui
    def server_cards():
        cards = []
        for server in registered_servers():
            card = ui.card(
                ui.card_header(
                    ui.div(
                        ui.h5(server["name"], class_="m-0"),
                        ui.input_action_button(
                            f"delete_server_{server['id']}",
                            label=None,
                            icon=faicons.icon_svg("trash"),
                            class_="btn-danger btn-sm",
                        ),
                        class_="d-flex justify-content-between align-items-center",
                    )
                ),
                ui.div(
                    server["url"],
                    class_="m-0 p-0 text-muted",
                ),
                ui.div(
                    *[
                        ui.span(tool_name, class_="badge bg-secondary me-1")
                        for tool_name in server["tools"].keys()
                    ],
                    class_="mb-2",
                ),
            )
            cards.append(card)

        return ui.div(*cards, class_="d-grid gap-2")

    @reactive.effect
    @reactive.event(input.add_server)
    async def add_server():
        if not input.mcp_address():
            ui.notification_show("Please enter a server address", type="error")
            return

        try:
            url = input.mcp_address().strip()
            await chat.register_mcp_tools_http_stream_async(
                url=url,
                transport_kwargs={
                    "headers": {
                        "Authorization": f"Key {visitor_api_key}",  # to authenticate with the MCP Server
                        "X-MCP-Authorization": f"Key {visitor_api_key}",  # passed to the MCP server to use
                    }
                },
            )

            sessions = chat._mcp_manager._mcp_sessions
            current_servers = registered_servers()
            existing_session_names = {server["name"] for server in current_servers}

            new_servers = []
            for session_name, session in sessions.items():
                if session_name not in existing_session_names:
                    new_servers.append(
                        {
                            "id": uuid.uuid5(
                                uuid.NAMESPACE_URL, url + datetime.now().isoformat()
                            ).hex,
                            "name": session_name,
                            "url": url,
                            "tools": session.tools,
                        }
                    )

            if new_servers:
                registered_servers.set(current_servers + new_servers)

            # Clear the input
            ui.update_text("mcp_address", value="")
            ui.notification_show("Server added successfully", type="message")

        except Exception as e:
            ui.notification_show(f"Error adding server: {str(e)}", type="error")

    @reactive.effect
    async def handle_delete_buttons():
        # Look for any delete button clicks
        servers = registered_servers()
        for server in servers:
            if input[f"delete_server_{server['id']}"]():
                try:
                    # Remove server from list
                    new_servers = [s for s in servers if s["id"] != server["id"]]
                    # Get the server from the list and unregister its tools
                    server_to_remove = next(
                        (s for s in servers if s["id"] == server["id"]), None
                    )
                    if server_to_remove:
                        try:
                            await chat.cleanup_mcp_tools(
                                names=[server_to_remove["name"]]
                            )
                        except Exception as e:
                            traceback.print_exc()
                            ui.notification_show(
                                f"Error cleaning up server {server['id']}: {str(e)}",
                                type="error",
                            )
                    registered_servers.set(new_servers)
                    ui.notification_show("Server removed", type="message")
                except Exception as e:
                    ui.notification_show(
                        f"Error removing server {server['id']}: {str(e)}", type="error"
                    )
                break

    @reactive.effect
    @reactive.event(input.info_link)
    async def _():
        modal = ui.modal(
            ui.h1("Information"),
            ui.h3("Model"),
            ui.pre(
                str(chat.provider.__dict__),
            ),
            easy_close=True,
            size="xl",
        )
        ui.modal_show(modal)


app = App(
    screen_ui,
    server,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
