"""Bundle Storage Report

Reports bundle storage per content item on a Posit Connect server, with a
focus on pins, and lets an administrator set bundle retention limits on many
items at once.

Built for servers with thousands of content items:

- Data loads in a background task (the app stays responsive) and is cached
  for the whole process, so new sessions and filter changes don't refetch.
- Filtering, sorting and totals run on the server; the browser only ever
  receives the top rows of the current view (100 by default).
- Bulk changes can target every item matching the filters, not just the rows
  you can see, and run several API calls at once.
"""

from __future__ import annotations

import asyncio
import os
import time
import traceback
from datetime import date

import faicons
from posit.connect import Client
from posit.connect.errors import ClientError
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui

import storage_utils as su

ON_CONNECT = os.getenv("RSTUDIO_PRODUCT") == "CONNECT"
CACHE = su.ReportCache(ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "600")))
PATCH_CONCURRENCY = 8
CONFIRM_TYPING_THRESHOLD = 100  # bulk changes this large must be typed to confirm

SORT_CHOICES = {
    "_bytes_total": "Total storage",
    "_bytes_inactive": "Inactive storage",
    "bundles": "Bundle count",
    "title": "Title",
}
ROW_LIMITS = {"100": "100", "250": "250", "500": "500"}

DISPLAY_LABELS = {
    "title": "Title",
    "type": "Type",
    "owner": "Owner",
    "bundles": "Bundles",
    "total_mb": "Total (MB)",
    "active_mb": "Active (MB)",
    "inactive_mb": "Inactive (MB)",
    "retention_limit": "Retention limit",
}

STYLE = ui.tags.style(
    """
    .bar-row { display: grid; grid-template-columns: minmax(0, 14rem) 1fr 5.5rem;
               gap: .5rem; align-items: center; margin-bottom: .35rem; font-size: .875rem; }
    .bar-label, .sel-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .bar-track { background: var(--bs-secondary-bg); border-radius: 4px; height: .9rem; }
    .bar-fill { background: var(--bs-primary); border-radius: 4px; height: 100%; }
    .bar-value { text-align: right; font-variant-numeric: tabular-nums; }
    .message-card { max-width: 720px; margin: 4rem auto; }
    .sel-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .5rem;
               font-size: .875rem; padding: .2rem 0; border-bottom: 1px solid var(--bs-border-color); }
    .view-note { font-size: .875rem; color: var(--bs-secondary-color); }
    """
)


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
def message_ui(title: str, *body):
    return ui.page_fillable(
        ui.card(ui.card_header(title), *body, class_="message-card"),
        title="Bundle Storage Report",
    )


INTEGRATION_HELP = message_ui(
    "Setup: Connect Visitor API Key",
    ui.markdown(
        """
This report runs **as the signed-in viewer**, so it needs a
*Connect Visitor API Key* integration.

In this content's settings, open the **Runtime** tab (**Access** before
Connect 2026.08.0) and add the "Connect Visitor API Key" integration under
**Integrations**. Then reload this page.

See the [OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key).
"""
    ),
)

NOT_ADMIN = message_ui(
    "Administrator access required",
    ui.p(
        "Bundle storage reporting and server-wide retention changes require "
        "the Administrator role. Ask a Connect "
        "administrator to view this report."
    ),
)


def report_ui():
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_switch("pins_only", "Pins only", value=False),
            ui.panel_conditional(
                "!input.pins_only",
                ui.input_selectize(
                    "types",
                    "Content type",
                    choices=[],
                    multiple=True,
                    options={"placeholder": "All types"},
                ),
            ),
            # update_on="blur": filter on Enter or leaving the field, not on
            # every keystroke.
            ui.input_text(
                "search",
                "Search title or owner",
                placeholder="Press Enter to search",
                update_on="blur",
            ),
            ui.input_numeric(
                "min_inactive_mb", "Min inactive storage (MB)", value=0, min=0, step=10
            ),
            ui.input_select("sort_by", "Sort by", SORT_CHOICES),
            ui.input_select("max_rows", "Rows shown", ROW_LIMITS),
            ui.hr(),
            ui.h6("Set retention limit"),
            ui.input_radio_buttons(
                "scope",
                "Apply to",
                {"selected": "Selected rows", "matching": "All items matching filters"},
            ),
            ui.output_text("scope_summary"),
            ui.input_radio_buttons(
                "limit_mode",
                "Limit",
                {
                    "n": "Keep N inactive bundles",
                    "all": "Keep all inactive bundles",
                    "default": "Use server default",
                },
            ),
            ui.panel_conditional(
                "input.limit_mode === 'n'",
                ui.input_numeric("limit_n", "N", value=3, min=1, step=1),
            ),
            ui.input_action_button("apply", "Apply…", class_="btn-primary w-100"),
            ui.hr(),
            ui.download_button("download_csv", "Export CSV (all matching)", width="100%"),
            ui.input_action_button(
                "refresh",
                "Reload from Connect",
                icon=faicons.icon_svg("rotate"),
                class_="w-100 btn-outline-secondary",
            ),
            ui.output_text("loaded_at", inline=False),
            width=310,
        ),
        ui.output_ui("body"),
        STYLE,
        title="Bundle Storage Report",
        fillable=False,
    )


def body_ui():
    return ui.TagList(
        ui.layout_column_wrap(
            ui.value_box(
                "Bundle storage on server",
                ui.output_text("vb_total"),
                ui.output_text("vb_total_sub"),
                showcase=faicons.icon_svg("hard-drive"),
            ),
            ui.value_box(
                "Inactive (reclaimable)",
                ui.output_text("vb_inactive"),
                ui.output_text("vb_inactive_sub"),
                showcase=faicons.icon_svg("box-archive"),
                theme="warning",
            ),
            ui.value_box(
                "Pins",
                ui.output_text("vb_pins"),
                ui.output_text("vb_pins_sub"),
                showcase=faicons.icon_svg("thumbtack"),
                theme="primary",
            ),
            fill=False,
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Largest inactive storage in this view"),
                ui.output_ui("top_bars"),
            ),
            ui.card(
                ui.card_header("Selected items"),
                ui.output_ui("selected_links"),
            ),
            col_widths=(8, 4),
            fill=False,
        ),
        ui.card(
            ui.card_header(
                "Content by bundle storage",
                ui.tags.small(
                    " — select rows to act on them", class_="text-body-secondary"
                ),
            ),
            ui.output_ui("view_note"),
            ui.output_data_frame("table"),
            full_screen=True,
            min_height="420px",
        ),
    )


def loading_ui(detail: str):
    return ui.card(
        ui.card_body(
            ui.div(
                ui.div(class_="spinner-border spinner-border-sm me-2", role="status"),
                ui.span(detail),
                class_="d-flex align-items-center",
            )
        )
    )


app_ui = ui.page_output("screen")


# --------------------------------------------------------------------------- #
# Server
# --------------------------------------------------------------------------- #
def make_client(session: Session) -> tuple[Client | None, str | None]:
    """Return (client, problem). problem is 'integration', 'admin' or 'error'."""
    token = session.http_conn.headers.get("Posit-Connect-User-Session-Token")
    try:
        if token:
            client = Client().with_user_session_token(token)
        elif ON_CONNECT:
            # Never fall back to the publisher's key on Connect: viewers would
            # act with the publisher's permissions.
            return None, "integration"
        else:
            # Local development: CONNECT_SERVER / CONNECT_API_KEY.
            client = Client()
        if client.me.get("user_role") != "administrator":
            return None, "admin"
        return client, None
    except ClientError as err:
        if err.error_code == 212:  # no Visitor API Key integration configured
            return None, "integration"
        traceback.print_exc()
        return None, "error"
    except Exception:
        traceback.print_exc()
        return None, "error"


def plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def server(input: Inputs, output: Outputs, session: Session):
    client, problem = make_client(session)

    @render.ui
    def screen():
        if problem == "integration":
            return INTEGRATION_HELP
        if problem == "admin":
            return NOT_ADMIN
        if problem == "error":
            return message_ui(
                "Could not connect",
                ui.p("The report could not reach the Connect API. Check the logs."),
            )
        return report_ui()

    if client is None:
        return

    # ---- data: loaded in a background thread, cached per process ----------- #
    # Seed from the cache so a warm process renders immediately.
    data = reactive.value(CACHE.current())
    load_error = reactive.value(None)

    @reactive.extended_task
    async def load_task(force: bool):
        return await asyncio.to_thread(CACHE.get, client, force)

    @reactive.effect
    def _start_load():
        force = input.refresh() > 0
        with reactive.isolate():
            load_error.set(None)
        load_task.invoke(force)

    @reactive.effect
    def _receive_load():
        status = load_task.status()
        if status == "success":
            data.set(load_task.result())
        elif status == "error":
            try:
                load_task.result()
            except Exception as err:  # surface the reason in the UI
                traceback.print_exc()
                load_error.set(str(err))

    @render.ui
    def body():
        if load_error():
            return ui.card(
                ui.card_header("Could not load storage data"),
                ui.p(load_error()),
                ui.p("Use Reload from Connect to try again."),
            )
        if data() is None:
            return loading_ui(
                "Loading bundle storage for every content item. On large "
                "servers this can take a minute; later visits use a cached copy."
            )
        return body_ui()

    @render.text
    def loaded_at():
        if load_task.status() == "running" and data() is not None:
            return "Reloading…"
        d = data()
        if d is None:
            return ""
        mins = int((time.time() - d[2]) // 60)
        return f"Data loaded {'just now' if mins == 0 else f'{mins} min ago'}."

    @reactive.calc
    def totals():
        req(data())
        return data()[0]

    @reactive.calc
    def report():
        req(data())
        return data()[1]

    @reactive.effect
    def _update_types():
        types = sorted(report()["type"].unique().tolist())
        with reactive.isolate():
            current = input.types()
        ui.update_selectize("types", choices=types, selected=current)

    @reactive.calc
    def view():
        """Every item matching the filters, sorted. Never sent whole to the browser."""
        return su.filter_report(
            report(),
            pins_only=input.pins_only(),
            types=list(input.types() or []),
            search=input.search(),
            sort_by=input.sort_by(),
            min_inactive_mb=input.min_inactive_mb() or 0,
        )

    @reactive.calc
    def shown():
        """The rows actually rendered in the table."""
        return view().head(int(input.max_rows()))

    # ---- value boxes ------------------------------------------------------- #
    @render.text
    def vb_total():
        return su.format_bytes(totals().get("bytes_total"))

    @render.text
    def vb_total_sub():
        t = totals()
        return f"{plural(t.get('count', 0), 'bundle')} across {plural(t.get('content_count', 0), 'item')}"

    @render.text
    def vb_inactive():
        return su.format_bytes(totals().get("bytes_inactive"))

    @render.text
    def vb_inactive_sub():
        t = totals()
        total = t.get("bytes_total") or 0
        pct = 100 * (t.get("bytes_inactive") or 0) / total if total else 0
        return f"{pct:.0f}% of bundle storage"

    @reactive.calc
    def pins():
        return report()[report()["type"] == "pin"]

    @render.text
    def vb_pins():
        return su.format_bytes(pins()["_bytes_total"].sum())

    @render.text
    def vb_pins_sub():
        p = pins()
        return (
            f"{plural(len(p), 'pin')}, {plural(int(p['bundles'].sum()), 'version')}, "
            f"{su.format_bytes(p['_bytes_inactive'].sum())} inactive"
        )

    # ---- top 10 chart ------------------------------------------------------ #
    @render.ui
    def top_bars():
        top = view().nlargest(10, "_bytes_inactive")
        top = top[top["_bytes_inactive"] > 0]
        if top.empty:
            return ui.p("No inactive bundle storage in this view.", class_="mb-0")
        biggest = top["_bytes_inactive"].max()
        return ui.div(
            *[
                ui.div(
                    ui.span(
                        r["title"], class_="bar-label", title=f"{r['title']} — {r['owner']}"
                    ),
                    ui.div(
                        ui.div(
                            class_="bar-fill",
                            style=f"width:{100 * r['_bytes_inactive'] / biggest:.1f}%",
                        ),
                        class_="bar-track",
                    ),
                    ui.span(su.format_bytes(r["_bytes_inactive"]), class_="bar-value"),
                    class_="bar-row",
                )
                # to_dict, not itertuples: itertuples renames "_"-prefixed columns
                for r in top.to_dict("records")
            ]
        )

    # ---- table ------------------------------------------------------------- #
    @render.ui
    def view_note():
        v, s = len(view()), len(shown())
        matching = f"{plural(v, 'item')} match"
        if v > s:
            return ui.p(
                f"Showing the top {s:,} of {v:,} matching items "
                f"({su.format_bytes(view()['_bytes_inactive'].sum())} inactive in all). "
                "Narrow the filters, raise Rows shown, or export CSV for the full list.",
                class_="view-note mb-2",
            )
        return ui.p(
            f"{matching} ({su.format_bytes(view()['_bytes_inactive'].sum())} inactive).",
            class_="view-note mb-2",
        )

    @render.data_frame
    def table():
        # Plain text cells only: HTML cells are costly to render by the thousand.
        df = shown()[list(DISPLAY_LABELS)].rename(columns=DISPLAY_LABELS)
        return render.DataGrid(
            df, selection_mode="rows", filters=False, width="100%", height="560px"
        )

    @reactive.calc
    def selected():
        # data_view keeps the index of shown(), so this stays correct when the
        # viewer re-sorts the table by clicking a column header.
        s = shown()
        idx = table.data_view(selected=True).index
        return s.loc[s.index.intersection(idx)]

    @render.ui
    def selected_links():
        sel = selected()
        if sel.empty:
            return ui.p(
                "Select rows to see links to their settings in Connect.",
                class_="view-note mb-0",
            )
        items = [
            ui.div(
                ui.span(r["title"], class_="sel-title", title=r["owner"]),
                ui.a("Open", href=r["dashboard_url"], target="_blank", rel="noopener")
                if r["dashboard_url"]
                else ui.span(),
                class_="sel-row",
            )
            for r in sel.head(25).to_dict("records")
        ]
        more = ui.p(f"…and {len(sel) - 25:,} more", class_="view-note mt-1") if len(sel) > 25 else None
        return ui.div(*items, more)

    # ---- bulk retention ---------------------------------------------------- #
    @reactive.calc
    def targets():
        return selected() if input.scope() == "selected" else view()

    @render.text
    def scope_summary():
        t = targets()
        if t.empty:
            return (
                "Select rows in the table."
                if input.scope() == "selected"
                else "No items match the filters."
            )
        return f"{plural(len(t), 'item')} · {su.format_bytes(t['_bytes_inactive'].sum())} inactive"

    def requested_limit():
        mode = input.limit_mode()
        if mode == "default":
            return None, "the server default"
        if mode == "all":
            return 0, "keep all inactive bundles"
        n = input.limit_n()
        if n is None or n < 1 or int(n) != n:
            return "invalid", None
        return int(n), f"keep {plural(int(n), 'inactive bundle')}"

    pending = reactive.value(None)  # frozen target list while the modal is open

    @reactive.effect
    @reactive.event(input.apply)
    def _confirm():
        t = targets()
        if t.empty:
            ui.notification_show(
                "Select rows first, or apply to all matching items.", type="warning"
            )
            return
        limit, label = requested_limit()
        if limit == "invalid":
            ui.notification_show("N must be a whole number of 1 or more.", type="error")
            return
        # Freeze the list so later filter changes can't alter what gets updated.
        pending.set(t[["guid", "title"]].copy())
        big = len(t) >= CONFIRM_TYPING_THRESHOLD
        ui.modal_show(
            ui.modal(
                ui.p(
                    ui.strong(f"Set the bundle retention limit to {label} on {plural(len(t), 'content item')}?")
                ),
                ui.p(
                    f"These items hold {su.format_bytes(t['_bytes_inactive'].sum())} of "
                    "inactive bundles. Connect deletes inactive bundles beyond the "
                    "limit, so older versions (for pins, older pin versions) can no "
                    "longer be restored. The active bundle is always kept.",
                    class_="text-body-secondary",
                ),
                ui.tags.ul(*[ui.tags.li(x) for x in t["title"].head(10)]),
                ui.p(f"…and {len(t) - 10:,} more") if len(t) > 10 else None,
                ui.input_text(
                    "confirm_count",
                    f"Type {len(t)} to confirm",
                )
                if big
                else None,
                title="Confirm retention limit",
                footer=ui.TagList(
                    ui.modal_button("Cancel"),
                    ui.input_action_button("confirm_apply", "Apply", class_="btn-danger"),
                ),
                easy_close=True,
            )
        )

    @reactive.effect
    @reactive.event(input.confirm_apply)
    async def _apply():
        t = pending()
        if t is None or t.empty:
            return
        if len(t) >= CONFIRM_TYPING_THRESHOLD and (input.confirm_count() or "").strip() != str(len(t)):
            ui.notification_show(f"Type {len(t)} to confirm.", type="warning")
            return
        ui.modal_remove()
        pending.set(None)
        limit, label = requested_limit()

        sem = asyncio.Semaphore(PATCH_CONCURRENCY)

        async def update(guid: str, title: str):
            async with sem:
                try:
                    await asyncio.to_thread(su.set_retention_limit, client, guid, limit)
                    return guid, None
                except Exception as err:  # keep going; report at the end
                    return guid, f"{title}: {err}"

        done, ok, failures = 0, [], []
        with ui.Progress(min=0, max=len(t)) as p:
            p.set(0, message=f"Updating {plural(len(t), 'item')}…")
            for fut in asyncio.as_completed(
                [update(g, ti) for g, ti in zip(t["guid"], t["title"])]
            ):
                guid, err = await fut
                done += 1
                (failures.append(err) if err else ok.append(guid))
                if done % 10 == 0 or done == len(t):
                    p.set(done, detail=f"{done:,} of {len(t):,}")

        # Update the cached report in place; no need to reload thousands of items.
        CACHE.update_retention(ok, su.retention_label(limit))
        if CACHE.current() is not None:
            data.set(CACHE.current())

        ui.notification_show(
            f"Set {label} on {plural(len(ok), 'item')}.",
            type="message" if not failures else "warning",
            duration=8,
        )
        if failures:
            ui.modal_show(
                ui.modal(
                    ui.tags.ul(*[ui.tags.li(f) for f in failures[:50]]),
                    ui.p(f"…and {len(failures) - 50:,} more") if len(failures) > 50 else None,
                    title=f"{plural(len(failures), 'update')} failed",
                    easy_close=True,
                )
            )

    # ---- export ------------------------------------------------------------ #
    @render.download_button(
        filename=lambda: f"bundle-storage-{date.today().isoformat()}.csv",
    )
    def download_csv():
        yield su.to_csv(view())


app = App(app_ui, server)
