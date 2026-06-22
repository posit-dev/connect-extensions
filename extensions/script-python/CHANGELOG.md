# Changelog

All notable changes to the Python Scheduled Data Transformation example will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-06-22

### Changed

- Rewrote the title, description, and README to explain running on a schedule and the email setup, and to show how to adapt the script to your own data. (#392)

### Fixed

- Exported the CSV files without the leading row-index column. (#392)
- Re-pinned `requirements.txt` to a minimal, Python 3.9-compatible set so the example installs on 3.9 servers; the previous `ipykernel` pin required Python 3.10, contradicting the declared `~=3.9` floor. (#392)

### Removed

- Removed the committed `script.quarto_ipynb` build intermediate, which Quarto regenerates on render. (#392)

## [1.0.1] - 2026-06-11

### Changed

- Raised the minimum Python version to 3.9 (`~=3.9`). (#355)

## [1.0.0] - 2025-05-30

### Added

- Initial release.
