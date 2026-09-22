# Copyright (C) 2026 by Posit Software, PBC.

"""A chat app whose skills come from a Connect agent plugin marketplace.

The point it teaches: the skills an agent can use are decided by **Connect**,
per signed-in viewer, not by this app and not by whoever deployed it.

One deployment serves everyone. When a viewer opens it, Connect attaches a
short-lived `Posit-Connect-User-Session-Token` to the request. The app posts
that token to Connect, which answers with the marketplaces that viewer may
read and a credential for each. The app then clones each marketplace from its
own upstream -- Package Manager, GitHub, wherever it lives. Connect is not in
the clone path.

Two things gate what arrives. The content must be associated with an Agent
Plugins integration, or Connect refuses outright; and each marketplace's own
access list decides whether this viewer is on it. Access is per marketplace,
not per plugin, because the upstream authorizes whole repositories.

The skills then reach the model three ways, differing in who chooses:

  * As a tool. Each one is registered with chatlas as `load_skill`, so the
    model asks for a skill's instructions when it judges them relevant. This
    mirrors how Posit Assistant and Claude Code expose skills -- a real tool
    call carrying the skill's name -- so the call is visible on the wire and
    in Connect's gateway telemetry rather than buried in a prompt.
  * As a slash command, so a person who already knows which skill applies can
    invoke it instead of hoping the model agrees. Slash commands come from
    shinychat, the chat widget: Connect decides which skills exist for this
    viewer, and the client decides how they are offered.
  * Pinned into the system prompt, for a skill that should be in force for a
    whole conversation regardless of what the model decides.

Until both an LLM provider and the Agent Plugins integration are configured,
the app shows a setup screen instead of the chat. There is deliberately no
fallback to the deploying user's own identity: that would hand a viewer the
owner's marketplaces, which is the bypass this design exists to prevent.

What is *not* a product feature: chatlas has no plugin, skill, or marketplace
concept, and neither does Connect's content path today. The acquiring logic
here is app code, and it is the argument for declaring plugins in the manifest
and restoring them at build time rather than a substitute for it.
"""

import atexit
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import chatlas
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

# Connect injects both. The API key says which content is asking; it is not
# an identity this app ever acts as.
CONNECT_SERVER = os.environ.get("CONNECT_SERVER", "").rstrip("/")
CONNECT_API_KEY = os.environ.get("CONNECT_API_KEY", "")

# chatlas reads these itself. They are read here only to detect whether a
# model is configured, which decides whether to show the setup screen.
CHATLAS_CHAT_PROVIDER_MODEL = os.environ.get("CHATLAS_CHAT_PROVIDER_MODEL")
CHATLAS_CHAT_PROVIDER = os.environ.get("CHATLAS_CHAT_PROVIDER")
LLM_CONFIGURED = bool(CHATLAS_CHAT_PROVIDER_MODEL or CHATLAS_CHAT_PROVIDER)

# Connect attaches this to every interactive content request, naming the
# person viewing the app.
SESSION_TOKEN_HEADER = "Posit-Connect-User-Session-Token"

# Connect's error codes for the conditions the setup screen explains. They
# are distinct on purpose: an empty marketplace list is a normal answer and
# must not be confused with any of these.
NOT_ENABLED_ERROR = 289
NO_SESSION_TOKEN_ERROR = 290
BAD_SESSION_TOKEN_ERROR = 291

# How long a viewer's plugin set is reused before being re-read. Entitlements
# change in Connect, not here, so this only bounds staleness; it is not a
# correctness boundary.
CACHE_SECONDS = 300


# --------------------------------------------------------------------------
# Setup screen
# --------------------------------------------------------------------------

_SETUP_STYLE = ui.tags.style("""
    .setup-container {
        max-width: 820px;
        margin: 0 auto;
        padding: 2.5rem 1.5rem;
    }
    .setup-title { font-weight: 700; margin-bottom: .5rem; }
    .setup-lede { color: #4a5568; font-size: 1.05rem; margin-bottom: 2rem; }
    .setup-step {
        border-left: 4px solid #447099;
        padding: 0 0 0 1rem;
        margin: 2rem 0 0 0;
    }
    .setup-step h2 { font-size: 1.3rem; font-weight: 600; margin-bottom: .5rem; }
    .setup-step p { color: #4a5568; line-height: 1.6; }
    .setup-code {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 1rem 1.25rem;
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: .875rem;
        margin: 1rem 0;
        overflow-x: auto;
    }
    /* A provider's error arrives as one long line. Wrapping keeps the part
       that says what went wrong on screen. */
    .setup-error-code {
        white-space: pre-wrap;
        word-break: break-word;
        overflow-x: visible;
    }
    .setup-done { color: #1a7f5a; font-weight: 600; }
""")


def _integration_step(n: int) -> ui.Tag:
    return ui.div(
        ui.h2(f"{n}. Add the Agent Plugins integration"),
        ui.p(
            "Agent plugins are off for every piece of content until this "
            "integration is added. Open this content's ",
            ui.strong("Runtime"),
            " tab and add ",
            ui.strong("Agent Plugins"),
            " under ",
            ui.strong("Integrations"),
            ". Connect ships it, so it is already there.",
        ),
        ui.p(
            "Adding it allows every marketplace. Which ones you actually "
            "receive is decided by each marketplace's own access list, under ",
            ui.strong("System"),
            " › ",
            ui.strong("Agent plugins"),
            ". So this app can be enabled here and still show you nothing, if "
            "you are on no marketplace's list.",
        ),
        ui.p(
            "This content also cannot be public. Connect refuses to add a "
            "viewer-scoped integration to content anyone can open, because "
            "there is no viewer to name. Signed-in users, or a specific list "
            "of users and groups, both work.",
        ),
        ui.p(
            ui.a(
                "OAuth integrations documentation",
                href="https://docs.posit.co/connect/user/oauth-integrations/",
                target="_blank",
                rel="noopener",
            )
        ),
        class_="setup-step",
    )


def _llm_step(n: int, error: str = "") -> ui.Tag:
    # A model that is set but rejected needs a different fix from one that
    # was never set, so the heading and the error say which happened rather
    # than both showing the same "configure a provider" instruction.
    rejected = bool(error)
    heading = (
        f"{n}. Fix the LLM provider" if rejected else f"{n}. Configure an LLM provider"
    )
    return ui.div(
        ui.h2(heading),
        ui.div(
            ui.tags.p(
                ui.strong("The configured model did not answer."),
                " Connect asked it once at startup and got this back:",
            ),
            ui.pre(error, class_="setup-code setup-error-code"),
            class_="alert alert-warning",
        )
        if rejected
        else None,
        ui.p(
            "Open this content's ",
            ui.strong("Vars"),
            " tab and set ",
            ui.code("CHATLAS_CHAT_PROVIDER_MODEL"),
            " plus the matching API key. For example, for Anthropic:",
        ),
        ui.pre(
            "CHATLAS_CHAT_PROVIDER_MODEL = anthropic/claude-sonnet-4-5-20250929\n"
            "ANTHROPIC_API_KEY           = <your Anthropic API key>",
            class_="setup-code",
        ),
        ui.p(
            "Other providers follow the same pattern with their own model "
            "string and key (",
            ui.code("OPENAI_API_KEY"),
            ", ",
            ui.code("GOOGLE_API_KEY"),
            ", and so on).",
        ),
        ui.p(
            ui.a(
                "chatlas ChatAuto documentation",
                href="https://posit-dev.github.io/chatlas/reference/ChatAuto.html",
                target="_blank",
                rel="noopener",
            )
        ),
        class_="setup-step",
    )


def _marketplace_step(n: int) -> ui.Tag:
    return ui.div(
        ui.h2(f"{n}. Make sure a marketplace exists"),
        ui.p(
            "An administrator adds agent plugin marketplaces under ",
            ui.strong("System"),
            " › ",
            ui.strong("Agent plugins"),
            ", and controls which users and groups may read each one. Access "
            "is per marketplace rather than per plugin, because the upstream "
            "authorizes whole repositories.",
        ),
        ui.p(
            "This app is told which marketplaces you may read, so it needs no "
            "marketplace names of its own and an administrator is free to "
            "call them anything."
        ),
        ui.p(
            "The upstream can be any git repository carrying a "
            "marketplace.json, including an authenticated Posit Package "
            "Manager plugins repository."
        ),
        class_="setup-step",
    )


def setup_ui(
    need_integration: bool,
    need_llm: bool,
    llm_error: str = "",
    detail: str = "",
) -> ui.Tag:
    """Render only the steps that are still outstanding.

    A partially configured app should not repeat instructions the publisher
    has already followed.
    """
    # Numbered as rendered, not as declared: a screen that skips from 1 to 3
    # reads as a rendering fault rather than a step already done.
    builders = []
    if need_integration:
        builders.append(_integration_step)
    if need_llm:
        builders.append(lambda n: _llm_step(n, llm_error))
    builders.append(_marketplace_step)
    steps = [build(n) for n, build in enumerate(builders, start=1)]

    return ui.page_fixed(
        _SETUP_STYLE,
        ui.div(
            ui.h1("Set up this chat app", class_="setup-title"),
            ui.p(
                "This app gets its skills from a Connect agent plugin "
                "marketplace, filtered to whoever is signed in. Here is what "
                "is still needed before it can do that. The chat opens once "
                "the model answers and a viewer identity resolves.",
                class_="setup-lede",
            ),
            ui.div(detail, class_="alert alert-warning") if detail else None,
            *steps,
            class_="setup-container",
        ),
    )


# --------------------------------------------------------------------------
# Reading the marketplace
# --------------------------------------------------------------------------


def redact(text: str) -> str:
    """Strip credentials out of text before it reaches a log or the UI.

    git puts the remote URL in its error messages, and this app's URLs carry a
    Package Manager token in userinfo. Without this, diagnosing a failed clone
    would mean pasting a working credential into a screenshot.
    """
    return re.sub(r"(https?://)[^@/\s]*@", r"\1<redacted>@", text)


def probe_model() -> tuple[bool, str]:
    """Check that the configured model can actually answer.

    Being configured and being usable are different things, and only the
    second matters to someone about to type a message. chatlas reports a
    missing or rejected credential on the first request rather than when the
    client is built, so the only way to know is to send one.

    The cost is one tiny request per content process, paid at startup instead
    of by whoever sends the first real message and gets an error back.
    """
    if not LLM_CONFIGURED:
        return False, ""
    try:
        chatlas.ChatAuto(system_prompt="Reply with OK.").chat("ping", echo="none")
    except Exception as error:  # noqa: BLE001 - reported on the setup screen
        # An unknown provider name fails here too, at construction, which is
        # worth reporting in the same place as a rejected key.
        detail = redact(f"{type(error).__name__}: {error}")
        print(f"[agent-plugins] the configured model is unusable: {detail}", flush=True)
        return False, detail
    return True, ""


def resolve_marketplaces(
    origin: str, api_key: str, session_token: str
) -> tuple[list[dict], str | None, int | None]:
    """Ask Connect which marketplaces this viewer may read.

    Returns the marketplaces, an error message, and Connect's error code when
    there is one. The code matters: agent plugins not being enabled for this
    content is something an administrator fixes, while a missing viewer
    identity is something about how the app was reached, and both differ from
    the normal answer of an empty list.

    One call carries everything needed -- the viewer's identity, each
    marketplace's upstream URL, and a credential for it -- so the app needs no
    marketplace names of its own and no second request to learn who it is
    acting for.

    The token goes in the body because Connect strips an inbound
    Posit-Connect-User-Session-Token header before any handler sees it, so
    that a caller cannot assert whichever viewer it likes.
    """
    body = json.dumps({"user_session_token": session_token}).encode()
    request = urllib.request.Request(
        f"{origin}/__api__/v1/agent-plugins/credentials", data=body, method="POST"
    )
    request.add_header("Authorization", "Key " + api_key)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        code = None
        message = body[:300]
        try:
            parsed = json.loads(body)
            code = parsed.get("code")
            message = parsed.get("error", message)
        except ValueError:
            pass
        return [], message, code
    except OSError as error:
        return [], f"Could not reach Connect: {error}", None

    return payload, None, None


def authenticated_url(clone_url: str, credential: dict | None) -> str:
    """Put a marketplace's credential into its URL's userinfo.

    Userinfo keeps the credential out of a .netrc the content account shares
    with everything else it runs. It still reaches the process table for the
    duration of the clone, which is acceptable for a demo and is the reason
    the real build-time path writes CONNECT_NETRC_CONTENTS instead.

    A marketplace needing no credential -- a public repository -- is cloned
    with the URL untouched.
    """
    if not credential:
        return clone_url
    parts = urlsplit(clone_url)
    userinfo = "%s:%s" % (
        quote(credential.get("username", ""), safe=""),
        quote(credential.get("password", ""), safe=""),
    )
    return urlunsplit((parts.scheme, f"{userinfo}@{parts.netloc}", parts.path, "", ""))


def run_clone(url: str, destination: Path, shallow: bool):
    """Run one git clone, returning the completed process."""
    command = ["git", "clone", "--quiet"]
    if shallow:
        command += ["--depth", "1"]
    command += [url, str(destination)]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        env={
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(destination.parent),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        },
    )


def clone_marketplace(
    name: str, clone_url: str, credential: dict | None, destination: Path
) -> tuple[list[dict], str | None]:
    """Clone one marketplace and collect the skills it carried.

    Shallow first, since a marketplace's history is of no use here, then a
    full clone if the upstream cannot serve one. Not every git host can: a
    repository served as static files over HTTP has no upload-pack to
    negotiate with, and refuses shallow outright. Marketplaces are ordinary
    git repositories on whatever host their owner chose, so the transport's
    capabilities are not something this app gets to assume.

    Returns the skills found and an error message, if any. The error carries
    git's own stderr, redacted, because otherwise every cause -- an
    unreachable host, a rejected credential, a missing repository -- arrives
    as the same unactionable sentence.
    """
    url = authenticated_url(clone_url, credential)
    try:
        result = run_clone(url, destination, shallow=True)
        if result.returncode != 0 and "shallow" in (result.stderr or ""):
            shutil.rmtree(destination, ignore_errors=True)
            result = run_clone(url, destination, shallow=False)
    except FileNotFoundError:
        return [], "git is not available to this content process."
    except subprocess.TimeoutExpired:
        return [], f"Timed out cloning marketplace {name!r}."

    if result.returncode != 0:
        detail = redact((result.stderr or result.stdout or "").strip())
        return [], (
            f"Could not clone marketplace {name!r} "
            f"(git exit {result.returncode}). {detail}"
        )

    return collect_skills(destination, name), None


# Where a marketplace document may live, in the order clients try them.
DOCUMENT_PATHS = (
    "marketplace.json",
    ".plugin/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    ".cursor-plugin/marketplace.json",
)


def read_document(root: Path) -> list[dict]:
    """Read a clone's marketplace document and return its plugin entries."""
    for candidate in DOCUMENT_PATHS:
        path = root / candidate
        if not path.is_file():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("plugins") or []
        except ValueError:
            return []
    return []


def plugin_root(root: Path, entry: dict) -> Path | None:
    """Resolve where in the clone a marketplace entry's plugin lives.

    The entry's source is a path relative to the repository, and "./" means
    the repository itself -- the layout a repository that is one plugin uses.
    A source that is not a relative path names something outside this clone
    and is skipped rather than guessed at.
    """
    source = entry.get("source")
    if not isinstance(source, str) or "://" in source or source.startswith("/"):
        return None
    candidate = (root / source).resolve() if source else root.resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        # A source climbing out of the clone.
        return None
    return candidate if candidate.is_dir() else None


def collect_skills(root: Path, marketplace: str) -> list[dict]:
    """Read every skill the marketplace's plugins carry.

    Each plugin's location comes from its entry in the marketplace document,
    not from a directory named after it. Nothing normalises the layout on the
    way here, so a repository declaring "./" keeps its skills at the root
    while one listing several plugins nests them.
    """
    skills = []
    for entry in read_document(root):
        name = entry.get("name")
        base = plugin_root(root, entry)
        if not name or base is None:
            continue
        for skill_file in sorted(base.glob("skills/*/SKILL.md")):
            body = skill_file.read_text(encoding="utf-8", errors="replace")
            skills.append(
                {
                    "marketplace": marketplace,
                    "plugin": name,
                    "name": skill_file.parent.name,
                    "description": frontmatter_value(body, "description"),
                    "body": body,
                }
            )
    return skills


def assign_tool_names(skills: list[dict]) -> list[str]:
    """Give every skill a unique name to advertise to the model, and say which
    ones had to be qualified.

    Two marketplaces can carry a plugin of the same name, and one plugin can
    carry a skill whose name another plugin also uses. The model addresses a
    skill by a single string, so those have to be separated before they reach
    it -- otherwise one silently shadows the other and which one wins depends
    on clone order.

    The escalation mirrors what MCP clients do with colliding tool names:
    prefer the short name, qualify only where it is ambiguous, and report that
    it happened rather than resolving it quietly.
    """
    counts: dict[str, int] = {}
    for skill in skills:
        counts[skill["name"]] = counts.get(skill["name"], 0) + 1

    qualified = []
    for skill in skills:
        if counts[skill["name"]] == 1:
            skill["tool_name"] = skill["name"]
            continue
        # plugin:skill is the convention plugin clients already use.
        candidate = f"{skill['plugin']}:{skill['name']}"
        if (
            sum(
                1
                for other in skills
                if f"{other['plugin']}:{other['name']}" == candidate
            )
            > 1
        ):
            # Same plugin name in two marketplaces: only the marketplace
            # separates them.
            candidate = f"{candidate}@{skill['marketplace']}"
        skill["tool_name"] = candidate
        qualified.append(candidate)
    return qualified


def frontmatter_value(body: str, field: str) -> str:
    """Pull one field out of a skill's frontmatter.

    Hand-parsed on purpose: the skill spec's frontmatter is line-oriented and
    a YAML dependency would be the only one this app needs.
    """
    if not body.startswith("---"):
        return ""
    for line in body.splitlines()[1:]:
        if line.strip() == "---":
            break
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""


# How long to wait before re-probing a model that failed.
LLM_RETRY_SECONDS = 60

# The probe result is process state, not per-viewer state: it answers a
# question about the content's configuration, not about who is looking.
_llm_lock = threading.Lock()
_llm_state = {"ok": False, "error": "", "at": 0.0, "probed": False}


def llm_status() -> tuple[bool, str]:
    """Report whether the configured model answers, re-probing on failure.

    A success is final: a model that answered is configured correctly, and
    asking again on every session would spend a request per viewer. A failure
    is provisional -- a rate limit or a momentary network fault would
    otherwise hide the chat until someone restarted the content -- so it is
    retried, at most once per LLM_RETRY_SECONDS.
    """
    with _llm_lock:
        fresh = time.monotonic() - _llm_state["at"] < LLM_RETRY_SECONDS
        if _llm_state["ok"] or (_llm_state["probed"] and fresh):
            return _llm_state["ok"], _llm_state["error"]

        ok, error = probe_model()
        _llm_state.update(ok=ok, error=error, at=time.monotonic(), probed=True)
        return ok, error


WORKDIR = Path(tempfile.mkdtemp(prefix="connect-plugins-"))


@atexit.register
def _cleanup():
    shutil.rmtree(WORKDIR, ignore_errors=True)


class PluginCache:
    """Per-viewer plugin sets, held briefly so a reload does not re-clone.

    One deployment serves every viewer, so this holds one entry per identity
    rather than one for the process. The lock matters: two viewers arriving
    together would otherwise clone into the same directory.
    """

    def __init__(self):
        self._entries: dict[str, dict] = {}
        self._lock = threading.Lock()

    def get(self, username: str, payload: dict) -> dict:
        """Clone every marketplace in a credentials response.

        Takes the response rather than fetching it, because credentials are
        short-lived: the caller requests them per refill, and a cache hit must
        not reuse a token that has since expired.
        """
        with self._lock:
            cached = self._entries.get(username)
            if cached and time.monotonic() - cached["at"] < CACHE_SECONDS:
                return cached

            root = WORKDIR / username
            shutil.rmtree(root, ignore_errors=True)

            marketplaces = payload.get("marketplaces") or []
            # Connect reports a marketplace this viewer may read but could not
            # be let into. Carried through rather than dropped: "Connect
            # cannot get you in" is not "you may read nothing".
            problems = list(payload.get("warnings") or [])

            skills: list[dict] = []
            names = []
            for marketplace in marketplaces:
                name = marketplace.get("name", "?")
                names.append(name)
                found, failure = clone_marketplace(
                    name,
                    marketplace.get("url", ""),
                    marketplace.get("credential"),
                    root / name,
                )
                skills.extend(found)
                if failure:
                    problems.append(failure)

            qualified = assign_tool_names(skills)
            entry = {
                "at": time.monotonic(),
                "marketplaces": sorted(names),
                "skills": skills,
                "by_name": {skill["tool_name"]: skill for skill in skills},
                "qualified": qualified,
                "error": " ".join(problems) if problems else None,
            }
            self._entries[username] = entry
            error = entry["error"]

        # Logged because the sidebar reaches only a viewer who already has the
        # app open, and Shiny delivers it over the websocket rather than in the
        # initial HTML -- so this is otherwise invisible in the logs.
        if error:
            print(f"[agent-plugins] {username}: {error}", flush=True)
        else:
            print(
                "[agent-plugins] %s received %d skill(s) from %s: %s"
                % (
                    username,
                    len(skills),
                    ", ".join(entry["marketplaces"]) or "no marketplaces",
                    ", ".join(entry["by_name"]) or "none",
                ),
                flush=True,
            )
            if qualified:
                print(
                    "[agent-plugins] %s: qualified colliding skill name(s): %s"
                    % (username, ", ".join(sorted(qualified))),
                    flush=True,
                )
        return entry


PLUGINS = PluginCache()


# --------------------------------------------------------------------------
# Chat UI
# --------------------------------------------------------------------------

chat_page = ui.page_sidebar(
    ui.sidebar(
        ui.output_ui("identity_note"),
        ui.hr(),
        ui.h5("Skills from Connect"),
        ui.output_ui("skill_list"),
        ui.output_ui("pin_note"),
        ui.input_checkbox_group("pinned_skills", None, choices={}),
        ui.output_ui("activity"),
        width=360,
    ),
    ui.chat_ui("chat", placeholder="Ask for something one of your skills covers"),
    title="Chat with Connect-managed skills",
)

app_ui = ui.page_output("screen")


def server(input: Inputs, output: Outputs, session: Session):
    has_llm, llm_error = llm_status()
    session_token = session.http_conn.headers.get(SESSION_TOKEN_HEADER)

    # One call resolves everything: who is viewing, which marketplaces they
    # may read, and the credential for each. The content's own key says which
    # content is asking; the session token says who is looking at it.
    viewer_name = None
    resolved = None
    need_integration = False
    detail = ""

    if not session_token:
        # No viewer to scope to, so there is nothing to answer. Falling back to
        # this content's own identity would show every viewer the owner's
        # marketplaces.
        need_integration = True
        detail = (
            "Connect sent no viewer session token for this request. Set this "
            "content's access to signed-in users only."
        )
    elif not CONNECT_API_KEY:
        detail = (
            "No CONNECT_API_KEY. Deploy with Applications.DefaultAPIKeyEnv "
            "enabled so Connect injects one."
        )
    else:
        payload, error, code = resolve_marketplaces(
            CONNECT_SERVER, CONNECT_API_KEY, session_token
        )
        if error:
            # Not being enabled for this content is the case the setup screen
            # exists for. Anything else is reported as-is rather than
            # rewritten into advice that might not apply.
            # Only these two are fixed by the integration step. Any other
            # failure shows the detail alone rather than advice that might
            # send someone to the wrong screen.
            need_integration = code in (NOT_ENABLED_ERROR, NO_SESSION_TOKEN_ERROR)
            if code == BAD_SESSION_TOKEN_ERROR:
                # Reloading mints a fresh token, which is the whole fix.
                detail = error + " Reload the page."
            detail = error
            print(f"[agent-plugins] {error}", flush=True)
        else:
            resolved = payload
            viewer_name = (payload.get("viewer") or {}).get("username")

    entry = (
        PLUGINS.get(viewer_name, resolved)
        if resolved is not None and viewer_name
        else {
            "marketplaces": [],
            "skills": [],
            "by_name": {},
            "qualified": [],
            "error": None,
        }
    )
    skills = entry["skills"]
    by_name = entry["by_name"]

    tool_calls = reactive.value([])
    chat = ui.Chat(id="chat", on_error="actual")

    ui.update_checkbox_group(
        "pinned_skills",
        choices={skill["tool_name"]: skill["tool_name"] for skill in skills},
    )

    @render.ui
    def screen():
        if resolved is None or not has_llm:
            return setup_ui(
                need_integration=need_integration,
                need_llm=not has_llm,
                llm_error=llm_error,
                detail=detail,
            )
        return chat_page

    @render.ui
    def identity_note():
        return ui.div(
            ui.tags.p(
                "Signed in as ",
                ui.strong(viewer_name or "unknown"),
                ".",
            ),
            ui.tags.small(
                "Connect exchanged your session token for a key carrying your "
                "identity and filtered the marketplace with it. A plugin you "
                "are not granted was never sent to this app."
            ),
        )

    @render.ui
    def skill_list():
        if entry["error"]:
            return ui.div(entry["error"], class_="text-warning")
        if not skills:
            return ui.div(
                ui.tags.p(
                    "No plugins are granted to you in "
                    + (", ".join(entry["marketplaces"]) or "any marketplace")
                    + "."
                ),
                ui.tags.small(
                    "An administrator grants access per marketplace and per "
                    "plugin under System › Agent plugins."
                ),
            )
        # Grouped by marketplace so provenance is visible: with more than one
        # in play, "where did this skill come from" is the first question.
        groups = []
        for marketplace in entry["marketplaces"]:
            mine = [s for s in skills if s["marketplace"] == marketplace]
            if not mine:
                continue
            groups.append(
                ui.div(
                    ui.tags.small(ui.strong(marketplace), class_="text-muted"),
                    ui.tags.ul(
                        *[
                            ui.tags.li(
                                ui.tags.code(skill["tool_name"]),
                                f" — {skill['description']}",
                                ui.tags.span(
                                    f" ({skill['plugin']})", class_="text-muted"
                                ),
                            )
                            for skill in mine
                        ]
                    ),
                )
            )
        if entry["qualified"]:
            groups.append(
                ui.tags.small(
                    "Some skill names appear in more than one place, so they "
                    "are qualified above to keep them distinct.",
                    class_="text-warning",
                )
            )
        return ui.div(*groups)

    @render.ui
    def pin_note():
        if not skills:
            return ui.div()
        return ui.div(
            ui.hr(),
            ui.h5("Pin into the system prompt"),
            ui.tags.small(
                "Every skill above reaches the model three ways: as a tool "
                "the assistant calls on its own, as a slash command you can "
                "invoke yourself, and pinned here to hold it in force for "
                "the whole conversation."
            ),
        )

    @render.ui
    def activity():
        calls = tool_calls.get()
        if not calls:
            return ui.div()
        return ui.div(
            ui.hr(),
            ui.h5("Skills the assistant loaded"),
            ui.tags.ul(*[ui.tags.li(ui.tags.code(name)) for name in calls]),
        )

    def system_prompt() -> str:
        available = ", ".join(by_name) or "none"
        prompt = [
            "You are a helpful, concise assistant running on Posit Connect.",
            f"Skills available through the load_skill tool: {available}.",
            "Call load_skill when a request matches a skill's purpose, then "
            "follow the instructions it returns. Say which skill you used.",
        ]
        for name in input.pinned_skills() or ():
            skill = by_name.get(name)
            if skill:
                prompt.append(
                    f"The following skill is always in force:\n\n{skill['body']}"
                )
        return "\n\n".join(prompt)

    @reactive.calc
    def client():
        # Rebuilt when the pinned set changes: a skill pinned into the system
        # prompt applies for the rest of the conversation, so changing the set
        # starts a new one.
        chat_client = chatlas.ChatAuto(system_prompt=system_prompt())

        def load_skill(skill: str) -> str:
            """Load a skill's instructions into the conversation.

            Args:
                skill: The name of the skill to load.
            """
            found = by_name.get(skill)
            if not found:
                return (
                    f"No skill named {skill!r}. "
                    f"Available: {', '.join(by_name) or 'none'}."
                )
            with reactive.isolate():
                tool_calls.set([*tool_calls.get(), skill])
            return found["body"]

        if skills:
            chat_client.register_tool(load_skill)
        return chat_client

    def register_slash_commands():
        """Offer every skill this viewer received as a slash command.

        The model can already reach a skill through the load_skill tool. A
        command is the other direction: the person chooses the skill, which is
        what you want when you know which one applies and would rather not
        hope the model agrees.

        Command names take only letters, digits, hyphens and underscores, so a
        qualified skill name like `quarto:brand-yml@internal` has to be
        rewritten. The description keeps the real name so the palette still
        says which skill it is.
        """
        for skill in skills:
            name = re.sub(r"[^A-Za-z0-9_-]+", "-", skill["tool_name"]).strip("-")
            if not name:
                continue
            description = skill["description"] or f"Use the {skill['name']} skill"
            if skill["tool_name"] != name:
                description = f"{description} ({skill['tool_name']})"

            chat.slash_command(name, description[:120], make_handler(skill), force=True)

    def make_handler(skill: dict):
        """Bind one skill to a command handler.

        A factory rather than a default argument: shinychat counts a
        handler's parameters to decide whether it takes the text after the
        command, and a bound default would read as a second parameter.
        """

        async def handler(user_input: str = ""):
            await run_with_skill(skill, user_input)

        return handler

    async def run_with_skill(skill: dict, user_input: str):
        """Answer with one skill's instructions in force for this turn."""
        with reactive.isolate():
            tool_calls.set([*tool_calls.get(), skill["tool_name"]])
        prompt = (
            f"Follow these instructions for this request.\n\n{skill['body']}\n\n"
            f"Request: {user_input or '(no request given -- summarize what this skill does)'}"
        )
        response = await client().stream_async(prompt)
        await chat.append_message_stream(response)

    # Registered after the first flush, not during setup. The chat widget is
    # rendered by a dynamic output -- the setup screen swaps the whole page --
    # so it is not in the DOM yet while the server function runs, and the
    # command list would be sent to an element that does not exist and
    # silently dropped.
    session.on_flushed(register_slash_commands, once=True)

    @chat.on_user_submit
    async def handle(user_input: str):
        response = await client().stream_async(user_input)
        await chat.append_message_stream(response)


app = App(app_ui, server)
