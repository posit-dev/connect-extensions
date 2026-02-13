import os
from itertools import chain

import streamlit as st

from posit import connect

VIEWER_INTEGRATION_GUID = os.environ.get("VIEWER_INTEGRATION_GUID")
ADMIN_INTEGRATION_GUID = os.environ.get("ADMIN_INTEGRATION_GUID")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_data(_viewer_client, _admin_client):
    """Fetch all nameservice and group data."""
    users = _viewer_client.get("/v1/nameservice/users").json()

    suppl_groups_by_user = {}
    for user in users:
        name = user.get("name")
        if name:
            try:
                suppl_groups_by_user[name] = _viewer_client.get(
                    f"/v1/nameservice/supplementary-groups/{name}"
                ).json()
            except Exception:
                suppl_groups_by_user[name] = []

    nameservice_groups = _viewer_client.get("/v1/nameservice/groups").json()
    connect_groups = _admin_client.get("/v1/groups", params={"page_size": 500}).json()

    return users, suppl_groups_by_user, nameservice_groups, connect_groups


def get_client_with_token(base, token, audience, label):
    if not token:
        return base
    try:
        return base.with_user_session_token(token, audience=audience)
    except Exception as e:
        st.error(f"Failed to create {label} client: {e}")
        return base


def main():
    st.title("Nameservice Inspector")

    if st.button("Refresh"):
        st.cache_data.clear()

    base_client = connect.Client()
    token = st.context.headers.get("Posit-Connect-User-Session-Token")

    viewer_client = get_client_with_token(
        base_client, token, VIEWER_INTEGRATION_GUID, "viewer"
    )
    admin_client = get_client_with_token(
        base_client, token, ADMIN_INTEGRATION_GUID, "admin"
    )

    with st.spinner("Fetching data..."):
        users, suppl_groups_by_user, nameservice_groups, connect_groups = (
            fetch_all_data(viewer_client, admin_client)
        )

    users_table = [
        {
            "Username": user.get("name"),
            "POSIX UID": user.get("uid"),
            "POSIX Primary GID": user.get("gid"),
            "POSIX Supplementary Groups": ", ".join(
                str(g.get("gid", ""))
                for g in suppl_groups_by_user.get(user.get("name"), [])
            ),
            "Connect User ID": user.get("user_id"),
        }
        for user in users
    ]

    st.subheader("Nameservice Users")
    st.table(users_table)

    # Primary groups take precedence, then supplementary, then Connect groups
    all_group_sources = chain(
        nameservice_groups,
        *suppl_groups_by_user.values(),
        connect_groups.get("results", []),
    )
    all_groups = {}
    for group in all_group_sources:
        gid = group.get("gid")
        name = group.get("name")
        if gid is not None and gid not in all_groups and name != "rstudio-connect":
            all_groups[gid] = {"Group Name": name, "POSIX GID": gid}

    groups_table = sorted(all_groups.values(), key=lambda g: g["POSIX GID"])

    st.subheader("Nameservice Groups")
    st.table(groups_table)


if __name__ == "__main__":
    main()
