# Shell settings
SHELL := /bin/bash

# Environment settings
ENV ?= dev

# Project settings
PROJECT_NAME := connect-extensions

# Python settings
PYTHON ?= $(shell command -v python || command -v python3)
UV ?= uv
# uv defaults virtual environment to `$VIRTUAL_ENV` if set; otherwise .venv
VIRTUAL_ENV ?= .venv
UV_LOCK := uv.lock

# Docker settings
DOCKER_COMPOSE ?= docker compose
DOCKER_CONNECT_IMAGE ?= rstudio/rstudio-connect
DOCKER_PROJECT_IMAGE_TAG ?= $(PROJECT_NAME):latest
EXTENSION_NAME ?=

# Docker image settings specifically for the preview version
preview_DOCKER_CONNECT_IMAGE := rstudio/rstudio-connect-preview
preview_DOCKER_CONNECT_IMAGE_TAG := dev-jammy-daily

# Connect settings
CONNECT_BOOTSTRAP_SECRETKEY ?= $(shell head -c 32 /dev/random | base64)

# pytest settings
PYTEST_ARGS ?= "-s"


.DEFAULT_GOAL := latest


.PHONY: \
	$(CONNECT_VERSIONS) \
	all \
	build \
	clean \
	down \
	down-% \
	help \
	latest \
	preview \
	print-versions \
	test \
	up \
	up-%


# Versions starting with 2025.03.0 (first Connect version fully supporting extensions and version matching) and newer
CONNECT_VERSIONS := \
	preview \
	2025.03.0


# Compute the latest official release version (excludes preview)
LATEST_VERSION := $(firstword $(filter-out preview,$(CONNECT_VERSIONS)))


# Python dependencies for Connect integration tests
$(UV_LOCK): dev
	$(UV) lock


dev: ensure-uv  ## [py] Install dependencies for Connect integration tests
	$(UV) pip install --upgrade -e .


$(VIRTUAL_ENV):  ## [py] Create virtualenv for Connect integration tests
	@echo "Creating virtualenv at $(VIRTUAL_ENV)"
	@if [ -f "/.dockerenv" ]; then \
		echo "Docker environment detected - creating venv"; \
		rm -rf $(VIRTUAL_ENV); \
		$(PYTHON) -m venv $(VIRTUAL_ENV); \
		echo "Venv created - checking for python3"; \
		if [ ! -f "$(VIRTUAL_ENV)/bin/python3" ]; then \
				echo "Python3 not found in venv, creating symlink"; \
				ln -sf $$(which python) $(VIRTUAL_ENV)/bin/python3; \
		fi; \
		echo "Setting exec permissions"; \
		chmod +x $(VIRTUAL_ENV)/bin/*; \
		echo "Venv contents:"; \
		ls -la $(VIRTUAL_ENV)/bin/; \
	else \
		# Local environments use UV's venv creation
		$(UV) venv $(VIRTUAL_ENV); \
	fi

# Debug Docker environment
debug-env:
	@echo "=== ENVIRONMENT DEBUG INFO ==="; \
	echo "Current directory: $$(pwd)"; \
	echo "Python executable: $$(which python)"; \
	echo "Python version: $$(python --version)"; \
	echo "UV executable: $$(which uv)"; \
	echo "UV version: $$(uv --version 2>&1)"; \
	echo "VIRTUAL_ENV: $(VIRTUAL_ENV)"; \
	echo "Does .venv exist? $$(test -d $(VIRTUAL_ENV) && echo 'YES' || echo 'NO')"; \
	echo "================================"


ensure-uv:  ## [py] Ensure UV and virtualenv are available for Connect integration tests
	@if ! command -v $(UV) >/dev/null; then \
			$(PYTHON) -m ensurepip && $(PYTHON) -m pip install "uv >= 0.4.27"; \
	fi
	
	@echo "=== DEBUG before VENV creation ==="
	@$(MAKE) debug-env
	
	@# Always recreate venv in Docker
	@if [ -f "/.dockerenv" ]; then \
			echo "Docker detected - removing old venv"; \
			rm -rf $(VIRTUAL_ENV); \
	fi
	
	@# Create/update virtual environment without redirection
	@echo "Creating virtual environment without redirection..."
	@$(MAKE) $(VIRTUAL_ENV)
	
	@echo "=== Checking venv Python interpreter ==="
	@if [ -f "$(VIRTUAL_ENV)/bin/python3" ]; then \
			echo "Python3 interpreter exists at $(VIRTUAL_ENV)/bin/python3"; \
			ls -la $(VIRTUAL_ENV)/bin/python3; \
	else \
			echo "ERROR: Python3 interpreter NOT found at $(VIRTUAL_ENV)/bin/python3"; \
			echo "Creating it manually"; \
			mkdir -p $(VIRTUAL_ENV)/bin; \
			ln -sf $$(which python) $(VIRTUAL_ENV)/bin/python3; \
			chmod +x $(VIRTUAL_ENV)/bin/*; \
			ls -la $(VIRTUAL_ENV)/bin/python3; \
	fi
	
	@echo "=== DEBUG after VENV creation ==="
	@$(MAKE) debug-env
	
	@# Only use system UV in Docker to avoid interpreter errors
	@if [ -f "/.dockerenv" ]; then \
			echo "Using system UV in Docker"; \
	else \
			echo "Installing UV in virtualenv"; \
			$(UV) pip install "uv >= 0.4.27" --quiet; \
	fi


docker-deps: ensure-uv  ## [py] Install dependencies in Docker for Connect integration tests
	@if [ -f "/.dockerenv" ] && [ ! -x "$(VIRTUAL_ENV)/bin/python3" ]; then \
		echo "Fixing Python interpreter permissions"; \
		chmod +x $(VIRTUAL_ENV)/bin/python3; \
	fi
	# Sync given the `uv.lock` file
	$(UV) sync --frozen --no-install-project


clean:
	rm -rf logs reports
	find . -type d -empty -delete


# Run test suite for a specific Connect version.
$(CONNECT_VERSIONS): %:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required. Usage: make <version> EXTENSION_NAME=<name>"; \
			exit 1; \
	fi
	# Check if this is the preview version and use special settings
	@if [ "$*" = "preview" ]; then \
			$(MAKE) EXTENSION_NAME=$(EXTENSION_NAME) \
			DOCKER_CONNECT_IMAGE=$(preview_DOCKER_CONNECT_IMAGE) \
			DOCKER_CONNECT_IMAGE_TAG=$(preview_DOCKER_CONNECT_IMAGE_TAG) \
			down-$* up-$*; \
	else \
			$(MAKE) EXTENSION_NAME=$(EXTENSION_NAME) down-$* up-$*; \
	fi


# Run test suite against all Connect versions.
all:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required."; \
			echo "Usage: make all EXTENSION_NAME=<name>"; \
			exit 1; \
	fi
	$(MAKE) EXTENSION_NAME=$(EXTENSION_NAME) $(CONNECT_VERSIONS:%=%)


# Run test suite against latest official Connect release version.
latest:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required."; \
			echo "Usage: make latest EXTENSION_NAME=<name>"; \
			exit 1; \
	fi
	@echo "Running tests with latest version: $(LATEST_VERSION)"
	$(MAKE) $(LATEST_VERSION) EXTENSION_NAME=$(EXTENSION_NAME)

# Build Dockerfile
build: dev
	docker build -t $(DOCKER_PROJECT_IMAGE_TAG) .


# Tear down resources.
down: $(CONNECT_VERSIONS:%=down-%)
down-%: DOCKER_CONNECT_IMAGE_TAG=jammy-$*
down-%: CONNECT_VERSION=$*
down-%:
	# Capture Connect logs before shutdown
	mkdir -p logs
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME)-$(subst .,-,$(CONNECT_VERSION)) logs connect > logs/connect-$(CONNECT_VERSION).log || true

	CONNECT_BOOTSTRAP_SECRETKEY=$(CONNECT_BOOTSTRAP_SECRETKEY) \
	CONNECT_VERSION=$* \
	DOCKER_CONNECT_IMAGE_TAG=$(DOCKER_CONNECT_IMAGE_TAG) \
	DOCKER_CONNECT_IMAGE=$(DOCKER_CONNECT_IMAGE) \
	DOCKER_PROJECT_IMAGE_TAG=$(DOCKER_PROJECT_IMAGE_TAG) \
	PYTEST_ARGS="$(PYTEST_ARGS)" \
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME)-$(subst .,-,$(CONNECT_VERSION)) down -v


# Create, start, and run Docker Compose.
up: $(CONNECT_VERSIONS:%=up-%)
up-%: CONNECT_VERSION=$*
up-%: DOCKER_CONNECT_IMAGE_TAG=jammy-$*
up-%: build
	CONNECT_BOOTSTRAP_SECRETKEY=$(CONNECT_BOOTSTRAP_SECRETKEY) \
	CONNECT_VERSION=$* \
	EXTENSION_NAME=$(EXTENSION_NAME) \
	DOCKER_CONNECT_IMAGE_TAG=$(DOCKER_CONNECT_IMAGE_TAG) \
	DOCKER_CONNECT_IMAGE=$(DOCKER_CONNECT_IMAGE) \
	DOCKER_PROJECT_IMAGE_TAG=$(DOCKER_PROJECT_IMAGE_TAG) \
	PYTEST_ARGS="$(PYTEST_ARGS)" \
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME)-$(subst .,-,$(CONNECT_VERSION)) up -V --abort-on-container-exit --no-build


# Show available versions
print-versions:
	@printf "%s\n" $(strip $(CONNECT_VERSIONS))


# Show help message.
help:
	@echo "Makefile Targets:"
	@echo "  all              Run test suite for all Connect versions (requires EXTENSION_NAME)."
	@echo "  latest           Run test suite for latest Connect version (requires EXTENSION_NAME)."
	@echo "  preview          Run test suite for preview Connect version (requires EXTENSION_NAME)."
	@echo "  <version>        Run test suite for specific version (requires EXTENSION_NAME)."
	@echo "  up               Start Docker Compose for all Connect versions."
	@echo "  down             Tear down Docker resources for all Connect versions."
	@echo "  clean            Clean up the project directory."
	@echo "  print-versions   Show the available Connect versions."
	@echo "  help             Show this help message."
	@echo
	@echo "Required Parameters:"
	@echo "  EXTENSION_NAME   Name of the extension directory (e.g., publisher-command-center)"
	@echo
	@echo "Common Usage:"
	@echo "  make -C ./integration <target> EXTENSION_NAME=<name>"
	@echo
	@echo "Examples:"
	@echo "  # Run tests for specific version:"
	@echo "  make -C ./integration 2025.02.0 \\"
	@echo "    EXTENSION_NAME=publisher-command-center"
	@echo
	@echo "  # Run tests for latest version:"
	@echo "  make -C ./integration latest \\"
	@echo "    EXTENSION_NAME=publisher-command-center"
	@echo
	@echo "Environment Variables:"
	@echo "  DOCKER_COMPOSE           Command to invoke Docker Compose. Default: docker compose"
	@echo "  DOCKER_CONNECT_IMAGE     Docker image name for Connect. Default: rstudio/rstudio-connect"
	@echo "  DOCKER_PROJECT_IMAGE_TAG Docker image name and tag for the project image. Default: $(PROJECT_NAME):latest"
	@echo "  EXTENSION_NAME           Name of the extension to test. Required."
	@echo "  PYTEST_ARGS              Arguments to pass to pytest. Default: \"-s\""


# Run tests. This target is invoked by the Docker compose file.
test:
	mkdir -p logs reports
	set -o pipefail; \
	CONNECT_VERSION=${CONNECT_VERSION} \
	EXTENSION_NAME=${EXTENSION_NAME} \
	CONNECT_API_KEY="$(shell $(UV) run rsconnect bootstrap -i -s http://connect:3939 --raw)" \
	$(UV) run pytest $(PYTEST_ARGS) \
					--junit-xml=./reports/$(CONNECT_VERSION).xml | \
	tee ./logs/$(CONNECT_VERSION).log
