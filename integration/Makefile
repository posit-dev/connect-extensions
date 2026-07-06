# Shell settings
SHELL := /bin/bash

# Python settings
UV ?= uv
# Read UV version from pyproject.toml with more portable command
UV_VERSION ?= $(shell grep 'required-version' pyproject.toml 2>/dev/null | sed -E 's/.*required-version = "([^"]+)".*/\1/' || echo ">=0.6.14")
# uv defaults virtual environment to `$VIRTUAL_ENV` if set; otherwise .venv
VIRTUAL_ENV ?= .venv
UV_LOCK := uv.lock

# with-connect settings
WITH_CONNECT ?= with-connect
LICENSE_FILE ?= ./license.lic

# Extension settings
EXTENSION_NAME ?=

# pytest settings
PYTEST_ARGS ?= "-s"


.DEFAULT_GOAL := latest


.PHONY: \
	$(CONNECT_VERSIONS) \
	all \
	clean \
	dev \
	ensure-lockfile \
	ensure-uv \
	help \
	latest \
	package-extension \
	print-versions


# All versions starting with the first Connect version that fully supports extensions and version matching.
# The `preview` entry maps to the with-connect preview image.
# Note: every extension's minimumConnectVersion must appear in this list (CI validates this).
CONNECT_VERSIONS := \
	preview \
	release \
	2026.06.0 \
	2026.04.1 \
	2026.03.1 \
	2026.02.0 \
	2025.04.0


# Compute the latest pinned version (excludes preview and release)
LATEST_VERSION := $(firstword $(filter-out preview release,$(CONNECT_VERSIONS)))


# Ensure uv.lock file exists and dev dependencies are installed
$(UV_LOCK): dev
	$(UV) lock


# Install dependencies for integration tests
dev: ensure-uv
	$(UV) pip install --upgrade -e .


# Ensure uv.lock file exists
ensure-lockfile:
	@if [ ! -f "$(UV_LOCK)" ]; then \
		echo "Lock file not found, creating it..."; \
		$(UV) lock; \
	fi


# Create virtualenv
$(VIRTUAL_ENV):
	@echo "Creating virtualenv at $(VIRTUAL_ENV)"
	$(UV) venv $(VIRTUAL_ENV)


# Ensure UV and virtualenv are available
ensure-uv:
	@if ! command -v $(UV) >/dev/null; then \
		python -m ensurepip && python -m pip install "uv$(UV_VERSION)"; \
	fi
	@$(MAKE) $(VIRTUAL_ENV)


clean:
	rm -rf logs reports
	find . -type d -empty -delete


# Run test suite for a specific Connect version using with-connect.
$(CONNECT_VERSIONS): %:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
		echo "Error: EXTENSION_NAME is required. Usage: make <version> EXTENSION_NAME=<name>"; \
		exit 1; \
	fi
	mkdir -p reports logs
	$(WITH_CONNECT) --version $* --license $(LICENSE_FILE) \
		-e CONNECT_SERVER_EMAILPROVIDER=None \
		-e CONNECT_APPLICATIONS_PACKAGEAUDITINGENABLED=true \
		-- bash -c '\
			set -o pipefail; \
			cd $(CURDIR) && \
			$(UV) run tests/posit/connect/set_bootstrap_admin_email.py && \
			EXTENSION_NAME=$(EXTENSION_NAME) \
			BUNDLE_BASE_PATH=$(CURDIR)/bundles \
			$(UV) run pytest $$(echo $(PYTEST_ARGS)) \
				--junit-xml=./reports/$*.xml \
			2>&1 | tee ./logs/$*.log'


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


# Show available versions
print-versions:
	@printf "%s\n" $(strip $(CONNECT_VERSIONS))


# Package an extension into a tar.gz file and save it to the integrations bundles folder.
# Usage: make package-extension EXTENSION_NAME=<extension-name>
package-extension:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required."; \
			echo "Usage: make package-extension EXTENSION_NAME=<extension-name>"; \
			exit 1; \
	fi
	@if [ ! -d "../extensions/$(EXTENSION_NAME)" ]; then \
			echo "Error: Extension directory 'extensions/$(EXTENSION_NAME)' does not exist."; \
			echo "Available extensions:"; \
			ls -1 ../extensions/; \
			exit 1; \
	fi
	@mkdir -p ./bundles
	@echo "Packaging extension: $(EXTENSION_NAME)"
	@pushd .. > /dev/null && tar -czf ./integration/bundles/$(EXTENSION_NAME).tar.gz -C ./extensions $(EXTENSION_NAME) && popd > /dev/null
	@echo "Package created: ./bundles/$(EXTENSION_NAME).tar.gz"


# Show help message.
help:
	@echo "Makefile Targets:"
	@echo "  all              Run test suite for all Connect versions (requires EXTENSION_NAME)."
	@echo "  latest           Run test suite for latest Connect version (requires EXTENSION_NAME)."
	@echo "  preview          Run test suite for preview Connect version (requires EXTENSION_NAME)."
	@echo "  <version>        Run test suite for specific Connect version (requires EXTENSION_NAME)."
	@echo "  clean            Clean up the project directory."
	@echo "  print-versions   Show the available Connect versions."
	@echo "  package-extension Package an extension into a tar.gz file."
	@echo "  dev              Install dependencies for development"
	@echo "  help             Show this help message."
	@echo
	@echo "Required Parameters:"
	@echo "  EXTENSION_NAME   Name of the extension directory (e.g., publisher-command-center)"
	@echo
	@echo "Common Usage:"
	@echo "  make <target> EXTENSION_NAME=<name>"
	@echo
	@echo "Prerequisites:"
	@echo "  - with-connect: uv tool install git+https://github.com/posit-dev/with-connect.git"
	@echo "  - A valid Connect license file at ./license.lic"
	@echo
	@echo "Examples:"
	@echo "  # Run tests for specific version:"
	@echo "  make -C ./integration 2026.04.1 \\"
	@echo "    EXTENSION_NAME=publisher-command-center"
	@echo
	@echo "  # Run tests for latest version:"
	@echo "  make -C ./integration latest \\"
	@echo "    EXTENSION_NAME=publisher-command-center"
	@echo
	@echo "Environment Variables:"
	@echo "  WITH_CONNECT  Command to invoke with-connect. Default: with-connect"
	@echo "  LICENSE_FILE  Path to Connect license file. Default: ./license.lic"
	@echo "  EXTENSION_NAME Name of the extension to test. Required."
	@echo "  PYTEST_ARGS   Arguments to pass to pytest. Default: \"-s\""
