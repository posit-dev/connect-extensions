# Content Health Monitor

This report uses the publisher’s API key to monitor a single piece of content. It checks whether the content is 
reachable, but does not validate its functionality. If scheduled to run regularly, it will send an email alert if the 
content becomes unreachable.

# Setup

The following environment variables are required when previewing the report locally.

```bash:
# Required variables
CONNECT_SERVER  # Set automatically when deployed to Connect
CONNECT_API_KEY # Set automatically when deployed to Connect
MONITORED_CONTENT # GUID for the content to monitor
```	

# Usage

Deploy the Content Health Monitor to Connect, then follow the setup instructions, and then refresh (re-render) the report.

## Extending Validation

By default, the monitor only checks HTTP status codes.

For more advanced validation, modify the `validate()` function in `content_health_utils.py`. You can add checks for expected text, specific HTML elements, or any other content validation logic.


# Testing

The Content Health Monitor includes a comprehensive test suite. You can run the tests using the provided Makefile or manually with pytest.

## Using the Makefile

The project includes a Makefile with several targets to simplify common tasks:

```bash
# Setup environment and install dependencies
make setup

# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Update manifest.json (preserves extension and environment blocks)
make update-manifest

# Show help with all available targets
make help

# Clean up virtual environment and cache files
make clean
```
