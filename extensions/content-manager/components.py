import humanize
import pendulum
from shiny.ui import Tag as e
from shiny import ui


def NameComponent(title: str | None):
    if title:
        return title
    return e("em", "No Name")


def DateComponent(value: str):
    date = pendulum.parse(value)
    local_tz = pendulum.local_timezone()
    date = local_tz.convert(date)
    return date.format("MMM Do, YYYY")


def DateTimeComponent(value: str):
    date = pendulum.parse(value)
    local_tz = pendulum.local_timezone()
    date = local_tz.convert(date)
    return date.format("MMM Do YYYY, hh:mm:ss A zz")


def DurationComponent(value: str):
    if not value:
        return

    dt = pendulum.parse(value)
    return dt.diff_for_humans()


def ContentDetailsComponent(
    content: dict, author: dict, metrics: dict, jobs: list[dict], processes: list[dict],
):
    return [
        ContentInformationComponent(content),
        ContentAuthorComponent(author),
        ContentActivityComponent(metrics),
        ContentSessionsComponent(processes),
    ]


def ContentInformationComponent(content: dict):
    title = "Details"
    details = [
        CardBodyLabelAndValueComponent(
            "Name", NameComponent(content.get("title"))
        ),
        CardBodyLabelAndValueComponent(
            "Updated", DurationComponent(content.get("last_deployed_time"))
        ),
        CardBodyLabelAndValueComponent(
            "Created", DateComponent(content.get("created_time"))
        ),
    ]
    return CardComponent(title, details)

def ContentAuthorComponent(author: dict ):
    print(author)
    title = "Author"
    author = [
        CardBodyLabelAndValueComponent(
            "First Name", NameComponent(author.get("first_name"))
        ),
        CardBodyLabelAndValueComponent(
            "Last Name", NameComponent(author.get("last_name"))
        ),
        CardBodyLabelAndValueComponent("Email", NameComponent(author.get("email"))),
        CardBodyLabelAndValueComponent(
            "Last Active", DurationComponent(author.get("active_time"))
        ),
    ]

    return CardComponent(title, author)

def ContentActivityComponent(events: list[dict]):
    if len(events) == 0:
        return

    title = "Activity"

    times = [event.get("started") for event in events]
    times = sorted(times)

    details = [
        CardBodyLabelAndValueComponent("Views", len(times)),
        CardBodyLabelAndValueComponent("Last Visit", DurationComponent(times[-1])),
        CardBodyLabelAndValueComponent("First Visit", DateComponent(times[0])),
    ]

    return CardComponent(
        title,
        details,
        # ui.output_ui("views_chart"),
    )


def ContentSessionsComponent(processes: list[dict]):
    if len(processes) == 0:
        return

    def ContentSessionComponent(process: dict):
        return [
            CardBodyLabelAndValueComponent("Id", process.get("pid")),
            CardBodyLabelAndValueComponent(
                "Started", DurationComponent(process.get("start_time"))
            ),
            CardBodyLabelAndValueComponent(
                "CPUs", format(process.get("cpu_current"), ".1f")
            ),
            CardBodyLabelAndValueComponent(
                "Memory", humanize.naturalsize(process.get("ram"), gnu=True)
            ),
            CardBodyLabelAndValueComponent("Host", process.get("hostname")),
        ]

    title = "Instances"
    details = [ContentSessionComponent(process) for process in processes]
    return CardComponent(title, *details)


def CardBodyLabelAndValueComponent(label, value):
    return (
        e(
            "div",
            {"class": "d-flex justify-content-between mb-1"},
            [
                e(
                    "span",
                    {"class": "text-secondary"},
                    label,
                ),
                e("span", value),
            ],
        ),
    )

def CardComponent(title, *details):
    return e(
        "div",
        {"class": "row m-3"},
        [
            e("h5", title),
            [
                e(
                    "div",
                    {"class": "col-6"},
                    e(
                        "div",
                        {"class": "card position"},
                        e("div", {"class": "card-body"}, detail),
                    ),
                )
                for detail in details
            ],
        ],
    )
