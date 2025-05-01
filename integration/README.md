# Integration Tests

This directory contains integration tests for Connect Extensions.

It is primarily designed to be run in CI, but can also be run locally.

## Prerequisites

- [UV package manager](https://docs.astral.sh/uv/getting-started/installation/) with the same version from `[tool.uv]` in `integrations/pyproject.toml`
- Python with the same version in `integrations/pyproject.toml`

## Quick Start

For local testing:
- All instructions are run from the root directory
- Copy a valid Connect license file to `integration/license.lic` making sure the license enables all of the features your content requires, for example API Publishing
- Copy the packaged extension (\*.tar.gz) to `integration/bundles` or create one using `make -C ./integration package-extension EXTENSION_NAME=my-extension`
- Run integration tests against a specific Connect version: `make -C ./integration <connect-version> EXTENSION_NAME=<extension-name>` 
  - `<connect-version>` matches a valid version from CONNECT_VERSIONS in the Makefile 
	- `<extension-name>` matches the base name of your .tar.gz file (without the .tar.gz extension)

Example:

- `make -C ./integration 2025.04.0 EXTENSION_NAME=my-extension`

For detailed commands and examples, run: `make -C ./integration help`
