import asyncio
import os
import threading
from posit import connect
from chatlas import ChatAuto, ChatBedrockAnthropic
import markdownify
from shiny import App, Inputs, Outputs, Session, ui, reactive, render

from helpers import (
    content_choice_label,
    content_ready,
    is_chattable_content,
    resolve_visitor_client,
    running_on_connect,
    truncate_for_context,
)

# Zero-config fallback model, used only when no LLM provider is configured. Bedrock
# picks up credentials from an instance role, so it needs no API key.
BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Cap the startup Bedrock probe so a reachable-but-slow endpoint can't hang the worker.
BEDROCK_PROBE_TIMEOUT_SECONDS = 10

# Give up on a reply that stalls between chunks. Streams run one at a time, so a
# provider that stops sending would otherwise hold that slot and leave the app
# looking frozen with its input disabled. Generous, because the first chunk for a
# large page can legitimately take a while, but far below the provider SDKs' own
# ten-minute default.
STREAM_STALL_TIMEOUT_SECONDS = 120

# Give up on a Connect API call (session exchange, listing content, opening an
# item). The SDK sets no request timeout of its own, so an unresponsive Connect
# server would otherwise hang the calling task indefinitely. This bounds how long
# the app waits, not how long the underlying thread runs: asyncio.to_thread can't
# interrupt a call already in flight, so a timeout here lets the app move on and
# report the failure, though the abandoned thread still runs until Connect (or the
# OS) eventually gives up on its end.
CONNECT_API_TIMEOUT_SECONDS = 30


def check_aws_bedrock_credentials():
    # Probe for usable Bedrock credentials by making a real (throwaway) Bedrock call.
    # Bedrock is the zero-config fallback: this only runs when no provider is set via
    # CHATLAS_CHAT_PROVIDER_MODEL, so an explicit choice is never probed over.
    # The probe makes a live network call at import, so run it under a timeout: a
    # reachable-but-slow Bedrock (partial credentials, throttling) must not block
    # worker startup. On timeout, fall back to the setup screen.
    outcome = {}

    def _probe():
        try:
            ChatBedrockAnthropic(model=BEDROCK_MODEL).chat("test", echo="none")
            outcome["ok"] = True
        except Exception as e:  # noqa: BLE001 - reported below, never raised
            outcome["error"] = e

    # A daemon thread, so a probe still blocked on a socket can't hold up process
    # exit when Connect restarts this content. A pooled thread is joined at exit.
    thread = threading.Thread(target=_probe, daemon=True)
    thread.start()
    thread.join(BEDROCK_PROBE_TIMEOUT_SECONDS)
    if outcome.get("ok"):
        return True
    reason = outcome.get("error", "timed out")
    print(
        f"AWS Bedrock credential probe failed or timed out; with no LLM provider "
        f"configured, the app will show the setup screen. Err: {reason}"
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


def error_ui(detail: str):
    # Shown when the app can't start for the viewer (e.g. the session couldn't be
    # read, or the chat provider couldn't be initialized), so the failure states why
    # in plain language instead of crashing. detail is always a self-contained,
    # non-technical sentence: the underlying error goes to the server log instead,
    # since a viewer can't act on SDK/vendor detail and it isn't meant for them.
    return ui.page_fillable(
        _SETUP_STYLE,
        ui.div(
            ui.div(
                ui.h1("Something went wrong", class_="setup-title"),
                ui.div(
                    detail,
                    class_="setup-description",
                ),
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
        # Rendered with its choices (see content_selector) rather than declared empty
        # and filled with update_select, so the dropdown paints already populated.
        ui.output_ui("content_selector"),
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
        // Cap the scraped HTML before sending it. A page carrying megabytes of
        // embedded scripts and data would exceed Shiny's websocket message limit,
        // which drops the whole session rather than reporting an error, and would
        // block the worker while it was converted to markdown. This is only a
        // transport limit; the server truncates the markdown again to fit the
        // model's context window.
        var MAX_HTML_CHARS = 1000000;

        window.Shiny.addCustomMessageHandler('update-iframe', function(message) {
            var iframe = document.getElementById('content_frame');
            iframe.src = message.url;

            iframe.onload = function() {
                var content;
                try {
                    content = iframe.contentWindow.document.documentElement.outerHTML;
                } catch (e) {
                    // Cross-origin: the frame loaded from a different origin (e.g. an
                    // external redirect), so we can't read it to summarize. Tell the
                    // server so it can inform the viewer instead of failing silently.
                    Shiny.setInputValue('iframe_read_failed', Date.now(), {priority: 'event'});
                    return;
                }
                // priority 'event' so selecting a different item whose HTML is
                // byte-identical to the last still re-fires and re-summarizes.
                Shiny.setInputValue('iframe_content', content.slice(0, MAX_HTML_CHARS), {priority: 'event'});
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
    # Unscoped: only ever passed into resolve_visitor_client below, which returns it
    # as-is off Connect or exchanges it for a viewer-scoped client on Connect.
    # Nothing else should read from this directly, since that would act with the
    # deployer's identity instead of the viewer's.
    deploy_client = connect.Client()
    # Errors from a reply are turned into a readable notification by stream_reply
    # below, so the built-in on_error handling is not used.
    chat_obj = ui.Chat("chat")

    on_connect = running_on_connect()
    token = (
        session.http_conn.headers.get("Posit-Connect-User-Session-Token")
        if on_connect
        else None
    )

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
    # chat_error carries a configured-but-broken provider (bad model, missing key):
    # initializing would otherwise raise and crash the session, so catch it and show
    # a readable error screen instead. Only an administrator can fix a broken
    # provider, so the raw error goes to the log rather than onto the screen.
    chat = None
    chat_error = None
    try:
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
    except Exception as err:
        chat_error = err.__cause__ or err
        print(f"chat-with-content: chat provider failed to start: {chat_error}")

    # Exchanging the session token, reading the viewer's name, and listing their
    # content are all blocking Connect API calls. server() runs synchronously while
    # Shiny holds a single, process-wide reactive lock to process this session's
    # "init" message, and a plain (non-async) effect runs under that same lock during
    # a flush, so a blocking call in either place would stall every other session on
    # this worker for as long as it takes. Running them in an extended task keeps
    # that work off the lock; to_thread keeps it off the event loop entirely, since
    # the SDK calls themselves are blocking I/O.
    @reactive.extended_task
    async def resolve_session():
        # Scope the client to the signed-in viewer, and never fall back to the
        # deploy client on Connect, which would list the deployer's content as if it
        # were the viewer's. Without the Visitor API Key integration,
        # integration_enabled is False so the setup screen shows; session_error
        # carries the cases setup can't fix (no signed-in viewer, or the exchange
        # failing) so the screen can say why.
        try:
            scoped_client, integration_enabled, session_error = await asyncio.wait_for(
                asyncio.to_thread(
                    resolve_visitor_client, deploy_client, on_connect, token
                ),
                CONNECT_API_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            print(
                f"chat-with-content: session token exchange timed out after "
                f"{CONNECT_API_TIMEOUT_SECONDS} seconds"
            )
            scoped_client, integration_enabled, session_error = (
                deploy_client,
                True,
                "Couldn't read your Connect session: Connect didn't respond in "
                "time. Try reloading the page.",
            )
        name = "you"
        # None until content is actually attempted, so the loading effect below can
        # tell "not set up yet" apart from "set up, but there's nothing to show".
        choices = None
        content_error = None
        if content_ready(session_error, chat, integration_enabled):

            async def _load_choices():
                nonlocal choices, content_error
                try:
                    content_list = await asyncio.wait_for(
                        asyncio.to_thread(fetch_connect_content_list, scoped_client),
                        CONNECT_API_TIMEOUT_SECONDS,
                    )
                    # Build the labels here too, so a bad item surfaces the error
                    # rather than silently leaving the selector empty.
                    choices = {
                        item["guid"]: content_choice_label(item)
                        for item in content_list
                    }
                except Exception as err:
                    # The raw cause may be full of Connect API/SDK detail a viewer
                    # can't act on, so it goes to the log rather than onto the toast.
                    if isinstance(err, asyncio.TimeoutError):
                        cause = f"timed out after {CONNECT_API_TIMEOUT_SECONDS} seconds"
                    else:
                        cause = err.__cause__ or err
                    print(f"chat-with-content: couldn't load content list: {cause}")
                    content_error = (
                        "Couldn't load your content from Connect. Try reloading "
                        "the page; if this keeps happening, contact your "
                        "administrator."
                    )

            async def _load_name():
                nonlocal name
                try:
                    me = await asyncio.wait_for(
                        asyncio.to_thread(lambda: scoped_client.me),
                        CONNECT_API_TIMEOUT_SECONDS,
                    )
                    name = (
                        f"{me.get('first_name', '')} {me.get('last_name', '')}".strip()
                        or me.get("username")
                        or "you"
                    )
                except Exception:
                    pass

            # Independent of each other, so run them concurrently rather than
            # paying for two sequential Connect API round trips.
            await asyncio.gather(_load_choices(), _load_name())
        return (
            scoped_client,
            integration_enabled,
            session_error,
            name,
            choices,
            content_error,
        )

    resolve_session()
    # Nothing needs the result after the viewer has left.
    session.on_ended(resolve_session.cancel)

    @render.ui
    def screen():
        _, integration_enabled, session_error, _, _, _ = resolve_session.result()
        # An unusable session blocks everything, so show it before anything else.
        # The helper supplies the detail because the reason differs: no signed-in
        # viewer reads differently from an exchange that failed.
        if session_error is not None:
            return error_ui(session_error)
        # A configured-but-broken chat provider can't be fixed from the setup screen,
        # so say what actually failed rather than showing setup steps.
        if chat_error is not None:
            return error_ui(
                "Couldn't start the chat provider, so the app can't answer "
                "questions about your content. Contact your administrator to check "
                "the LLM provider configuration; the technical detail is in the "
                "application logs."
            )
        # Show only the setup step(s) still missing; otherwise the app itself.
        need_llm = chat is None
        need_integration = not integration_enabled
        if need_llm or need_integration:
            return setup_ui(need_llm, need_integration)
        return app_ui

    # Explain in-app how identity and permissions flow, using the viewer's own name
    @render.ui
    def identity_note():
        _, _, _, name, _, _ = resolve_session.result()
        return ui.p(
            "Signed in as ",
            ui.strong(name),
            ", resolved from your Connect session. Content is listed and read "
            "with your own permissions through a Connect Visitor API Key. No "
            "admin key is stored, and answers draw only on the content you select.",
            class_="text-muted small",
        )

    # The content selector's choices. Held in a reactive value and rendered directly
    # by content_selector, so the dropdown is populated when it first paints instead
    # of racing an update_select message against the dynamically rendered screen.
    selector_choices = reactive.Value({})

    # Load the viewer's content into the selector once resolve_session finishes.
    @reactive.Effect
    def _():
        _, _, _, _, choices, content_error = resolve_session.result()
        if content_error is not None:
            # duration=None so the reason stays visible instead of leaving a blank
            # selector once a transient toast fades.
            ui.notification_show(content_error, type="error", duration=None)
            return
        if choices is None:
            # Not attempted: a session error, no chat, or no integration, so the
            # setup or error screen is up and there's nothing to load for yet.
            return
        if not choices:
            ui.notification_show(
                "You don't have any content available to chat with.",
                type="message",
                duration=None,
            )
            return
        selector_choices.set({"": "Select content", **choices})

    @render.ui
    def content_selector():
        return ui.input_selectize(
            "content_selection",
            "",
            choices=selector_choices.get(),
            width="100%",
        )

    # Selecting new content supersedes a reply that is still streaming for the
    # previous item. A plain holder (not reactive) so the streaming task below can
    # read it without a reactive context.
    content_token = {"n": 0}

    # What the last summary was built from, so a repeated frame load doesn't buy a
    # second identical summary.
    last_summary = {"token": None, "markdown": None}

    # Every reply streams through this one extended task. Shiny queues a call made
    # while the task is running and starts it only once the previous one has fully
    # finished, so exactly one stream is ever in flight. Two at once would fight over
    # the chat object: the transcript holds one stream at a time and queues the
    # other's chunks behind it (dropping some), and each request sends the provider
    # the other's half-written turn.
    async def reset_conversation():
        # Clear the transcript and the model's memory together, so the chat is never
        # left answering from an item that is no longer in the frame.
        await chat_obj.clear_messages()
        chat.set_turns([])
        last_summary["token"], last_summary["markdown"] = None, None

    @reactive.extended_task
    async def stream_reply(page: str | None, token: int, new_content: bool):
        # For a summary, `page` is the scraped HTML; for a question it is the text the
        # viewer typed. A summary with no page means the frame couldn't be read.
        #
        # Only a summary is dropped when a newer selection supersedes it. A question
        # has already been shown in the transcript with a spinner, so dropping it
        # would leave a blank answer there with nothing explaining why.
        if new_content and token != content_token["n"]:
            return
        try:
            if new_content:
                if page is None:
                    await reset_conversation()
                    return
                try:
                    # Converted here rather than in the effect that scraped it: an
                    # effect runs inside the process-wide reactive lock and holds it
                    # across every await, so converting a large page there would
                    # stall every session on this worker. An extended task runs
                    # outside that lock.
                    markdown = truncate_for_context(
                        await asyncio.to_thread(
                            markdownify.markdownify, page, heading_style="atx"
                        )
                    )
                except Exception as err:
                    await reset_conversation()
                    print(
                        f"chat-with-content: couldn't convert content to summarize "
                        f"it: {err.__cause__ or err}"
                    )
                    ui.notification_show(
                        "Couldn't read this content to summarize it. Try selecting "
                        "it again; if this keeps happening, contact your "
                        "administrator.",
                        type="error",
                        duration=None,
                    )
                    return
                # One selection can load the frame more than once (a page that
                # refreshes itself, for instance). Summarizing the same text again
                # would only spend another request to say the same thing.
                if (token, markdown) == (
                    last_summary["token"],
                    last_summary["markdown"],
                ):
                    return
                await reset_conversation()
                last_summary["token"], last_summary["markdown"] = token, markdown
                # Content and request go as one user turn. Two user turns in a row
                # are rejected by strict providers (Anthropic on Bedrock, the
                # zero-config fallback).
                prompt = (
                    f"<context>{markdown}</context>\n\n"
                    'Write a brief "### Summary" of the content.'
                )
            else:
                prompt = page
            # message_stream_context appends from this task, so the queue above
            # covers the whole stream. append_message_stream would instead start a
            # second background task and return, leaving nothing to serialize.
            async with chat_obj.message_stream_context() as stream:
                reply = await chat.stream_async(prompt)
                while True:
                    # Waiting per chunk rather than around the whole stream, so a
                    # long-but-healthy reply is never cut off while a stalled one
                    # still releases the queue.
                    try:
                        chunk = await asyncio.wait_for(
                            reply.__anext__(), STREAM_STALL_TIMEOUT_SECONDS
                        )
                    except StopAsyncIteration:
                        break
                    # Again, only a summary is abandoned mid-stream; an answer the
                    # viewer asked for is finished even if they moved on.
                    if new_content and token != content_token["n"]:
                        return
                    await stream.append(chunk)
        except Exception as err:
            # Forget which page was summarized, so a reload of the same page is
            # allowed to retry rather than being taken for a duplicate.
            last_summary["token"], last_summary["markdown"] = None, None
            # The provider records the question and an empty placeholder answer
            # before the first chunk arrives, so a request that fails that early
            # leaves the placeholder behind. Providers drop an empty answer, which
            # leaves two questions in a row and makes every later request fail, so
            # forget the failed exchange.
            turns = chat.get_turns()
            if turns and turns[-1].role == "assistant" and not turns[-1].contents:
                chat.set_turns(turns[:-2])
            if isinstance(err, asyncio.TimeoutError):
                # Already a plain-language description, not a raw exception, so
                # showing it to the viewer directly is fine.
                message = (
                    "Couldn't get a response from the chat provider: it stopped "
                    f"responding after {STREAM_STALL_TIMEOUT_SECONDS} seconds. Try "
                    "asking again."
                )
            else:
                # The raw cause may be full of provider SDK detail a viewer can't act
                # on, so it goes to the log rather than onto the toast.
                print(
                    f"chat-with-content: chat provider request failed: "
                    f"{err.__cause__ or err}"
                )
                message = (
                    "Couldn't get a response from the chat provider. Try asking "
                    "again; if this keeps happening, contact your administrator."
                )
            ui.notification_show(message, type="error", duration=None)

    # Stop a reply the viewer will never see. Nothing streams after the session
    # ends, so there is no later stream for the cancellation to disturb.
    session.on_ended(stream_reply.cancel)

    # Update iframe when content selection changes
    @reactive.Effect
    @reactive.event(input.content_selection)
    async def _():
        selection = input.content_selection()
        if not selection:
            return
        # The dropdown is only populated once resolve_session has succeeded, so its
        # result is available here without blocking.
        scoped_client, _, _, _, _, _ = resolve_session.result()
        try:
            # to_thread: content.get() is blocking I/O, and this effect runs under
            # the process-wide reactive lock during a flush (see resolve_session).
            content = await asyncio.wait_for(
                asyncio.to_thread(scoped_client.content.get, selection),
                CONNECT_API_TIMEOUT_SECONDS,
            )
        except Exception as err:
            # The raw cause may be full of Connect API/SDK detail a viewer can't act
            # on, so it goes to the log rather than onto the toast.
            if isinstance(err, asyncio.TimeoutError):
                cause = f"timed out after {CONNECT_API_TIMEOUT_SECONDS} seconds"
            else:
                cause = err.__cause__ or err
            print(f"chat-with-content: couldn't open content {selection}: {cause}")
            ui.notification_show(
                "Couldn't open that content. Try selecting it again; if this keeps "
                "happening, contact your administrator.",
                type="error",
                duration=None,
            )
            return
        # The URL is optional in the Connect API, so read it by key and say when it
        # is missing rather than raising out of this effect with nothing shown.
        url = content.get("content_url")
        if not url:
            ui.notification_show(
                "Couldn't open that content: Connect didn't give a URL for it.",
                type="error",
                duration=None,
            )
            return
        # Supersede any reply still streaming for the previous item, but only now
        # that the new item has opened: a selection that failed to open leaves the
        # previous item in the frame, so its reply is still the right one. The
        # transcript is replaced when the new summary starts (below).
        content_token["n"] += 1
        await session.send_custom_message("update-iframe", {"url": url})

    # The frame loaded from a different origin, so it can't be read to summarize.
    @reactive.Effect
    @reactive.event(input.iframe_read_failed)
    async def _():
        ui.notification_show(
            "Couldn't read this content to summarize it, because it loaded from a "
            "different location.",
            type="error",
            duration=None,
        )
        # Sent through the queue with no page, which empties the chat. Otherwise the
        # transcript and the model would keep the previous item while the frame shows
        # this one, and the next answer would describe content the viewer can't see.
        if chat is not None:
            stream_reply(None, content_token["n"], new_content=True)

    # Process iframe content when it changes
    @reactive.Effect
    @reactive.event(input.iframe_content)
    async def _():
        if chat is None or not input.iframe_content():
            return
        # The page goes over as-is; converting and truncating it happens in the task,
        # off the reactive lock this effect holds.
        stream_reply(input.iframe_content(), content_token["n"], new_content=True)

    # Handle chat messages
    @chat_obj.on_user_submit
    async def _(message):
        if chat is None:
            return
        stream_reply(message, content_token["n"], new_content=False)


app = App(screen_ui, server)
