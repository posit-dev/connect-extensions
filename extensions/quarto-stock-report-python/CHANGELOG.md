# Changelog

All notable changes to the Quarto Stock Report using Python extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.6] - 2026-07-24

### Changed

- Pinned the Quarto `project.render` list to `index.qmd` so only the report renders, preventing a sibling `CHANGELOG.md` from rendering as a stray page. (#442)
- Removed `connect-extension.qmd`, a superseded legacy gallery-metadata file that is no longer used. (#442)

## [1.0.5] - 2026-06-15

### Changed

- Constrained the Python runtime requirement to the current major version (`>=3.11` → `~=3.11`). (#376)

## [1.0.4] - 2026-06-10

### Changed

- Updated Python package dependencies, including pandas 3.0 and matplotlib 3.10.

### Fixed

- Updated date parsing and indexing in `index.qmd` for compatibility with pandas 3.0.

## [1.0.3] - 2026-06-08

### Changed

- Reported the daily change as a day-over-day move so the email subject and table agree. (#368)

### Fixed

- Updated report and email text and formatting to reflect a market index rather than a share price (e.g., index points instead of dollars). (#368)
- Keyed the email's date off the latest date in the data rather than today's date. (#368)
- Renamed the summary table's "Avg Volume" column to "Volume" so the most recent day's volume is no longer mislabeled as an average. (#368)

## [1.0.2] - 2026-06-04

### Fixed

- Flipped the price-change indexing so a price increase is no longer reported as "down". (#362)
- Used `tail()` instead of `head()` to show the latest stock prices. (#362)

## [1.0.1] - 2025-05-08

### Added

- Added Quarto version constraints. (#95)

## [1.0.0] - 2025-04-14

### Added

- Initial release.
