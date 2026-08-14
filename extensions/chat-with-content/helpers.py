import os
from datetime import datetime, timezone

import requests

# Static/rendered content the app can extract text from. Interactive apps (Shiny,
# Streamlit, ...) render in the browser, so their HTML holds no content to chat with.
CHATTABLE_APP_MODES = ("jupyter-static", "quarto-static", "rmd-static", "static")

# Upper bound on the markdown handed to the LLM. A large report can produce a DOM
# far bigger than the model's context window; truncating keeps the request within
# bounds instead of erroring, at the cost of dropping the tail of very long pages.
MAX_CONTEXT_CHARS = 100_000

# How long a single Connect HTTP request may stall. This is requests' read timeout,
# i.e. the gap between bytes, so a slow but progressing response (a large paginated
# content list) is not cut off; only a genuinely stuck one is.
CONNECT_REQUEST_TIMEOUT_SECONDS = 60


# The SDK ships its session with no timeout of its own, so a Connect server that
# accepts a connection and then goes quiet would hang the calling thread forever.
# app.py runs these calls through asyncio.to_thread, which can stop waiting on a
# stuck call but cannot interrupt it, so without a deadline here those threads
# accumulate and eventually starve the worker. Supplying the default through an
# adapter uses requests' own extension point rather than reaching into the SDK.
class _TimeoutAdapter(requests.adapters.HTTPAdapter):
    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = CONNECT_REQUEST_TIMEOUT_SECONDS
        return super().send(request, **kwargs)


# Applied to every client the app uses. The token exchange builds a fresh client
# with its own session, so that one needs it as much as the deploy client does.
def with_request_timeout(client):
    for prefix in ("http://", "https://"):
        client.session.mount(prefix, _TimeoutAdapter())
    return client


# Both env vars are checked because a missed "on Connect" detection would fall back
# to the deploy client for a viewer (see resolve_visitor_client), so err toward True.
def running_on_connect():
    return "CONNECT" in (os.getenv("POSIT_PRODUCT"), os.getenv("RSTUDIO_PRODUCT"))


# What the viewer is told when their session can't be used at all. Adding the
# integration fixes neither case, so these are kept separate from the setup screen.
# Self-contained sentences: the underlying error, if any, goes to the server log
# instead (see resolve_visitor_client), since a viewer can't act on it and it may
# be full of vendor/SDK detail that isn't meant for them.
NO_SESSION_DETAIL = (
    "Couldn't read your Connect session, so the app can't list or read content as "
    "you. Make sure you're signed in to Connect. If you are, your administrator may "
    "need to enable OAuth integrations on this server."
)
EXCHANGE_FAILED_DETAIL = (
    "Couldn't read your Connect session, so the app can't list or read content as "
    "you. Contact your administrator; the technical detail is in the application logs."
)
# Raised by app.py, not resolve_visitor_client: the exchange itself has no timeout,
# so app.py bounds the call with asyncio.wait_for and reports this on expiry.
SESSION_TIMEOUT_DETAIL = (
    "Couldn't read your Connect session, so the app can't list or read content as "
    "you. Connect didn't respond in time; try reloading the page."
)


# Returns (client, integration_enabled, session_error), where session_error is the
# detail to show the viewer when their session can't be used, or None otherwise. The
# gate is the point: never fall back to the deploy client for a viewer, because that
# would list the deployer's content as if it were theirs. Off Connect, the deploy
# client is the intended one.
def resolve_visitor_client(client, on_connect, token):
    if not on_connect:
        return client, True, None
    if not token:
        # No token means there is no signed-in viewer to act as: content that allows
        # anonymous access sends none, and OAuth integrations may be off server-wide.
        # Neither is fixed on the Access tab, so say that rather than showing setup.
        return client, True, NO_SESSION_DETAIL
    try:
        return with_request_timeout(client.with_user_session_token(token)), True, None
    except Exception as err:
        # Compare as a string so a code reported as 212 or "212" both count as the
        # missing-integration case (setup screen) rather than a scary error screen.
        if str(getattr(err, "error_code", "")) == "212":
            return client, False, None
        # The raw error may be full of SDK/vendor detail a viewer can't act on, so it
        # goes to the log for an administrator rather than onto the screen.
        raw = getattr(err, "error_message", None) or str(err)
        print(f"chat-with-content: session token exchange failed: {raw}")
        return client, True, EXCHANGE_FAILED_DETAIL


# Whether the app is fully set up and should load and use the viewer's content.
# The content selector runs as a reactive effect independent of the rendered
# screen, so it gates on this itself: a token error leaves the client as the
# unscoped deploy client (must never load with it), and a missing LLM or
# integration means the setup screen is up, so there's nothing to load for yet.
def content_ready(token_error, chat, integration_enabled):
    return token_error is None and chat is not None and integration_enabled


def time_since_deployment(deployment_time_str):
    # Content that has never been deployed reports no time; skip the label rather
    # than crash on a None passed to fromisoformat().
    if not deployment_time_str:
        return ""

    try:
        deployment_time = datetime.fromisoformat(
            deployment_time_str.replace("Z", "+00:00")
        )
    except (AttributeError, TypeError, ValueError):
        # A malformed timestamp shouldn't crash the whole content list; just omit
        # the "last deployed" phrase for this one item. AttributeError covers a
        # value that isn't a string at all, which has no .replace().
        return ""
    # A timestamp with no offset would raise when subtracted from an aware "now";
    # treat it as UTC so a naive-but-valid time still renders instead of crashing.
    if deployment_time.tzinfo is None:
        deployment_time = deployment_time.replace(tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)

    time_diff = current_time - deployment_time
    total_seconds = time_diff.total_seconds()

    # Deployment time slightly in the future (clock skew between servers).
    if total_seconds < 0:
        return "last deployed in the future"

    if total_seconds < 60:
        value = int(total_seconds)
        unit = "second" if value == 1 else "seconds"
    elif total_seconds < 3600:  # Less than 1 hour
        value = int(total_seconds // 60)
        unit = "minute" if value == 1 else "minutes"
    elif total_seconds < 86400:  # Less than 1 day
        value = int(total_seconds // 3600)
        unit = "hour" if value == 1 else "hours"
    elif total_seconds < 604800:  # Less than 1 week
        value = int(total_seconds // 86400)
        unit = "day" if value == 1 else "days"
    elif total_seconds < 2629746:  # Less than 1 month (avg 30.44 days)
        value = int(total_seconds // 604800)
        unit = "week" if value == 1 else "weeks"
    elif total_seconds < 31556952:  # Less than 1 year (365.24 days)
        value = int(total_seconds // 2629746)
        unit = "month" if value == 1 else "months"
    else:
        value = int(total_seconds // 31556952)
        unit = "year" if value == 1 else "years"

    return f"last deployed {value} {unit} ago"


# Content items are read with .get() throughout: Connect leaves optional fields out
# of the payload, and the SDK raises AttributeError for a field accessed as an
# attribute but absent, which would take out the whole content list over one unusual
# item. Attribute access is also deprecated in the SDK in favour of key access.
def is_chattable_content(item):
    return (
        item.get("app_mode") in CHATTABLE_APP_MODES
        and item.get("app_role") != "none"
        and item.get("content_category") != "pin"
    )


def content_choice_label(item):
    title = item.get("title") or item.get("name") or item.get("guid")
    # .get() also sidesteps ContentItem.owner, a property that fetches the owner
    # over HTTP (one request per item) when Connect didn't include it.
    owner = item.get("owner") or {}
    name = f"{owner.get('first_name') or ''} {owner.get('last_name') or ''}".strip()
    deployed = time_since_deployment(item.get("last_deployed_time"))

    # Join only the parts we actually have so the label never shows " -  ".
    suffix = " ".join(part for part in (name, deployed) if part)
    return f"{title} - {suffix}" if suffix else title


def truncate_for_context(markdown, max_chars=MAX_CONTEXT_CHARS):
    if len(markdown) <= max_chars:
        return markdown
    kept = markdown[:max_chars]
    # Cutting mid-page can leave a code fence open, which would make the model read
    # the notice below as more code instead of as a note about the content. Only a
    # fence starting a line opens or closes a block: page content that merely
    # mentions ``` mid-line must not be counted, or a balanced block would be
    # "closed" again and the notice pushed inside the new one.
    fences = sum(1 for line in kept.splitlines() if line.lstrip().startswith("```"))
    if fences % 2:
        kept += "\n```"
    return (
        kept
        + "\n\n[Content truncated because it exceeds the size this app sends to the model.]"
    )
