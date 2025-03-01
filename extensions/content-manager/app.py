import json

import pendulum
from posit import connect
from shiny import App, render, ui
from shiny.ui import Tag as e

from assets import bootstrap, fontawesome
from components import ContentDetailsComponent, NameComponent

client = connect.Client()

user = client.me
content = client.content.find()
content = [item for item in content if item["owner_guid"] == user["guid"]]


def get_title(row):
    return e(
        "div",
        [
            e("div", {"class": "fw-bold"}, row.get("title") or "No Name"),
            e("div", {"class": "text-secondary"}, row.get("guid")),
        ],
    )


def get_link(row):
    return e(
        "a",
        {
            "class": "fa-solid fa-arrow-up-right-from-square",
            "href": row["dashboard_url"],
            "target": "_blank",
        },
    )


def get_language(content):
    if content.get("r_version"):
        return e("span", {"class": "badge text-secondary"}, "R")

    if content.get("py_version"):
        return e("span", {"class": "badge text-secondary"}, "Python")

    if content.get("quarto_version"):
        return e("span", {"class": "badge text-secondary"}, "Quarto")

    if content.get("content_category") == "pin":
        return e("span", {"class": "badge text-secondary"}, "Pin")

    return None


def get_time(value):
    date = pendulum.parse(value)
    return date.format("MMM Do, YYYY")

# Create the table rows
rows = []
for idx, row in enumerate(content):
    element_id = f"row_{str(idx)}"
    row = e(
        "tr",
        {
            "id": element_id,
            "data-bs-toggle": "offcanvas",
            "data-bs-target": "#details",
            "class": "clickable-item",
        },
        [
            e("td", get_link(row)),
            e(
                "td",
                [
                    e("div", {"class": "fw-bold"}, NameComponent(row.get("title"))),
                    e("div", {"class": "text-secondary"}, row.get("guid")),
                ],
            ),
            e("td", get_language(row)),
            e("td", get_time(row["last_deployed_time"])),
            e("td", get_time(row["created_time"])),
        ],
        e(
            "script",
            f"""
            document.getElementById('{element_id}').addEventListener('click', async () => {{
                await Shiny.setInputValue('selected_content_guid', {json.dumps(row["guid"])});
            }})
            """,
        ),
    )
    rows.append(row)

# Create the static table
table = e(
    "div",
    [
        e("h1", {"class": "display-3"}, "Content Management"),
        e(
            "p",
            {"class": "lead"},
            "Manage your content and their settings here.",
        ),
        e(
            "table",
            {"class": "table"},
            e(
                "thead",
                e(
                    "tr",
                    e("th", {"scope": "col"}, ""),
                    e("th", {"scope": "col"}, "Title"),
                    e("th", {"scope": "col"}, "Language"),
                    e("th", {"scope": "col"}, "Last Updated"),
                    e("th", {"scope": "col"}, "Date Added"),
                ),
            ),
            e("tbody", *rows),
        ),
    ],
)

html = e(
    "html",
    e(
        "head",
        e("meta", name="viewport", content="width=device-width, initial-scale=1.0"),
        e("meta", **{"http-equiv": "X-UA-Compatible", "content": "ie=edge"}),
        bootstrap.css,
        fontawesome.icons,
        e(
            "style",
            """
            .offcanvas.offcanvas-end {
                width: 800px;
            }
            """,
        ),
    ),
    e(
        "body",
        [
            e("div", {"class": "container"}, table),
            e(
                "div",
                {
                    "class": "offcanvas offcanvas-end",
                    "tabindex": "-1",
                    "id": "details",
                },
                [
                    e(
                        "div",
                        {"class": "offcanvas-header"},
                        [
                            e(
                                "h3",
                                {"class": "offcanvas-title"},
                                "Content Details",
                            ),
                            e(
                                "button",
                                {
                                    "type": "button",
                                    "class": "btn-close",
                                    "data-bs-dismiss": "offcanvas",
                                },
                            ),
                        ],
                    ),
                    e(
                        "div",
                        {"class": "offcanvas-body"},
                        ui.output_ui("sidebar"),
                    ),
                ],
            ),
            bootstrap.js,
        ],
    ),
)


def server(input, output, session):

    def get_processes():
        response = client.get("metrics/procs")
        processes = response.json()
        return processes

    @output
    @render.ui
    def sidebar():
        content_guid = input.selected_content_guid.get()
        content = client.content.get(content_guid)
        metrics = client.metrics.usage.find(content_guid=content_guid)

        processes = [
            process
            for process in get_processes()
            if process.get("app_guid") == content_guid
        ]

        return ContentDetailsComponent(content, content.owner, metrics, content.jobs, processes, input, output, session)


app = App(html, server)
