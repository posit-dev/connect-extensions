import re
from datetime import datetime
from functools import cache
from typing import Callable
import requests
import json

import pandas as pd
from htmltools import tags
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from posit.connect import Client
from shiny import reactive
from shiny.express import input, render, ui

client = Client()
packages = reactive.value(pd.DataFrame([]))

with ui.sidebar():
    ui.input_text("guid", "Content GUID")

@render.text
def datagrid_label():
    ui.busy_indicators.options(spinner_type=None)
    if num_packages() > 0:
        return f"{num_packages()} packages for content '{content_title()}'"
    else:
        return "Please enter a content GUID to search for packages."

def update_packages(app_packages):
    data = prepare_packages_data(get_packages(app_packages))
    packages.set(data)


@render.data_frame
def app_grid():
    app_packages = packages_spec()
    if not app_packages:
        return None
    update_packages(app_packages)
    return render.DataGrid(
        packages.get(),
        width="100%",
        height="100%",
        selection_mode="rows",
        styles=dict(style={"white-space": "nowrap"}),
    )


@reactive.calc
def num_packages():
    return len(packages.get())

@reactive.calc
def content_title():
    if input.guid() == "":
        return
    response = client.get(
        f"v1/content/{input.guid()}",
    )
    if response.status_code != 200:
        raise Exception(f"Failed to search for {input.guid()}: {response.text}")

    data = response.json()
    title = data.get("title")
    if title is None:
        raise Exception(f"Invalid search response from server: {response.text}")

    return title


@reactive.calc
def packages_spec():
    if input.guid() == "":
        return
    return get_app_packages(input.guid())

def get_packages(app_packages) -> pd.DataFrame:
    package_strs = []
    for package in app_packages:
        package_str = f'{package["name"]}=={package["version"]}'
        package_strs.append(package_str)
    
    response = stream_packages_info(package_strs)
    for line in response.iter_lines():
        if line:
            try:
                package_data = json.loads(line)
                for package in app_packages:
                    if package_data.get('name') == package.get('name') and package_data.get('version') == package.get('version'):
                        vulns = package_data.get('vulns', [])
                        cves = []
                        for vuln in vulns:
                            cves.append(vuln["id"])
                        available_versions = package_data.get('available_versions', [])
                        package["cves"] = cves
                        package["available_versions"] = ", ".join(available_versions)
                        package["package"] = f"{package.get('name')} {package.get('version')}"

                        # The newest version is always the first
                        # TODO we aren't properly accounting for dev versions and such, need to correctly parse versions
                        package["up_to_date"] = get_up_to_date(package.get('version'), available_versions[0])
                        break

            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")

    print(f"Found {len(app_packages)} packages for content '{content_title()}'")
    return pd.DataFrame(app_packages)

# TODO don't hard code this
def stream_packages_info(names):
    url = "http://ec2-3-84-118-18.compute-1.amazonaws.com/__api__/filter/packages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJwYWNrYWdlbWFuYWdlciIsImp0aSI6IjJmMDQ5MGNmLWE5NTgtNDQzNy1hZGRmLWJhNzQ0MWNhM2NiNiIsImlhdCI6MTczNjQzOTgzMiwiaXNzIjoicGFja2FnZW1hbmFnZXIiLCJzY29wZXMiOnsiZ2xvYmFsIjoiYWRtaW4ifX0.Ptu-FXvBjw5vJQE7xqhAJqcy2i5_-CLQsH1HITpjpYQ"
    }

    data = {
        "names": names,
        "repo": "pypi",
        "snapshot": "latest"
    }

    return requests.post(url, json=data, headers=headers, stream=True)

def get_app_packages(app_guid: str):
    # get the specific version used
    package_response = client.get(
        f'v1/content/{app_guid}/packages'
    )

    if package_response.status_code != 200:
        raise Exception(f'Failed to get packages for {app_guid}: {package_response.text}')

    package_data = package_response.json()
    if package_data is None:
        raise Exception(f"Invalid packages response from server: {package_response.text}")

    return package_data
    

def get_up_to_date(current_version, latest_version):
    if current_version >= latest_version:
        return "✅"
    return "❌"

def prepare_packages_data(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return df
    
    for i, row in df.iterrows():

        df.at[i, "package_link"] = tags.a(
            tags.span("↗", style="font-size: 1.5em"),
            target="_blank",
            href=f"http://ec2-3-84-118-18.compute-1.amazonaws.com/client/#/repos/pypi/packages/overview?search={row['name']}",
        )

        if row.cves:
            vulns = []
            for cve in row.cves:
                link = tags.a(
                    tags.span(cve, style="font-size: 1em"),
                    target="_blank",
                    href=f"https://osv.dev/vulnerability/{cve}"
                )
                vulns.append(link)

            df.at[i, "cves"] = tags.span([
                item if i == 0 else [", ", item] 
                for i, item in enumerate(vulns)
            ])

    columns = {
        "package_link": "Link",
        "name": "Name",
        "version": "Version",
        "cves": "Known Vulnerabilities",
        "up_to_date": "Up to Date",
        "available_versions": "Available Versions at Snapshot",
    }
    df = df[columns.keys()].rename(columns=columns)
    return df


@reactive.calc
def has_selection():
    return len(input.app_grid_selected_rows()) > 0
