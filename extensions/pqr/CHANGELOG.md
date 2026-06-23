# Changelog

All notable changes to the Quarto Document with Python and R extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-06-22

### Fixed

- Pinned `pandas>=2.3.3` so the bundled datasets load without crashing on Connect releases that ship Python 3.14. The previous `pandas==2.3.2` had no Python 3.14 wheel and built from source, producing a broken extension that segfaulted when loading data. (#398)

## [0.1.2] - 2026-06-15

### Changed

- Constrained the Python, Quarto, and R runtime requirements to their current major versions (`>=3.11` → `~=3.11`, `>=1.4` → `~=1.4`, `>=4.3` → `~=4.3`). (#376)

### Fixed

- Corrected a stale manifest checksum; no change to bundled files. (#376)

## [0.1.1] - 2026-06-11

### Changed

- Switched to with-connect for integration tests. (#355)

## [0.1.0] - 2025-09-12

### Added

- Initial release. (#274)
