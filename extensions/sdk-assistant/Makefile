PYTHON ?= $(shell command -v python || command -v python3)
.DEFAULT_GOAL := help

.PHONY=FORCE
FORCE:

all: _prompt.xml manifest.json FORCE  ## [py] Lazily update the prompt and manifest

install: ensure-uv FORCE ## [py] Install the assistant
	uv pip install --python 3.12 -r requirements.txt

PORT=7000
AUTORELOAD_PORT=7001
shiny: _prompt.xml FORCE ## [py] Run the shiny app
	@$(MAKE) install 1>/dev/null
	uv run --python 3.12 python -m \
		shiny run \
		--port $(PORT) \
		--reload --autoreload-port $(AUTORELOAD_PORT) \
		--launch-browser \
		app.py

app.py:
requirements.txt:
manifest.json: app.py requirements.txt _prompt.xml
	@$(MAKE) manifest
manifest: ensure-uv FORCE ## [py] Write the manifest file for GitHub
	uv run --python 3.12 \
		--with "rsconnect-python >= 1.21.0" \
		rsconnect write-manifest shiny \
		-x "_swagger_prompt.md" \
		-x "custom-prompt-instructions.md" \
		-x "uv_*.py" \
		-x "requirements.txt" \
		-x "Makefile" \
		-x "README.md" \
		-x ".DS_Store" \
		-x "repomix.config.json" \
		-x ".gitignore" \
		-x "chatlas/*" \
		-x "_swagger.json" \
		 --overwrite \
		.

prompt: ensure-uv FORCE ## [py] Update the assistant's system prompt
	uv run --python 3.12 uv_update_prompt.py

test: ensure-uv FORCE ## [py] Test the assistant locally
	uv run --python 3.12 uv_test_chat.py

_prompt.xml: custom-prompt-instructions.md _swagger_prompt.md
	@$(MAKE) prompt

_swagger_prompt.md:
	@$(MAKE) swagger

swagger: ensure-uv FORCE ## [py] Update the Swagger file
	uv run uv_update_swagger.py

# --server https://pub.demo.posit.team/ \
deploy: ensure-uv FORCE  ## [py] Deploy the assistant
	uv run --python 3.12 \
		--with "rsconnect-python >= 1.21.0" \
		rsconnect deploy shiny \
		--server https://connect.posit.it/ \
		--app-id 21ac1399-b840-4356-a35c-bc37d10ef1d8 \
		.

# Do not add a dep on `ensure-uv` to avoid recursive depencencies
.venv:
	uv venv
ensure-uv: FORCE
	@if ! command -v uv >/dev/null; then \
		$(PYTHON) -m ensurepip && $(PYTHON) -m pip install "uv >= 0.5.22"; \
	fi
	@# Install virtual environment (before calling `uv pip install ...`)
	@$(MAKE) .venv 1>/dev/null
	@# Be sure recent uv is installed
	@uv pip install "uv >= 0.4.27" --quiet

help: FORCE  ## Show help messages for make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; { \
		printf "\033[32m%-18s\033[0m", $$1; \
		if ($$2 ~ /^\[docs\]/) { \
			printf "\033[34m[docs]\033[0m%s\n", substr($$2, 7); \
		} else if ($$2 ~ /^\[py\]/) { \
			printf "  \033[33m[py]\033[0m%s\n", substr($$2, 5); \
		} else if ($$2 ~ /^\[ext\]/) { \
			printf " \033[35m[ext]\033[0m%s\n", substr($$2, 6); \
		} else if ($$2 ~ /^\[r\]/) { \
			printf "   \033[31m[r]\033[0m%s\n", substr($$2, 4); \
		} else { \
			printf "       %s\n", $$2; \
		} \
	}'
