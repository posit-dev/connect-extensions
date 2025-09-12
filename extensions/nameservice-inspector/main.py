import streamlit as st

from posit import connect

def main():

    client = connect.Client()

    token = st.context.headers.get("Posit-Connect-User-Session-Token")
    if token:
        client = client.with_user_session_token(token)

    st.subheader("Nameservice Users")
    st.table(client.get("/v1/nameservice/users").json())

    st.subheader("Nameservice Groups")
    st.table(client.get("/v1/nameservice/groups").json())


if __name__ == "__main__":
    main()
