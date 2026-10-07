# Snowflake public data explorer

A Shiny for Python dashboard for exploring the free public data available from
the Snowflake Marketplace.

The dashboard integrates an AI powered chat, where anyone viewing it can ask
questions about the data and get back tables and charts. The dashboard doesn't
ask a model to guess at answers. It asks Cortex to write SQL, runs that SQL in
Snowflake, and shows both the result and the query that produced it.

When published to Posit Connect, the dashboard uses a Snowflake OAuth
integration, so your questions run under your Snowflake identity. Data,
compute, and inference all stay inside your Snowflake account.

A simpler example is found in the Snowflake
[LLM dashboard quickstart](https://www.snowflake.com/en/developers/guides/build-an-llm-powered-dashboard-with-posit-connect-and-cortex/)
([repo](https://github.com/posit-dev/snowflake-posit-llm-dashboard-connect-python)).

## Requirements

- Python 3.12 or later, and [uv](https://docs.astral.sh/uv/).
- A Snowflake account with the free public data, available from the Snowflake Marketplace.
- A Snowflake warehouse.
- Snowflake connection credentials.
- Cortex available in the account region.


## Run it

```bash
uv sync
uv run shiny run app.py
```

Snowflake connection credentials resolve automatically. Locally and in
Workbench, your default Snowflake connection is used. On Connect, the OAuth
token of the person viewing is used.

The app first asks for you to choose some tables. Select up to five.

After picking tables, you're presented with the main chat interface, which
starts off by providing some basic information about the tables you selected.
Charts, queries, and results appear inline in the conversation.


## Configuration

The defaults work for the free public data. Override with environment
variables:

| Variable | Default | Notes |
| --- | --- | --- |
| `SNOWFLAKE_ACCOUNT` | — | Supplied by the Snowflake integration on Connect. |
| `SNOWFLAKE_WAREHOUSE` | — | Unset uses the default warehouse for the connection or Snowflake user. |
| `SNOWFLAKE_DEFAULT_CONNECTION_NAME` | from `$SNOWFLAKE_HOME/config.toml` | Names the connection locally and in Workbench. |
| `SNOWFLAKE_CORTEX_MODEL` | `claude-haiku-4-5` | Availability varies by region. |
| `SNOWFLAKE_DATABASE` | `SNOWFLAKE_PUBLIC_DATA_FREE` | |
| `SNOWFLAKE_SCHEMA` | `PUBLIC_DATA_FREE` | |
| `APP_TITLE` | `Snowflake Public Data Explorer` | Change it alongside the database and schema. |


## Deploying to Connect

Publish this application to Connect, then attach a Snowflake OAuth integration
to the content.

Connect needs `git` and outbound network access in order to install packages
for the application.

## Development

```bash
uv sync --group dev
uv run ruff check
uv run ruff format --check
```

Dependencies live in `pyproject.toml`.

Regenerate the `manifest.json` after modifying the application or its
supporting files. The `Makefile` creates the `manifest.json` with an
`extension` field; manual editing is unnecessary.

```bash
make clean
make manifest.json
```
