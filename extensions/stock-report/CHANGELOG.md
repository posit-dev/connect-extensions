# Changelog

All notable changes to the Automated Stock Report extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-04

### Changed

- Read cached price data from `gspc.csv` instead of fetching live from Yahoo Finance on every render. (#357)
- Report on GSPC (S&P 500) instead of TSLA. (#357)

### Fixed

- Corrected the price history chart title, which referred to "Tesla". (#357)
- Improved the email price table's readability by removing the in-cell bars and adding column spacing. (#357)

## [1.0.0] - 2025-06-04

### Added

- Initial release.
