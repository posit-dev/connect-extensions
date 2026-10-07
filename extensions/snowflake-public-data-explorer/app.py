import asyncio
import logging
import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

import ibis
import snowflake.connector
from chatlas import ChatSnowflake
from posit.connect.external.snowflake import PositAuthenticator
from querychat import QueryChat
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from shinychat import chat_drawer
from shinychat.types import HistoryOptions
from snowflake.connector.config_manager import CONFIG_MANAGER
from snowflake.snowpark import Session as SnowparkSession

# The Snowflake free public data listing by default.
DATABASE = os.getenv("SNOWFLAKE_DATABASE") or "SNOWFLAKE_PUBLIC_DATA_FREE"
SCHEMA = os.getenv("SNOWFLAKE_SCHEMA") or "PUBLIC_DATA_FREE"
TITLE = os.getenv("APP_TITLE") or "Snowflake Public Data Explorer"

# Haiku 4.5 by default; model availability varies by account and region.
MODEL = os.getenv("SNOWFLAKE_CORTEX_MODEL") or "claude-haiku-4-5"

# Warehouse override, when set.
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")

STYLES = Path(__file__).parent / "css" / "styles.css"

# Basic QueryChat configuration.
QUERYCHAT_ID = "querychat"
TOOLS = ("filter", "query", "visualize")

# Rows fetched for the grid, small enough to read.
MAX_ROWS = 100
MAX_TABLES = 5

# Nothing in `shiny run`, uvicorn or Connect configures a handler for an
# app-defined logger, and the root logger defaults to WARNING, so INFO records
# are dropped silently. Configure it here instead of relying on the host.
logger = logging.getLogger("snowflake-llm-dashboard")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

# Rows the `query` tool may hand back to the *model*; unrelated to MAX_ROWS.
# querychat sends it every row it fetched (`tools.py` `_query_impl`), as named
# dicts costing ~57 tokens each, so one 5000-row result is ~285k tokens and
# exceeds this model's 200k window on its own. Results also accumulate across
# turns. Fifty rows cost ~3k and characterise a result as well as more would.
MAX_TOOL_ROWS = 50

# If the schema has Semantic Views, querychat puts every one's full DDL into the
# system prompt regardless of what was selected. They are also the only declared
# table relationships available, so leave them on unless they crowd the prompt.
SEMANTIC_VIEWS = True
if not SEMANTIC_VIEWS:
    os.environ["QUERYCHAT_DISABLE_SEMANTIC_VIEWS"] = "1"

# querychat requires every table name to be a plain SQL identifier.
IDENTIFIER = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")

# querychat overwrites the client's system prompt with its own rendered
# template, so anything passed to ChatSnowflake(system_prompt=...) is discarded.
# extra_instructions is the supported channel: querychat interpolates it into
# that template.
EXTRA_INSTRUCTIONS = f"""
The tables were chosen by the user and may be unrelated, so check the schema
before joining them, and say so when a question cannot be answered from the
data at hand.

These tables run to millions of rows and the token budget is finite, so answer
with aggregates:

- Prefer SQL returning a summary — counts, averages, a grouped breakdown, a
  top-N — over SQL returning detail rows.
- When you do need example rows, add a small `LIMIT`.
- Row-level results are truncated to {MAX_TOOL_ROWS} rows before you see them,
  so a larger query costs budget without telling you more.
"""

# With no `greeting=`, querychat renders this template against the selected
# tables and has the LLM write the opener. The tables are chosen at runtime, so
# a hand-written greeting is not possible.
GREETING_PROMPT = """
You are a friendly data assistant. Someone has just chosen a set of tables to
explore and does not yet know what is in them.

You have access to a {{db_type}} database with the following tables:

<tables>
{{{tables_overview}}}
</tables>

{{#data_description}}
<data_description>
{{{data_description}}}
</data_description>

{{/data_description}}
Write a short welcome covering, in order:

1. One sentence per table: what it holds, and its size if known.
{{#multi_table}}
2. How the tables appear to relate, based on columns they share. No foreign
   keys are declared, so say that this is inferred and unverified. Say plainly
   when they look unrelated.
{{/multi_table}}
3. Anything a newcomer would trip over: a row grain the table name does not
   suggest, or a figure that must be computed rather than read.

Do not list every column. Then offer suggestions.

Suggestions are clickable when wrapped in `<span class="suggestion">`. Give
2-4, grouped under `#####` headings, in explicit `<ul>`/`<li>` lists rather
than markdown list markers, which break silently. Write each as a complete
prompt, and include one that helps the user work out what can be asked.

<ul>
<li><span class="suggestion">What columns does … have?</span></li>
</ul>
"""


class SnowflakeIntegrationError(RuntimeError):
    """Raised when Connect has not been set up with a Snowflake OAuth integration."""


def credentials(session):
    """Snowflake connection parameters for the current viewer.

    On Connect, the viewer's session token is exchanged for a Snowflake OAuth
    token, so every query runs as the person looking at the dashboard. In
    Workbench, the managed credentials in connections.toml are used instead.
    """
    params = {"warehouse": WAREHOUSE} if WAREHOUSE else {}

    if os.getenv("RSTUDIO_PRODUCT") == "CONNECT":
        token = session.http_conn.headers.get("Posit-Connect-User-Session-Token")
        if token is None:
            raise SnowflakeIntegrationError(
                "This content is deployed to Posit Connect, but no Snowflake OAuth integration is attached to it."
            )
        account = os.getenv("SNOWFLAKE_ACCOUNT")
        if account is None:
            raise SnowflakeIntegrationError("The SNOWFLAKE_ACCOUNT environment variable is not set on this content.")

        auth = PositAuthenticator(
            local_authenticator="EXTERNALBROWSER",
            user_session_token=token,
        )
        return params | {
            "account": account,
            "authenticator": auth.authenticator,
            "token": auth.token,
        }

    # Resolved here because the connector only reads default_connection_name
    # when connect() is given no other arguments, and we pass a database and
    # schema. Honours config.toml and SNOWFLAKE_DEFAULT_CONNECTION_NAME.
    return params | {"connection_name": CONFIG_MANAGER["default_connection_name"]}


def connect(creds):
    """A raw connection and a lazy Ibis backend over it, for one viewer."""
    con = snowflake.connector.connect(
        database=DATABASE,
        schema=SCHEMA,
        validate_default_parameters=True,
        **creds,
    )
    return con, ibis.snowflake.from_connection(con, create_object_udfs=False)


def snowpark_session(con):
    """A Snowpark session wrapping one viewer's raw Snowflake connection."""
    return SnowparkSession.builder.configs({"connection": con}).create()


def get_chat(sp_session):
    """A Cortex chat client for one viewer, using its Snowpark session.

    Passing `sp_session` makes chatlas treat it as caller-owned, so
    `Chat.close()` leaves it open for `sp_session.close()` to close instead.
    """
    return ChatSnowflake(model=MODEL, session=sp_session)


def list_available(ibiscon):
    """Selectable table names in the schema."""
    return sorted(name for name in ibiscon.list_tables() if IDENTIFIER.match(name))


def table_metadata(con):
    """Name, comment, row count and size for every table in the schema.

    INFORMATION_SCHEMA is metadata, so this scans nothing. Public data arrives
    as a share, which may leave any of these columns null or refuse the query
    outright, so this is best effort: callers render whatever came back.
    """
    query = (
        "SELECT TABLE_NAME, COMMENT, ROW_COUNT, BYTES "
        f"FROM {DATABASE}.INFORMATION_SCHEMA.TABLES "
        f"WHERE TABLE_SCHEMA = '{SCHEMA}'"
    )
    try:
        with con.cursor() as cur:
            cur.execute(query)
            return {row[0]: {"comment": row[1], "rows": row[2], "bytes": row[3]} for row in cur}
    except snowflake.connector.Error:
        logger.info("table metadata unavailable", exc_info=True)
        return {}


def human_rows(meta, name):
    """Row count as "28.4M rows", or None if the share did not report one."""
    count = meta.get(name, {}).get("rows")
    if count is None:
        return None
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if count >= limit:
            return f"{count / limit:.1f}{suffix} rows"
    return f"{count} rows"


def comment_of(meta, name):
    """
    A table's description as one line. COMMENT holds multi-line paragraphs
    and callers want it collapsed.
    """
    return " ".join((meta.get(name, {}).get("comment") or "").split())


def describe(names, meta):
    """Context about the selected tables, for the LLM.

    States only what the metadata says. Relationships are left to the greeting,
    which can read the schemas and hedge.
    """
    lines = []
    for name in names:
        detail = " · ".join(part for part in (comment_of(meta, name), human_rows(meta, name)) if part)
        lines.append(f"- {name}: {detail}" if detail else f"- {name}")

    return (
        f"The user chose these tables from {DATABASE}.{SCHEMA}:\n\n"
        + "\n".join(lines)
        + "\n\nNo relationships between them are declared. Any join has to be "
        "inferred from the column names in the schema above."
    )


def cap_query_tool(client, max_rows=MAX_TOOL_ROWS):
    """Bound the rows querychat's `query` tool hands the model.

    Only the model's copy is capped; the displayed result is untouched. Wraps
    the Tool's `func` in place, since its name and JSON schema live on the
    object and rebuilding them is fragile.
    """
    tool = next((t for t in client.get_tools() if t.name == "querychat_query"), None)
    if tool is None or getattr(tool, "func", None) is None:
        logger.warning("querychat_query tool not found; results are not capped")
        return
    inner = tool.func

    def capped(*args, **kwargs):
        result = inner(*args, **kwargs)
        rows = getattr(result, "value", None)
        if isinstance(rows, list) and len(rows) > max_rows:
            omitted = len(rows) - max_rows
            logger.info("capped querychat_query result: %d rows dropped", omitted)
            result.value = {
                "rows": rows[:max_rows],
                "note": (
                    f"Showing {max_rows} of {len(rows)} rows; {omitted} were "
                    "omitted to stay inside the token budget. Aggregate in SQL "
                    "if you need to characterise the whole result."
                ),
            }
        return result

    tool.func = capped


def read_params(session):
    """The page's query string, as a dict.

    Not `session.http_conn.query_params`: that is the websocket request, opened
    against /websocket/ with no query string, so it is always empty. The page
    URL arrives as clientdata, which Shiny populates before calling `server`.
    """
    with reactive.isolate():
        search = session.clientdata.url_search()
    return dict(parse_qsl(search.lstrip("?")))


def selected_tables(params):
    """Table names from ?tables=A,B,C — deduplicated, valid, and capped."""
    raw = params.get("tables", "")
    names = [name.strip().upper() for name in raw.split(",") if name.strip()]
    unique = list(dict.fromkeys(names))
    return [name for name in unique if IDENTIFIER.match(name)][:MAX_TABLES]


def integration_error_card(message):
    """An alert explaining a missing Snowflake integration, with fix-it links."""
    return ui.div(
        ui.h5("Snowflake integration required", class_="alert-heading"),
        ui.p(message),
        ui.tags.ul(
            ui.tags.li(
                "If this Connect server does not yet include a Snowflake integration, ",
                "an administrator needs to create one in Snowflake, then configure Connect to use it. ",
                "Follow the instructions found in the ",
                ui.a(
                    "Connect Admin Guide",
                    href="https://docs.posit.co/connect/admin/integrations/oauth-integrations/snowflake/",
                    target="_blank",
                ),
                ".",
            ),
            ui.tags.li(
                "Once Connect has a configured Snowflake integration, ",
                "this content needs the integration to be attached. ",
                "Follow the guidance in the ",
                ui.a(
                    "Connect User Guide",
                    href="https://docs.posit.co/connect/user/oauth-integrations/#adding-integrations-to-deployed-content",
                    target="_blank",
                ),
                ".",
            ),
        ),
        class_="alert alert-danger my-3",
        role="alert",
    )


def connection_error_card(message):
    """An alert for a Snowflake connection failure, with the raw error."""
    using_default = os.getenv("SNOWFLAKE_DATABASE") is None and os.getenv("SNOWFLAKE_SCHEMA") is None
    items = []
    if using_default:
        items.append(
            ui.tags.li(
                ui.code(f"{DATABASE}.{SCHEMA}"),
                " is the default: the free public-data listing from the "
                "Snowflake Marketplace. If it is not installed on this "
                "account, an administrator can add it from the Marketplace, "
                "or set ",
                ui.code("SNOWFLAKE_DATABASE"),
                " and ",
                ui.code("SNOWFLAKE_SCHEMA"),
                " on this content to point at a different database and schema.",
            )
        )
    else:
        items.append(
            ui.tags.li(
                "Confirm ",
                ui.code("SNOWFLAKE_DATABASE"),
                f" (currently {DATABASE!r}) and ",
                ui.code("SNOWFLAKE_SCHEMA"),
                f" (currently {SCHEMA!r}) name a database and schema that exist in this account.",
            )
        )
    if WAREHOUSE:
        items.append(
            ui.tags.li(
                ui.code("SNOWFLAKE_WAREHOUSE"),
                f" is set to {WAREHOUSE!r}; confirm that warehouse exists.",
            )
        )
    items.append(
        ui.tags.li("Confirm the role used by this connection is granted USAGE on that database, schema, and warehouse.")
    )
    return ui.div(
        ui.h5("Could not connect to Snowflake", class_="alert-heading"),
        ui.p(message),
        ui.tags.ul(*items),
        class_="alert alert-danger my-3",
        role="alert",
    )


def setup_ui():
    return ui.page_fillable(
        ui.head_content(ui.include_css(STYLES)),
        ui.div(
            ui.h2(TITLE, class_="mb-3"),
            ui.p(
                f"Pick up to {MAX_TABLES} tables from ",
                ui.code(f"{DATABASE}.{SCHEMA}"),
                ", then ask questions about them in plain language.",
            ),
            # Every panel below waits on the same catalog load, so let the
            # progress notification be the only indicator rather than
            # showing four spinners.
            ui.busy_indicators.use(spinners=False),
            ui.output_ui("search"),
            ui.output_ui("picker"),
            ui.output_ui("start"),
            ui.output_ui("chosen"),
            class_="container py-4",
            style="max-width: 52rem;",
        ),
        title=TITLE,
    )


def setup_server(input: Inputs, session: Session):
    catalog = reactive.value(None)

    @reactive.effect
    async def _load():
        try:
            # async keeps the event loop free to deliver progress messages.
            with ui.Progress() as progress:
                progress.set(message="Loading credentials")
                creds = credentials(session)

                progress.set(message="Connecting to Snowflake")
                con, ibiscon = await asyncio.to_thread(connect, creds)
                session.on_ended(con.close)

                progress.set(message="Listing tables")
                available = await asyncio.to_thread(list_available, ibiscon)

                progress.set(message="Reading table descriptions")
                meta = await asyncio.to_thread(table_metadata, con)

                catalog.set((available, meta))
        except SnowflakeIntegrationError as e:
            ui.notification_show(integration_error_card(str(e)), type="error", duration=None)
        except snowflake.connector.Error as e:
            ui.notification_show(connection_error_card(str(e)), type="error", duration=None)

    def loaded():
        available, meta = req(catalog())
        return available, meta

    # The checkbox group only reports table names matching the current filter.
    # This tracks the checked items regardless of the current filter.
    picked = reactive.value(frozenset())

    @reactive.calc
    def filter_matches():
        """
        Names matching the filter, currently available to the checkbox
        group (picker).
        """

        available, meta = loaded()
        needle = (input.filter() or "").strip().lower()
        if not needle:
            return available
        return [name for name in available if needle in name.lower() or needle in comment_of(meta, name).lower()]

    @reactive.effect
    @reactive.event(input.tables)
    def _remember():
        """
        Update the (unfiltered) picked set based on the filtered set of
        table names and the checked items (input.tables) within that set.
        """
        picked.set((picked() - set(filter_matches())) | set(input.tables() or ()))

    @render.ui
    def search():
        available, _ = loaded()
        return ui.input_text(
            "filter",
            None,
            placeholder=f"Filter {len(available)} tables by name or description…",
            width="100%",
        )

    @render.ui
    def picker():
        """
        Renders a checkbox group containing every table matching the
        current search filter.

        The full table description is emitted, but CSS rules allow at most two
        lines to appear.
        """
        _, meta = loaded()
        names = filter_matches()
        if not names:
            return ui.p("No tables match that filter.", class_="text-muted my-3")
        with reactive.isolate():
            selected = [name for name in names if name in picked()]

        choices = {}
        for name in names:
            rows = human_rows(meta, name)
            desc = comment_of(meta, name)
            choices[name] = ui.div(
                ui.div(
                    ui.span(name, class_="name"),
                    ui.span(f" · {rows}", class_="text-muted small") if rows else None,
                ),
                ui.div(desc, class_="desc text-muted") if desc else None,
            )
        return ui.div(
            ui.input_checkbox_group("tables", None, choices=choices, selected=selected),
            id="table-picker",
            class_="border rounded",
        )

    @render.ui
    def start():
        available, _ = loaded()
        names = [name for name in available if name in picked()]
        if not names:
            return ui.p("Pick at least one table.", class_="text-muted my-3")
        if len(names) > MAX_TABLES:
            return ui.p(
                f"{len(names)} tables selected — pick at most {MAX_TABLES}.",
                class_="text-danger my-3",
            )
        # A link that forces a page load; QueryChat locks its table set once
        # its server starts.
        return ui.div(
            ui.a(
                "Start exploring",
                href="?" + urlencode({"tables": ",".join(names)}),
                class_="btn btn-primary",
            ),
            ui.a("Clear", href="?", class_="btn btn-link"),
            class_="my-3",
        )

    @render.ui
    def chosen():
        """
        Renders the set of selected tables. Unlike picker(), the full
        table description is shown.
        """
        available, meta = loaded()
        names = [name for name in available if name in picked()]
        if not names:
            return None
        cards = []
        for name in names:
            rows = human_rows(meta, name)
            cards.append(
                ui.div(
                    ui.strong(name),
                    ui.span(f" · {rows}", class_="text-muted small") if rows else None,
                    ui.p(
                        comment_of(meta, name) or "No description provided.",
                        class_="small text-muted mb-0 mt-1",
                    ),
                    class_="mb-3",
                )
            )
        return ui.div(
            ui.hr(),
            ui.h6(f"Selected ({len(names)})", class_="text-muted"),
            *cards,
        )


def dashboard_ui(names):
    # Rendering the chat needs the module id and tools, not the data, so this
    # instance holds no connection and is safe to build outside a session.
    qc_ui = QueryChat(id=QUERYCHAT_ID, tools=TOOLS)

    return qc_ui.page(
        ui.div(
            TITLE,
            # A link to force a page load with an empty table set.
            ui.a(
                "Tables…",
                href="?",
                class_="btn btn-outline-secondary btn-sm ms-3",
            ),
            class_="d-flex align-items-center",
        ),
        window_title=TITLE,
        drawer=chat_drawer(
            ui.head_content(ui.include_css(STYLES)),
            # Every panel below waits on the same thing, so let the progress
            # notification be the only indicator rather than showing four
            # spinners.
            ui.busy_indicators.use(spinners=False),
            ui.div(
                ui.div(
                    ui.input_radio_buttons("active_table", None, choices=names, selected=names[0]),
                    id="table-list",
                ),
                ui.card(
                    ui.card_header(
                        "Data Table",
                        ui.span(
                            ui.output_text("row_note", inline=True),
                            class_="text-muted ms-2",
                        ),
                        ui.input_action_link("expand", "Expand", class_="ms-auto"),
                    ),
                    ui.output_data_frame("data_table"),
                ),
                # A fillable column so the Data card, the only card left in
                # the drawer, can grow into the drawer's full height.
                class_="html-fill-container",
                style="height: 100%;",
            ),
            title=f"Tables ({len(names)})",
            width=420,
        ),
    )


def dashboard_server(input: Inputs, session: Session, names):
    values = reactive.value(None)

    @reactive.effect
    async def _load():
        try:
            # async keeps the event loop free to deliver progress messages.
            with ui.Progress() as progress:
                progress.set(message="Loading credentials")
                creds = credentials(session)

                progress.set(message="Connecting to Snowflake")
                con, ibiscon = await asyncio.to_thread(connect, creds)
                session.on_ended(con.close)

                progress.set(message="Connecting to Snowpark")
                sp_session = await asyncio.to_thread(snowpark_session, con)
                session.on_ended(sp_session.close)

                progress.set(message="Reading table descriptions")
                meta = await asyncio.to_thread(table_metadata, con)

                progress.set(message="Starting the Cortex session")
                chat = await asyncio.to_thread(get_chat, sp_session)
                session.on_ended(chat.close)

                progress.set(message="Constructing chat")
                qc = QueryChat(
                    id=QUERYCHAT_ID,
                    client=chat,
                    tools=TOOLS,
                    data_description=describe(names, meta),
                    extra_instructions=EXTRA_INSTRUCTIONS,
                    # Switching the selected tables is a page reload because the
                    # QueryChat table set is fixed after its server starts.
                    # Prevent shinychat from restoring an old conversation which
                    # targeted different tables.
                    history=HistoryOptions(restore_mode="none"),
                )
                qc.greeter.prompt = GREETING_PROMPT

                progress.set(message=f"Registering {len(names)} {'table' if len(names) == 1 else 'tables'}")
                # One add_tables call, so the prompt is built once for the batch.
                await asyncio.to_thread(qc.add_tables, ibiscon, names, include_in_greeting=True)

                progress.set(message="Generating greeting")
                await asyncio.to_thread(qc.generate_greeting)

                progress.set(message="Writing an overview of the tables")
                server_values = qc.server()
                cap_query_tool(server_values.client)
                values.set(server_values)
        except SnowflakeIntegrationError as e:
            ui.notification_show(integration_error_card(str(e)), type="error", duration=None)
        except snowflake.connector.Error as e:
            ui.notification_show(connection_error_card(str(e)), type="error", duration=None)

    def vals():
        """querychat's per-session values, once the loading effect has them."""
        return req(values())

    # The panel follows whichever table the model last filtered, until the
    # viewer picks one — then it stays put rather than moving mid-read. Picking
    # the table the model is already on resumes following.
    followed = reactive.value(names[0])
    pinned = reactive.value(False)

    @reactive.effect
    @reactive.event(input.active_table)
    def _pin():
        if input.active_table() == followed():
            return
        pinned.set(input.active_table() != vals().current_table())

    @reactive.effect
    def _follow():
        # Compares against `followed`, not input.active_table(): depending on
        # that input would re-run this on the viewer's own click, and effect
        # order is not guaranteed, so it could undo the click before _pin sees.
        name = vals().current_table()
        if name is None or pinned() or name == followed():
            return
        followed.set(name)
        ui.update_radio_buttons("active_table", selected=name)

    @reactive.calc
    def active_frame():
        # df() is a lazy Ibis table — the whole table before any filter, the
        # generated query after one. Limit before materializing, or Shiny pulls
        # every row from Snowflake. A calc, so the grid, the row note and the
        # modal share one query.
        df = vals().table(input.active_table()).df().head(MAX_ROWS)
        return df.to_pandas() if hasattr(df, "to_pandas") else df

    @render.text
    def row_note():
        # MAX_ROWS back means the cap was probably hit, so say the view is
        # partial rather than letting it look complete.
        count = len(active_frame())
        return f"first {count} rows" if count >= MAX_ROWS else f"{count} rows"

    @render.data_frame
    def data_table():
        return active_frame()

    @render.data_frame
    def data_table_wide():
        return active_frame()

    @reactive.effect
    @reactive.event(input.expand)
    def _expand():
        # The sidebar is too narrow for a wide table, so give the grid the
        # window on request instead of spending chat width on it permanently.
        ui.modal_show(
            ui.modal(
                ui.output_data_frame("data_table_wide"),
                title=f"Data Table: {input.active_table()} (first {MAX_ROWS} rows at most)",
                size="xl",
                easy_close=True,
                footer=None,
            )
        )


def app_ui(request):
    # The dashboard chat interface runs when we have a table selection
    # (provided by the ?tables= query argument). Run the table selector when
    # none have been chosen.
    params = request.query_params
    names = selected_tables(params)
    if not names:
        return setup_ui()
    else:
        return dashboard_ui(names)


def server(input: Inputs, output: Outputs, session: Session):
    # The dashboard chat interface runs when we have a table selection
    # (provided by the ?tables= query argument). Run the table selector when
    # none have been chosen.
    params = read_params(session)
    names = selected_tables(params)
    if not names:
        setup_server(input, session)
    else:
        dashboard_server(input, session, names)


app = App(app_ui, server)
