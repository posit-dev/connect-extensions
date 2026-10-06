NAME ?= snowflake-public-data-explorer
VERSION ?= 0.0.1
CONNECT_VERSION ?= 2026.02.0
TITLE ?= Snowflake Public Data Explorer
DESCRIPTION ?= Explore the free public data in Snowflake by asking questions in plain language. Cortex writes the SQL, Snowflake runs it, and the dashboard shows the result alongside the query that produced it. After installing, associate with your Snowflake integration.
HOMEPAGE ?= https://github.com/posit-dev/connect-extensions/tree/main/extensions/snowflake-public-data-explorer

all: clean manifest.json

clean:
	rm -f manifest.json

# Create a manifest.json for the project then inject the 'extension' field.
manifest.json:
	uvx --from rsconnect-python rsconnect write-manifest pyproject --overwrite "."
	jq \
		'. + {extension: { \
			name: "$(NAME)", \
			version: "$(VERSION)", \
			title: "$(TITLE)",\
			description: "$(DESCRIPTION)", \
			homepage: "$(HOMEPAGE)", \
			minimumConnectVersion: "$(CONNECT_VERSION)", \
			requiredFeatures: ["OAuth Integrations"], \
			category: "example", \
			tags: ["chat", "llm", "python", "shiny", "snowflake"] \
		} }' manifest.json > manifest.json.tmp
	mv manifest.json.tmp manifest.json
