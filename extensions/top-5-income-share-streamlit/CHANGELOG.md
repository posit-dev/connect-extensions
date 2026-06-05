# Changelog

All notable changes to the Top 5% Income Share using Streamlit extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-05

### Changed

- Modernized Python code to use `pathlib` instead of `os.path`.
- Read the data file via the resolved absolute path (the computed `DATA` path was previously unused in favor of a fragile relative path).
- Simplified redundant split string literals in the title and description.
