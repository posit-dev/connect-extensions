import re
from datetime import datetime
from functools import cache
from typing import Callable

import pandas as pd
from htmltools import tags
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from posit.connect import Client
from shiny import reactive
from shiny.express import input, render, ui

# This is the max page size accepted by the API.
# Use this until we have pagination.
page_size = 500

client = Client()
apps = reactive.value(pd.DataFrame([]))

with ui.sidebar():
    ui.input_text("name", "Package Name")
    ui.input_text("min_version", "Minimum version (>=)")
    ui.input_text("max_version", "Maximum version (<)")
    ui.hr()
    ui.input_action_button("lock_selected", "Lock Selected")
    ui.input_action_button("delete_selected", "Delete Selected")


@render.text
def datagrid_label():
    ui.busy_indicators.options(spinner_type=None)
    if has_valid_spec():
        return f"{num_apps()} items using {package_spec()}"
    else:
        return "Please enter a package name and optional versions."


def update_apps():
    spec = package_spec()
    if not has_valid_spec():
        return
    data = prepare_app_data(get_apps(spec))
    apps.set(data)


@render.data_frame
def app_grid():
    if not has_valid_spec():
        return None
    update_apps()
    return render.DataGrid(
        apps.get(),
        width="100%",
        height="100%",
        selection_mode="rows",
        styles=dict(style={"white-space": "nowrap"}),
    )


@reactive.calc
def num_apps():
    return len(apps.get())


@reactive.calc
def package_spec():
    spec = input.name()
    if spec == "":
        return ""
    if input.min_version() != "":
        spec += ">=" + input.min_version()
    if input.max_version() != "":
        comma = "," if input.min_version() != "" else ""
        spec += comma + "<" + input.max_version()
    return f'package:"{spec}"'


@reactive.calc
def has_valid_spec():
    spec = package_spec()
    if not spec:
        return False

    match = re.match(r'package:"[A-Za-z0-9_.-]+(.*)"', spec)
    if not match:
        return False

    versionSpec = match.group(1)
    if not versionSpec:
        return True

    try:
        _ = SpecifierSet(versionSpec)
        return True
    except InvalidSpecifier:
        return False


def get_apps(spec: str) -> pd.DataFrame:
    page_number = 1
    all_apps = []

    while True:
        response = client.get(
            "v1/search/content",
            params={
                "q": spec,
                "page_size": page_size,
                "page_number": page_number,
                "include": "owner"
            },
        )
        if response.status_code != 200:
            raise Exception(f"Failed to search for {spec}: {response.text}")

        data = response.json()
        results = data.get("results")
        if results is None:
            raise Exception(f"Invalid search response from server: {response.text}")

        if not results:
            # paged all the way through
            break

        # flatten the included owner sub-object
        for app in results:
            owner = app["owner"]
            app["owner_username"] = owner["username"]
            app["owner_first_name"] = owner["first_name"]
            app["owner_last_name"] = owner["last_name"]

        all_apps.extend(results)
        page_number += 1

    print(f"Found {len(all_apps)} apps matching '{spec}'")
    return pd.DataFrame(all_apps)


def get_display_name(row):
    if row.owner_first_name and row.owner_last_name:
        name = row.owner_first_name + " " + row.owner_last_name
    elif row.owner_first_name:
        name = row.owner_first_name
    elif row.owner_last_name:
        name = row.owner_last_name
    else:
        return row.owner_username
    return f"{row.owner_username} ({name})"


@cache
def get_owner_email(owner_guid: str) -> str:
    user = client.users.get(owner_guid)
    return user.email


def prepare_app_data(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return df

    df["title_link"] = None
    df["owner"] = None
    df["owner_email"] = None
    df["email_link"] = None
    df["created"] = pd.to_datetime(df["created_time"]).dt.date
    for i, row in df.iterrows():
        df.at[i, "app_link"] = tags.a(
            tags.span("↗", style="font-size: 1.5em"),
            target="_blank",
            href=row.dashboard_url,
        )
        title_len = 50
        title = df.at[i, "title"] or ""
        df.at[i, "title"] = title[:title_len] + (
            "..." if len(title) > title_len else ""
        )

        display_name = get_display_name(row)
        email = get_owner_email(row.owner_guid)

        df.at[i, "owner_display_name"] = display_name
        df.at[i, "owner_email"] = email
        if email:
            df.at[i, "email_link"] = tags.a(email, href=f"mailto:{email}")
        else:
            df.at[i, "email_link"] = email

        df.at[i, "lock_icon"] = "🔒" if row.locked else ""

        if row.bundle_id:
            bundle_url = f"{client.cfg.url}/v1/content/{row.guid}/bundles/{row.bundle_id}/download"
            df.at[i, "bundle_link"] = tags.a(
                tags.span("⤓", style="font-size: 1.5em"),
                target="_blank",
                href=bundle_url,
            )

    columns = {
        "app_link": "App",
        "id": "ID",
        "title": "Title",
        "owner_display_name": "Owner",
        "email_link": "Email",
        "created": "Created",
        "guid": "GUID",
        "bundle_link": "Download",
        "lock_icon": "Locked",
    }
    df = df[columns.keys()].rename(columns=columns)
    return df


@reactive.calc
def has_selection():
    return len(input.app_grid_selected_rows()) > 0


def each_selected_app(message: str, func: Callable[[str], bool]):
    rows = input.app_grid_selected_rows()
    if not rows:
        return

    selected_guids = apps.get().loc[list(rows)]["GUID"].tolist()
    print("Locking selected apps:", selected_guids)

    with ui.Progress(min=0, max=len(selected_guids)) as p:
        p.set(message=message + "...", value=0)
        success_count = 0

        for i, guid in enumerate(selected_guids):
            if func(guid):
                success_count += 1
            p.set(value=i + 1)

    update_apps()
    return success_count



@reactive.effect
@reactive.event(input.lock_selected)
def lock_selected_apps():
    rows = input.app_grid_selected_rows()
    if not rows:
        return

    successes = each_selected_app("Locking applications", lock_app)
    ui.notification_show(
        f"Locked {successes} out of {len(rows)} applications",
        type="message",
    )


def lock_app(guid):
    try:
        content = client.content.get(guid)
        today = datetime.now().date().isoformat()
        content.update(
            locked=True,
            locked_message=f"Locked on {today} because it is using a package matching '{package_spec()}'",
        )
        return True
    except Exception as e:
        print(f"Error locking app {guid}: {e}")
        return False


@reactive.effect
@reactive.event(input.delete_selected)
def delete_selected_apps():
    rows = input.app_grid_selected_rows()
    if not rows:
        return

    successes = each_selected_app("Deleting applications", delete_app)
    ui.notification_show(
        f"Deleted {successes} out of {len(rows)} applications",
        type="message",
    )


def delete_app(guid):
    try:
        content = client.content.get(guid)
        content.delete()
        return True
    except Exception as e:
        print(f"Error deleting app {guid}: {e}")
        return False
