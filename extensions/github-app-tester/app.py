# GitHub App Integration Tester
# A Shiny for Python app to test GitHub App (service account) integration on Posit Connect

import os
from datetime import datetime

import requests
from shiny import App, reactive, render, ui


# --- GitHub API helpers ---


def github_api_request(token: str, endpoint: str, params: dict = None) -> dict:
    """Make a request to the GitHub API."""
    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        return {
            "status_code": resp.status_code,
            "data": resp.json() if resp.text else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_token_metadata(token: str) -> dict:
    """Get metadata about the installation token including repos."""
    result = {
        "repositories": [],
        "rate_limit": {},
    }

    # Get rate limit info
    rate_resp = github_api_request(token, "/rate_limit")
    if "error" not in rate_resp and rate_resp.get("status_code") == 200:
        result["rate_limit"] = rate_resp.get("data", {})

    # Get accessible repositories
    repos_resp = github_api_request(
        token, "/installation/repositories", {"per_page": 100}
    )
    if "error" not in repos_resp:
        result["repositories_response"] = repos_resp
        if repos_resp.get("status_code") == 200:
            data = repos_resp.get("data", {})
            result["repositories"] = data.get("repositories", [])
            result["total_count"] = data.get("total_count", 0)

    return result


# --- UI Definition ---

app_ui = ui.page_fluid(
    ui.h2("GitHub App Integration Tester"),
    ui.output_ui("status_panel"),
    ui.card(
        ui.card_header("Content Session Token"),
        ui.output_ui("content_session_token_display"),
    ),
    ui.hr(),
    ui.row(
        ui.column(
            6,
            ui.card(
                ui.card_header("Token Information"),
                ui.output_ui("token_info"),
            ),
        ),
        ui.column(
            6,
            ui.card(
                ui.card_header("Rate Limit"),
                ui.output_ui("rate_limit_info"),
            ),
        ),
    ),
    ui.card(
        ui.card_header("Repository Browser"),
        ui.row(
            ui.column(
                4,
                ui.output_ui("repo_selector"),
            ),
            ui.column(
                8,
                ui.navset_tab(
                    ui.nav_panel("Issues", ui.output_ui("issues_panel")),
                    ui.nav_panel("Pull Requests", ui.output_ui("prs_panel")),
                    ui.nav_panel("Contents", ui.output_ui("contents_panel")),
                ),
            ),
        ),
    ),
    ui.tags.details(
        ui.tags.summary("Raw API Response"),
        ui.output_code("raw_response"),
        class_="mt-3",
    ),
)


# --- Server Logic ---


def server(input, output, session):
    # Reactive values for the connection state
    connection_state = reactive.Value({"status": "loading"})

    # Auto-connect on startup
    @reactive.effect
    def _auto_connect():
        if connection_state.get()["status"] != "loading":
            return

        # Check if running on Connect
        if os.getenv("POSIT_PRODUCT") != "CONNECT":
            connection_state.set(
                {
                    "status": "error",
                    "error": "This app must run on Posit Connect to use OAuth integrations.",
                }
            )
            return

        content_session_token_file = os.getenv("CONNECT_CONTENT_SESSION_TOKEN_FILE")
        if content_session_token_file:
            with open(content_session_token_file, "r") as f:
                content_session_token = f.read().strip()
        else:
            content_session_token = os.getenv("CONNECT_CONTENT_SESSION_TOKEN")
        if not content_session_token:
            connection_state.set(
                {
                    "status": "error",
                    "error": "CONNECT_CONTENT_SESSION_TOKEN not available. Make sure a GitHub App integration is associated with this content.",
                }
            )
            return

        # Use posit-sdk to get credentials
        try:
            from posit import connect

            client = connect.Client()
            credentials = client.oauth.get_content_credentials(content_session_token)
            access_token = credentials.get("access_token")

            if not access_token:
                connection_state.set(
                    {
                        "status": "error",
                        "error": f"No access_token in credentials response: {credentials}",
                    }
                )
                return

            # Get GitHub metadata
            metadata = get_token_metadata(access_token)

            connection_state.set(
                {
                    "status": "connected",
                    "credentials": credentials,
                    "metadata": metadata,
                }
            )

        except Exception as e:
            connection_state.set(
                {
                    "status": "error",
                    "error": f"Failed to get credentials: {str(e)}",
                }
            )

    @output
    @render.ui
    def content_session_token_display():
        """Read the content session token fresh on each render (not cached)."""
        content_session_token_file = "../job/.connect/session-token"
        try:
            with open(content_session_token_file, "r") as f:
                content_session_token = f.read().strip()
            return ui.div(
                ui.tags.code(content_session_token, style="word-break: break-all;"),
                ui.p(
                    f"Read from: {content_session_token_file}",
                    class_="text-muted mt-2",
                ),
            )
        except FileNotFoundError:
            return ui.p(
                f"Token file not found: {content_session_token_file}",
                class_="text-warning",
            )
        except Exception as e:
            return ui.p(f"Error reading token: {e}", class_="text-danger")

    @output
    @render.ui
    def status_panel():
        state = connection_state.get()
        status = state.get("status", "loading")

        if status == "loading":
            return ui.div(
                ui.p("Connecting to GitHub App integration...", class_="text-muted"),
                class_="alert alert-info",
            )

        if status == "error":
            return ui.div(
                ui.strong("Error: "),
                state.get("error", "Unknown error"),
                class_="alert alert-danger",
            )

        # Connected
        creds = state.get("credentials", {})
        token_type = creds.get("issued_token_type", "unknown")

        return ui.div(
            ui.strong("Connected! "),
            f"Token type: {token_type}",
            class_="alert alert-success",
        )

    @output
    @render.ui
    def token_info():
        state = connection_state.get()
        if state.get("status") != "connected":
            return ui.p("Not connected", class_="text-muted")

        creds = state.get("credentials", {})
        token = creds.get("access_token", "")
        token_type = creds.get("token_type", "unknown")

        # Mask the token for display
        masked_token = f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "****"

        return ui.tags.dl(
            ui.tags.dt("Token Type"),
            ui.tags.dd(token_type),
            ui.tags.dt("Access Token"),
            ui.tags.dd(ui.code(masked_token)),
            ui.tags.dt("Token Prefix"),
            ui.tags.dd(
                ui.code(token[:4]) if token else "N/A",
                " ",
                ui.span(
                    (
                        "(ghs_ = GitHub App installation token)"
                        if token.startswith("ghs_")
                        else ""
                    ),
                    class_="text-muted",
                ),
            ),
        )

    @output
    @render.ui
    def rate_limit_info():
        state = connection_state.get()
        if state.get("status") != "connected":
            return ui.p("Not connected", class_="text-muted")

        meta = state.get("metadata", {})
        rate = meta.get("rate_limit", {}).get("resources", {}).get("core", {})
        if not rate:
            return ui.p("Rate limit info not available", class_="text-muted")

        remaining = rate.get("remaining", 0)
        limit = rate.get("limit", 0)
        reset_ts = rate.get("reset", 0)
        reset_time = (
            datetime.fromtimestamp(reset_ts).strftime("%H:%M:%S") if reset_ts else "N/A"
        )

        pct = (remaining / limit * 100) if limit > 0 else 0
        bar_class = (
            "bg-success" if pct > 50 else "bg-warning" if pct > 20 else "bg-danger"
        )

        return ui.div(
            ui.p(f"{remaining} / {limit} requests remaining"),
            ui.div(
                ui.div(
                    style=f"width: {pct}%",
                    class_=f"progress-bar {bar_class}",
                ),
                class_="progress",
            ),
            ui.p(f"Resets at: {reset_time}", class_="text-muted mt-2"),
        )

    @output
    @render.ui
    def repo_selector():
        state = connection_state.get()
        if state.get("status") != "connected":
            return ui.p("Not connected", class_="text-muted")

        meta = state.get("metadata", {})
        repos = meta.get("repositories", [])

        if not repos:
            return ui.p("No repositories accessible", class_="text-warning")

        choices = {repo["full_name"]: repo["full_name"] for repo in repos}

        return ui.div(
            ui.input_select("selected_repo", "Select Repository", choices=choices),
            ui.p(f"{len(repos)} repositories accessible", class_="text-muted mt-2"),
        )

    @reactive.Calc
    def get_access_token():
        state = connection_state.get()
        if state.get("status") != "connected":
            return None
        return state.get("credentials", {}).get("access_token")

    @output
    @render.ui
    def issues_panel():
        token = get_access_token()
        if not token:
            return ui.p("Not connected", class_="text-muted")

        try:
            repo = input.selected_repo()
        except Exception:
            return ui.p("Select a repository", class_="text-muted")

        if not repo:
            return ui.p("Select a repository", class_="text-muted")

        # Fetch issues
        resp = github_api_request(
            token,
            f"/repos/{repo}/issues",
            {"state": "open", "per_page": 20, "sort": "updated"},
        )

        if "error" in resp:
            return ui.div(
                ui.p(f"Error: {resp['error']}", class_="text-danger"),
            )

        if resp.get("status_code") != 200:
            return ui.div(
                ui.p(
                    ui.strong(f"GitHub API Error ({resp.get('status_code')})"),
                    class_="text-danger",
                ),
                ui.pre(str(resp.get("data", {}))),
                ui.p(
                    "This may indicate the token doesn't have 'issues:read' permission.",
                    class_="text-muted",
                ),
            )

        issues = resp.get("data", [])
        # Filter out PRs (GitHub returns PRs in issues endpoint)
        issues = [i for i in issues if "pull_request" not in i]

        if not issues:
            return ui.p(
                "No open issues found (token has issues:read access)",
                class_="text-success",
            )

        items = []
        for issue in issues:
            items.append(
                ui.tags.li(
                    ui.a(
                        f"#{issue.get('number')} {issue.get('title', 'No title')}",
                        href=issue.get("html_url", "#"),
                        target="_blank",
                    ),
                    ui.br(),
                    ui.tags.small(
                        f"by {issue.get('user', {}).get('login', 'unknown')} | {issue.get('comments', 0)} comments",
                        class_="text-muted",
                    ),
                    class_="list-group-item",
                )
            )

        return ui.div(
            ui.p("Token has issues:read access", class_="text-success"),
            ui.tags.ul(*items, class_="list-group"),
        )

    @output
    @render.ui
    def prs_panel():
        token = get_access_token()
        if not token:
            return ui.p("Not connected", class_="text-muted")

        try:
            repo = input.selected_repo()
        except Exception:
            return ui.p("Select a repository", class_="text-muted")

        if not repo:
            return ui.p("Select a repository", class_="text-muted")

        # Fetch PRs
        resp = github_api_request(
            token,
            f"/repos/{repo}/pulls",
            {"state": "open", "per_page": 20, "sort": "updated"},
        )

        if "error" in resp:
            return ui.div(
                ui.p(f"Error: {resp['error']}", class_="text-danger"),
            )

        if resp.get("status_code") != 200:
            return ui.div(
                ui.p(
                    ui.strong(f"GitHub API Error ({resp.get('status_code')})"),
                    class_="text-danger",
                ),
                ui.pre(str(resp.get("data", {}))),
                ui.p(
                    "This may indicate the token doesn't have 'pull_requests:read' permission.",
                    class_="text-muted",
                ),
            )

        prs = resp.get("data", [])

        if not prs:
            return ui.p(
                "No open pull requests found (token has pull_requests:read access)",
                class_="text-success",
            )

        items = []
        for pr in prs:
            items.append(
                ui.tags.li(
                    ui.a(
                        f"#{pr.get('number')} {pr.get('title', 'No title')}",
                        href=pr.get("html_url", "#"),
                        target="_blank",
                    ),
                    " ",
                    ui.span(
                        "Draft" if pr.get("draft") else "Open",
                        class_=(
                            "badge bg-secondary"
                            if pr.get("draft")
                            else "badge bg-success"
                        ),
                    ),
                    ui.br(),
                    ui.tags.small(
                        f"by {pr.get('user', {}).get('login', 'unknown')} | {pr.get('head', {}).get('ref', '?')} -> {pr.get('base', {}).get('ref', '?')}",
                        class_="text-muted",
                    ),
                    class_="list-group-item",
                )
            )

        return ui.div(
            ui.p("Token has pull_requests:read access", class_="text-success"),
            ui.tags.ul(*items, class_="list-group"),
        )

    @output
    @render.ui
    def contents_panel():
        token = get_access_token()
        if not token:
            return ui.p("Not connected", class_="text-muted")

        try:
            repo = input.selected_repo()
        except Exception:
            return ui.p("Select a repository", class_="text-muted")

        if not repo:
            return ui.p("Select a repository", class_="text-muted")

        # Fetch root contents
        resp = github_api_request(token, f"/repos/{repo}/contents")

        if "error" in resp:
            return ui.div(
                ui.p(f"Error: {resp['error']}", class_="text-danger"),
            )

        if resp.get("status_code") != 200:
            return ui.div(
                ui.p(
                    ui.strong(f"GitHub API Error ({resp.get('status_code')})"),
                    class_="text-danger",
                ),
                ui.pre(str(resp.get("data", {}))),
                ui.p(
                    "This may indicate the token doesn't have 'contents:read' permission.",
                    class_="text-muted",
                ),
            )

        contents = resp.get("data", [])

        if not contents:
            return ui.p(
                "Repository is empty (token has contents:read access)",
                class_="text-success",
            )

        items = []
        for item in sorted(
            contents, key=lambda x: (x.get("type") != "dir", x.get("name", ""))
        ):
            icon = "📁 " if item.get("type") == "dir" else "📄 "
            items.append(
                ui.tags.li(
                    icon,
                    ui.a(
                        item.get("name", "unknown"),
                        href=item.get("html_url", "#"),
                        target="_blank",
                    ),
                    class_="list-group-item",
                )
            )

        return ui.div(
            ui.p("Token has contents:read access", class_="text-success"),
            ui.tags.ul(*items, class_="list-group"),
        )

    @output
    @render.code
    def raw_response():
        import json

        state = connection_state.get()
        result = dict(state)

        # Mask the token in the output
        if "credentials" in result and result["credentials"]:
            creds = dict(result["credentials"])
            if "access_token" in creds:
                token = creds["access_token"]
                creds["access_token"] = (
                    f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "****"
                )
            result["credentials"] = creds

        return json.dumps(result, indent=2, default=str)


app = App(app_ui, server)
