# Changelog

All notable changes to the Publisher Command Center extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.8] - 2026-06-05

### Changed

- Removed an unused `from http import client` import.
- Replaced the `str | None` type annotation with `Optional[str]` so the code honors the declared `~=3.8` Python requirement (the union syntax requires Python 3.10+).
