# Changelog

All notable changes to the Publisher Command Center extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.8] - 2026-06-09

### Fixed

- Replaced the `token: str | None` type hint with `Optional[str]` so it no longer requires Python 3.10 at runtime, matching the declared `~=3.8` minimum.
