# -*- coding: utf-8 -*-
# mypy: ignore-errors
import json
import sys

import jwt
from posit.connect.client import Client
from shiny import App, Inputs, Outputs, Session, render, ui

style = 'background-color: #f6f6f6; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; width: 60%;'
app_ui = ui.page_fluid(
    ui.row(ui.h3("Session Token")),
    ui.row(ui.output_text_verbatim("raw_session_token_text"), style=style),
    ui.row(ui.output_text_verbatim("parsed_session_token_text"), style=style+'height: 12em;'),
    ui.row(ui.span(style="padding: 1em")),
    ui.row(ui.h3("Access Token")),
    ui.row(ui.output_text_verbatim("raw_access_token_text"), style=style),
    ui.row(ui.output_text_verbatim("parsed_access_token_text"), style=style+'height: 12em;')
)

def server(input: Inputs, output: Outputs, session: Session):
    """
    Shiny for Python example application that shows how to obtain
    an OAuth Access Token from Connect using the `/credentials` endpoint
    by exchanging a user-session-token
    """
    session_token = session.http_conn.headers.get(
        "Posit-Connect-User-Session-Token", "session_token not found.")

    with Client() as client:
        try:
            credentials = client.oauth.get_credentials(session_token)
        except Exception as e:
            print(f"Unable to fetch credentials: %s" % e, file=sys.stderr)
            credentials = dict()

    @render.text
    def raw_session_token_text():
        return session_token

    @render.text
    def parsed_session_token_text():
        try:
            token = jwt.decode(jwt=session_token, options={"verify_signature": False})
            return json.dumps(token, indent=4)
        except jwt.exceptions.DecodeError:
            return "unable to parse session_token."

    @render.text
    def raw_access_token_text():
        return credentials.get("access_token", "access_token not found.")

    @render.text
    def parsed_access_token_text():
        try:
            token = jwt.decode(jwt=credentials.get("access_token"), options={"verify_signature": False})
            return json.dumps(token, indent=4)
        except jwt.exceptions.DecodeError:
            return credentials.get("access_token", "unable to parse access_token.")


app = App(app_ui, server)
