# Makefile for Content Health Monitor

# Default target
.PHONY: all
all: setup test

# Setup the virtual environment with dependencies
.PHONY: setup
setup:
	@echo "Setting up virtual environment and installing dependencies..."
	pip install uv
	uv venv
	uv pip install -r requirements.txt
	uv pip install pytest rsconnect-python

# Run all tests
.PHONY: test
test:
	@echo "Running all tests..."
	uv run pytest -v

# Run unit tests only
.PHONY: test-unit
test-unit:
	@echo "Running unit tests..."
	uv run pytest test_content_health_utils.py -v

# Run integration tests only
.PHONY: test-integration
test-integration:
	@echo "Running integration tests..."
	uv run pytest test_integration.py -v

# Clean up - remove virtual environment and cache files
.PHONY: clean
clean:
	@echo "Cleaning up..."
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf *.pyc

# This recipe updates the manifest, with a few helpful modifications:
# - Uses rsconnect-python to generate the manifest
# - Explicitly includes the necessary files in the manifest
# - Copies over `extension` and `environment` blocks from the old manifest to
#   the new one. These are Gallery-specific blocks, and not created by
#   rsconnect-python.
.PHONY: update-manifest
update-manifest:
	cp manifest.json manifest.old.json
	$(eval IMAGE_FILES := $(shell find images -type f | tr '\n' ' '))
	@echo "Including image files: $(IMAGE_FILES)"
	uv run rsconnect write-manifest quarto content-health-monitor.qmd content_health_utils.py $(IMAGE_FILES) --overwrite
	jq -n --slurpfile old manifest.old.json --slurpfile new manifest.json \
		'{"version": $$new[0].version, "locale": $$new[0].locale, "metadata": $$new[0].metadata, "extension": $$old[0].extension, "environment": $$old[0].environment} * ($$new[0] | del(.version, .locale, .metadata))' \
		> manifest.merged.json
	mv manifest.merged.json manifest.json
	rm -f manifest.old.json

# Help command to show available targets
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  setup           - Setup virtual environment and install dependencies"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  clean           - Clean up virtual environment and cache files"
	@echo "  update-manifest - Update manifest.json preserving extension and environment blocks"
	@echo "  help            - Show this help message"
	@echo "  all             - Setup environment and run tests (default)"
