# Changelog

All notable changes to the Quarto Stock Report using R extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-06-08

### Changed

- Reported the index direction as a day-over-day change so the summary, email subject, and email table all agree. (#368)

### Fixed

- Updated report and email text and number formatting to reflect a market index rather than a share price (e.g., index points instead of currency, cached data instead of a live API). (#368)
- Keyed the report's dates off the latest date in the data rather than the render date. (#368)

## [1.0.1] - 2026-06-04

### Fixed

- Rendered the email subject by removing a stray `#` that commented it out. (#362)
- Updated the stale "Tesla" chart label to GSPC. (#362)

## [1.0.0] - 2025-05-23

### Added

- Initial release.
