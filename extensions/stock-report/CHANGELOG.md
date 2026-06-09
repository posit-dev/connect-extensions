# Changelog

All notable changes to the Automated Stock Report extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-04

### Changed

- Read cached price data from `gspc.csv` instead of fetching live from Yahoo Finance on every render. (#357)
- Report on GSPC (S&P 500) instead of TSLA. (#357)
- Send the summary email when the index moves more than 1%, replacing the previous fixed dollar-amount threshold. (#357)

### Fixed

- Corrected the price history chart title, which referred to "Tesla". (#357)
- Improved the email price table's readability by removing the in-cell bars and adding column spacing. (#357)
- Updated report and email text and number formatting to reflect a market index rather than a share price (e.g., index points instead of currency). (#357)
- Clarified report wording: replaced the confusing "legacy report" note with a description of the downloadable CSV output, and noted that the table's volume is shown in millions. (#357)
- Reported the index direction as a day-over-day change so the summary text and the email agree (the summary previously compared the close to the same day's open). (#357)

## [1.0.0] - 2025-06-04

### Added

- Initial release.
