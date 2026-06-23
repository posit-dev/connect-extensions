# Changelog

All notable changes to the Stock API using Flask extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-06-22

### Changed

- Updated `pandas` and loosened the `numpy` pin to a range so the content installs with Python 3.14 wheels on Connect releases that ship Python 3.14, while still running on older Python versions. (#398)

## [1.0.2] - 2026-06-11

### Changed

- Switched from `os.path` to `pathlib` and used f-strings. (#365)

