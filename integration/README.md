# Integration Tests

This directory contains integration tests for Connect Extensions.

It is primarily designed to be run in CI, but can also be run locally.

## Prerequisites
- [UV package manager](https://docs.astral.sh/uv/getting-started/installation/)
- Python

## Quick Start
1. Use Makefile targets to set up and run tests
2. For local testing:
	- Copy the packaged extension (*.tar.gz) to `integration/bundles`
	- Run: `make <connect-version> EXTENSION_NAME=<extension-name>`
		- `<connect-version>` matches a valid version from CONNECT_VERSIONS in the Makefile 
		- `<extension-name>` matches the base name of your .tar.gz file (without the .tar.gz extension)

Example:
- `make 2025.03.0 EXTENSION_NAME=publisher-command-center`

For detailed commands and examples, run: `make help`
