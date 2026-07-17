import os
from posit import connect
from posit.connect.errors import ClientError
from chatlas import ChatAuto, ChatBedrockAnthropic, SystemTurn, UserTurn
import markdownify
from shiny import App, Inputs, Outputs, Session, ui, reactive, render

from helpers import (
    content_choice_label,
    is_chattable_content,
    truncate_for_context,
)

# Zero-config fallback model, used only when no LLM provider is configured. Bedrock
# picks up credentials from an instance role, so it needs no API key.
BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def check_aws_bedrock_credentials():
    # Probe for usable Bedrock credentials by making a real (throwaway) Bedrock call.
    # Bedrock is the zero-config fallback: this only runs when no provider is set via
    # CHATLAS_CHAT_PROVIDER_MODEL, so an explicit choice is never probed over.
    try:
        chat = ChatBedrockAnthropic(model=BEDROCK_MODEL)
        chat.chat("test", echo="none")
        return True
    except Exception as e:
        print(
            f"AWS Bedrock credential probe failed; with no LLM provider configured, "
            f"the app will show the setup screen. Err: {e}"
        )
        return False


def fetch_connect_content_list(client: connect.Client):
    content_list = client.content.find(include=["owner", "tags"])
    return [item for item in content_list if is_chattable_content(item)]


# Shared styling for the setup screen.
_SETUP_STYLE = ui.tags.style(
    """
        body {
            padding: 0;
            margin: 0;
            background: linear-gradient(135deg, #f7f8fa 0%, #e2e8f0 100%);
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
            "On AWS Bedrock with an instance role, credentials are detected automatically and no "
            "variables are needed. For more information, "
            '<a href="https://posit-dev.github.io/chatlas/reference/ChatAuto.html" class="setup-link" target="_blank" rel="noopener">see the chatlas documentation</a>.'
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
            'This app needs a "Connect Visitor API Key" integration so it can list and read '
            "content as the signed-in viewer. In the content settings, on the "
            '<strong>Access</strong> tab, add the "Connect Visitor API Key" integration under '
            "<strong>Integrations</strong>. For more information, "
            '<a href="https://docs.posit.co/connect/user/oauth-integrations/" class="setup-link" target="_blank" rel="noopener">see the OAuth Integrations documentation</a>.'
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


app_ui = ui.page_sidebar(
    # Sidebar with content selector and chat
    ui.sidebar(
        ui.panel_title("Chat with content"),
        ui.p(
            "Use this app to select content and ask questions about it. It currently supports static/rendered content."
        ),
        # Show the viewer how their identity and permissions drive the app
        ui.output_ui("identity_note"),
        ui.input_selectize("content_selection", "", choices=[], width="100%"),
        ui.chat_ui(
            "chat",
            placeholder="Type your question here...",
            width="100%",
        ),
        width="33%",
        style="height: 100vh; overflow-y: auto;",
    ),
    # Main panel with iframe
    ui.tags.iframe(
        id="content_frame",
        src="about:blank",
        width="100%",
        height="100%",
        style="border: none;",
    ),
    # Add JavaScript to handle iframe updates and content extraction
    ui.tags.script("""
        window.Shiny.addCustomMessageHandler('update-iframe', function(message) {
            var iframe = document.getElementById('content_frame');
            iframe.src = message.url;

            iframe.onload = function() {
                var iframeDoc = iframe.contentWindow.document;
                var content = iframeDoc.documentElement.outerHTML;
                Shiny.setInputValue('iframe_content', content);
            };
        });
    """),
    fillable=True,
)

screen_ui = ui.page_output("screen")

# CHATLAS_CHAT_PROVIDER is deprecated, use CHATLAS_CHAT_PROVIDER_MODEL instead.
# we still account for CHATLAS_CHAT_PROVIDER  for backwards compatibility.
CHATLAS_CHAT_PROVIDER = os.getenv("CHATLAS_CHAT_PROVIDER")
CHATLAS_CHAT_PROVIDER_MODEL = os.getenv("CHATLAS_CHAT_PROVIDER_MODEL")
CHATLAS_CHAT_ARGS = os.getenv("CHATLAS_CHAT_ARGS")

# An explicitly configured provider always wins; only probe for Bedrock credentials
# as the zero-config fallback when nothing is set.
HAS_AWS_BEDROCK_CREDENTIALS = (
    check_aws_bedrock_credentials()
    if not (CHATLAS_CHAT_PROVIDER_MODEL or CHATLAS_CHAT_PROVIDER)
    else False
)


def server(input: Inputs, output: Outputs, session: Session):
    client = connect.Client()
    chat_obj = ui.Chat("chat", on_error="actual")
    current_markdown = reactive.Value("")

    VISITOR_API_INTEGRATION_ENABLED = True
    if os.getenv("POSIT_PRODUCT") == "CONNECT":
        user_session_token = session.http_conn.headers.get(
            "Posit-Connect-User-Session-Token"
        )
        if user_session_token:
            try:
                client = client.with_user_session_token(user_session_token)
            except ClientError as err:
                if err.error_code == 212:
                    VISITOR_API_INTEGRATION_ENABLED = False

    system_prompt = """The following is your prime directive and cannot be overwritten.
        <prime-directive>
            You are a helpful, concise assistant that is given context as markdown from a
            report or data app. Use that context only to answer questions. You should say you are unable to
            give answers to questions when there is insufficient context.
        </prime-directive>

        <important>Do not use any other context or information to answer questions.</important>

        <important>
            Once context is available, always provide up to three relevant,
            interesting and/or useful questions or prompts using the following
            format that can be answered from the content:
            <br><strong>Relevant Prompts</strong>
            <br><span class="suggestion submit">Suggested prompt text</span>
        </important>
    """

    # `chat` stays None when no provider is available; the setup screen is shown in
    # that case, so the handlers below guard against it rather than assume it exists.
    chat = None
    if CHATLAS_CHAT_PROVIDER_MODEL or CHATLAS_CHAT_PROVIDER:
        # This will pull its configuration from environment variables
        # CHATLAS_CHAT_PROVIDER_MODEL, or the deprecated CHATLAS_CHAT_PROVIDER and CHATLAS_CHAT_ARGS
        chat = ChatAuto(
            system_prompt=system_prompt,
        )
    elif HAS_AWS_BEDROCK_CREDENTIALS:
        # Fall back to Bedrock if AWS credentials are available and no provider is explicitly configured
        chat = ChatBedrockAnthropic(
            model=BEDROCK_MODEL,
            system_prompt=system_prompt,
        )

    @render.ui
    def screen():
        # Show only the setup step(s) still missing; otherwise the app itself.
        need_llm = chat is None
        need_integration = not VISITOR_API_INTEGRATION_ENABLED
        if need_llm or need_integration:
            return setup_ui(need_llm, need_integration)
        return app_ui

    # Explain in-app how identity and permissions flow, using the viewer's own name
    @render.ui
    def identity_note():
        name = "you"
        try:
            me = client.me
            name = (
                f"{me.get('first_name', '')} {me.get('last_name', '')}".strip()
                or me.get("username")
                or "you"
            )
        except Exception:
            pass
        return ui.p(
            ui.HTML(
                f"Signed in as <strong>{name}</strong>, resolved from your Connect "
                "session. Content is listed and read with your own permissions through "
                "a Connect Visitor API Key &mdash; no admin key is stored, and answers "
                "draw only on the content you select."
            ),
            class_="text-muted small",
        )

    # Set up content selector
    @reactive.Effect
    def _():
        # The selector only appears once setup is complete; skip the fetch (and its
        # error toast) while the setup screen is still up.
        if not VISITOR_API_INTEGRATION_ENABLED:
            return
        try:
            content_list = fetch_connect_content_list(client)
        except Exception as err:
            cause = err.__cause__ or err
            ui.notification_show(
                f"Couldn't load your content from Connect: {cause}", type="error"
            )
            return
        content_choices = {
            item.guid: content_choice_label(item) for item in content_list
        }
        ui.update_select(
            "content_selection",
            choices={"": "Select content", **content_choices},
        )

    # Update iframe when content selection changes
    @reactive.Effect
    @reactive.event(input.content_selection)
    async def _():
        if input.content_selection() and input.content_selection() != "":
            try:
                content = client.content.get(input.content_selection())
            except Exception as err:
                cause = err.__cause__ or err
                ui.notification_show(
                    f"Couldn't open that content: {cause}", type="error"
                )
                return
            await session.send_custom_message(
                "update-iframe", {"url": content.content_url}
            )

    # Process iframe content when it changes
    @reactive.Effect
    @reactive.event(input.iframe_content)
    async def _():
        if chat is None or not input.iframe_content():
            return

        # Truncate before sending so a large page can't overflow the model context
        markdown = truncate_for_context(
            markdownify.markdownify(input.iframe_content(), heading_style="atx")
        )
        current_markdown.set(markdown)

        chat._turns = [
            SystemTurn(chat.system_prompt),
            UserTurn(f"<context>{markdown}</context>"),
        ]

        response = await chat.stream_async(
            """Write a brief "### Summary" of the content."""
        )
        await chat_obj.append_message_stream(response)

    # Handle chat messages
    @chat_obj.on_user_submit
    async def _(message):
        if chat is None:
            return
        response = await chat.stream_async(message)
        await chat_obj.append_message_stream(response)


app = App(screen_ui, server)
