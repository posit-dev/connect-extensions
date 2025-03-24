include ../vars.mk

# Docker settings
DOCKER_COMPOSE ?= docker compose
DOCKER_CONNECT_IMAGE ?= rstudio/rstudio-connect
DOCKER_PROJECT_IMAGE_TAG ?= $(PROJECT_NAME):latest
EXTENSION_NAME ?=


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


# TODO determine which Connect versions we want to include here, left two so we can test the workflow matrix
# Versions
CONNECT_VERSIONS := \
	preview \
	2025.02.0 \
	2025.01.0 \


clean:
	rm -rf logs reports
	find . -type d -empty -delete


# Run test suite for a specific Connect version.
$(CONNECT_VERSIONS): %:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required. Usage: make <version> EXTENSION_NAME=<name>"; \
			exit 1; \
	fi
	$(MAKE) EXTENSION_NAME=$(EXTENSION_NAME) down-$* up-$*


# Run test suite against all Connect versions.
all:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required."; \
			echo "Usage: make all EXTENSION_NAME=<name>"; \
			exit 1; \
	fi
	$(MAKE) EXTENSION_NAME=$(EXTENSION_NAME) $(CONNECT_VERSIONS:%=%) preview


# Run test suite against latest Connect version.
latest:
	@if [ -z "$(EXTENSION_NAME)" ]; then \
			echo "Error: EXTENSION_NAME is required."; \
			echo "Usage: make latest EXTENSION_NAME=<name>"; \
			exit 1; \
	fi
	$(MAKE) EXTENSION_NAME=$(EXTENSION_NAME) $(firstword $(CONNECT_VERSIONS))


# Run test suite against preview Connect version.
preview:
		@if [ -z "$(EXTENSION_NAME)" ]; then \
						echo "Error: EXTENSION_NAME is required."; \
						echo "Usage: make preview EXTENSION_NAME=<name>"; \
						exit 1; \
		fi
		$(MAKE) \
		EXTENSION_NAME=$(EXTENSION_NAME) \
		DOCKER_CONNECT_IMAGE=rstudio/rstudio-connect-preview \
		DOCKER_CONNECT_IMAGE_TAG=dev-jammy-daily \
		down-preview up-preview


# Build Dockerfile
build:
	make -C .. dev
	docker build -t $(DOCKER_PROJECT_IMAGE_TAG) ..


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
