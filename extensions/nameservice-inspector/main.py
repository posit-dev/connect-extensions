def main():
    import streamlit as st

    from posit import connect

    client = connect.Client()

    st.subheader("Nameservice Users")
    st.table(client.get("/v1/nameservice/users").json())

    st.subheader("Nameservice Groups")
    st.table(client.get("/v1/nameservice/groups").json())


if __name__ == "__main__":
    main()
