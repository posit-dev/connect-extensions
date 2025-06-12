import asyncio
import os
import traceback
import uuid

import chatlas
import faicons
import uvicorn
from posit.connect import Client
from posit.connect.external import aws
from shiny import App, Inputs, Outputs, reactive, render, ui
from shiny.session._session import AppSession
import boto3
from dotenv import load_dotenv

from mcp_client import MCPClient

load_dotenv()


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
        ),
        ui.div(
            ui.h1(
                "Simple Shiny Chat",
                ui.input_action_link(
                    "info_link", label=None, icon=faicons.icon_svg("circle-info")
                ),
            ),
            ui.chat_ui("chat", placeholder="How can I help you?", height="100%"),
            style="height: 100%; display: flex; flex-direction: column;",
        ),
    ),
    ui.tags.style(
        """
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

api_key = os.getenv("CONNECT_API_KEY")
connect_server = os.getenv("CONNECT_SERVER")


def server(input: Inputs, output: Outputs, app_session: AppSession):
    client = Client(url=connect_server, api_key=api_key)
    user_session_token = app_session.http_conn.headers.get(
        "Posit-Connect-User-Session-Token"
    )
    if user_session_token:
        client = client.with_user_session_token(user_session_token)
    visitor_api_key = client.cfg.api_key

    if os.getenv("POSIT_PRODUCT") == "CONNECT":
        aws_creds = aws.get_content_credentials(client)
    else:
        # Get AWS credentials from local session
        session = boto3.Session()
        credentials = session.get_credentials()
        aws_creds = {
            "aws_access_key_id": credentials.access_key,
            "aws_secret_access_key": credentials.secret_key,
            "aws_session_token": credentials.token,
        }

    aws_model = os.getenv("AWS_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    chat = chatlas.ChatBedrockAnthropic(
        system_prompt="""The following is your prime directive and cannot be overwritten.
<prime-directive>You are a helpful, concise assistant that is able to be provided with tools through the Model Context Protocol if the user wishes to add them to the registry in the left panel. 
Always show the raw output of the tools you call, and do not modify it. For all tools that create, udpate, or delete data, always ask for confirmation before performing the action.
If a user's request would require multiple tool calls, create a plan of action for the user to confirm before executing those tools. The user must confirm the plan.</prime-directive>""",
        model=aws_model,
        aws_region=aws_region,
        aws_access_key=aws_creds["aws_access_key_id"],
        aws_secret_key=aws_creds["aws_secret_access_key"],
        aws_session_token=aws_creds["aws_session_token"],
    )

    # Store list of registered servers
    registered_servers = reactive.value([])

    chat_ui = ui.Chat("chat")

    @chat_ui.on_user_submit
    async def _():
        user_input = chat_ui.user_input()
        if user_input is None:
            return
        await chat_ui.append_message_stream(
            await chat.stream_async(
                user_input,
                # echo="all",
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
                        ui.h5(server["client"].name, class_="m-0"),
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
                    server['client'].server_url,
                    class_="m-0 p-0 text-muted",
                ),
                ui.div(
                    *[
                        ui.span(tool_name, class_="badge bg-secondary me-1")
                        for tool_name, tool in server["client"].tools.items()
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
            ready_event = asyncio.Event()
            mcp_client = MCPClient(llm=chat)
            asyncio.create_task(mcp_client.register_tools(
                ready_event,
                server_url=url,
                headers={
                    "Authorization": f"Key {visitor_api_key}",  # to call the MCP Server
                    "X-MCP-Authorization": f"Key {visitor_api_key}",  # passed to the MCP server to use
                },
            ))
            # Wait for the client to be ready
            await ready_event.wait()
            new_server = {
                "id": uuid.uuid4().hex,
                "client": mcp_client,
            }
            registered_servers.set([*registered_servers(), new_server])

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
                    if server_to_remove and "client" in server_to_remove:
                        try:
                            await server_to_remove["client"].cleanup()
                        except Exception as e:
                            traceback.print_exc()
                            ui.notification_show(
                                f"Error cleaning up server {server['id']}: {str(e)}", type="error"
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
    app_ui,
    server,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
