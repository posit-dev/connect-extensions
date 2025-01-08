import humanize
import pendulum
from shiny.ui import Tag as e


def TitleComponent(title: str | None):
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
    return date.format("MMMM Do YYYY, hh:mm:ss A zz")


def DurationComponent(value: str):
    if not value:
        return

    dt = pendulum.parse(value)
    return dt.diff_for_humans()


def ContentDetailsComponent(
    content: dict, metrics: dict, jobs: list[dict], processes: list[dict]
):
    return [
        ContentInformationComponent(content),
        ContentActivityComponent(metrics),
        ContentSessionComponent(processes),
    ]


def ContentInformationComponent(content: dict):
    return e(
        "div",
        {"id": "content-information", "class": "row pb-4 gap-2"},
        [
            e("h5", "Details"),
            DetailsComponent("Title", TitleComponent(content.get("title"))),
            DetailsComponent(
                "Updated", DateTimeComponent(content.get("last_deployed_time"))
            ),
            DetailsComponent("Created", DateTimeComponent(content.get("created_time"))),
        ],
    )


def ContentActivityComponent(metrics: list[dict]):
    times = [event.get("started") for event in metrics]
    times = sorted(times)

    return e(
        "div",
        {"id": "content-metrics", "class": "row pb-4 gap-2"},
        [
            e("h5", "Activity"),
            DetailsComponent("Views", len(metrics)),
            DetailsComponent("Last Visit", DateTimeComponent(times[-1])),
            DetailsComponent("First Visit", DateTimeComponent(times[0])),
        ],
    )


def ContentSessionComponent(processes: list[dict]):
    if len(processes) == 0:
        return

    return e(
        "div",
        {"id": "content-metrics", "class": "row pb-4 gap-2"},
        [
            e("h5", "Sessions"),
            [
                e(
                    "div",
                    {"class": "row pb-3 gap-2"},
                    [
                        DetailsComponent("Process Id", process.get("pid")),
                        DetailsComponent(
                            "Started", DurationComponent(process.get("start_time"))
                        ),
                        DetailsComponent(
                            "CPUs", format(process.get("cpu_current"), ".1f")
                        ),
                        DetailsComponent(
                            "Memory", humanize.naturalsize(process.get("ram"), gnu=True)
                        ),
                        DetailsComponent("Host", process.get("hostname")),
                    ],
                )
                for process in processes
            ],
        ],
    )


def DetailsComponent(label: str, value: str | None):
    """Helper function to create a Bootstrap row with label and value."""
    return e(
        "div",
        {"class": "row"},
        [
            e("span", {"class": "col-2 text-secondary"}, label),
            e("span", {"class": "col-10"}, value),
        ],
    )
