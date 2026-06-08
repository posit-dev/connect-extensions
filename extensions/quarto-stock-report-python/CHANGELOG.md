# Changelog

All notable changes to the Quarto Stock Report using Python extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
