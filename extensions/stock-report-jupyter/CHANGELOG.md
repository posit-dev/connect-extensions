# Changelog

All notable changes to the Stock Report using Jupyter extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-06-10

### Changed

- Updated Python package dependencies, including pandas 3.0 and matplotlib 3.10.

## [1.0.1] - 2026-06-04

### Changed

- Read cached price data from `gspc.csv` instead of the deprecated Quandl WIKI dataset. (#357)
- Report on GSPC (S&P 500) instead of TSLA. (#357)

### Fixed

- Suppressed the stray Axes object text displayed above the price history chart. (#357)
- Renamed the summary table's "Avg Volume" column to "Volume" so the most recent day's volume is no longer mislabeled as an average. (#357)

## [1.0.0] - 2025-05-27

### Added

- Initial release.
