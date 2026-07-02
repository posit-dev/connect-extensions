# Changelog

All notable changes to the Portfolio Dashboard extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.5] - 2026-06-26

### Changed

- Retitled to `R Shiny: Portfolio Dashboard`, rewrote the description and README, and added explanatory comments to `app.R` (the Sortino ratio, the MAR, and the input throttle). (#413)
- Switched the sample data from `returns.rds` to `returns.csv` (columns: date, portfolio, returns), refreshed it through 2025 with both average return and volatility rising across the conservative, balanced, and aggressive tiers and a shared 2022 downturn, and made the portfolio selector read its options from the file, so swapping the data file updates it automatically. (#413)
- Clarified the sidebar input labels to `Minimum Acceptable Rate (MAR)` and `Rolling Window (months)`, and lowered the MAR slider's maximum to a realistic monthly rate (2%). (#413)
- Switched the rolling Sortino series to trailing (right-aligned) windows so each value reads as of its date, and replaced the month-scale range buttons (a leftover from unused daily data) with 1-, 3-, and 5-year ranges suited to the monthly data. (#413)

### Fixed

- Removed the dated 2016 election marker and annotation, the unused `dygraphs` import (and dropped `dygraphs`, `stringi`, `stringr`, and `utf8` from the bundled packages, none of which the app needs), and the dead daily-returns series; added the explicit `ggplot2` import; fixed the hardcoded rolling-window label to follow the window input; and replaced the deprecated `size` aesthetic with `linewidth`. (#413)
- Showed a message instead of a blank Rolling Sortino plot when the start date leaves fewer months than the rolling window. (#413)
- Removed an unused by-hand Sortino calculation, and named the scatterplot colors so up and down months stay correctly colored even when a selection contains only one. (#413)

## [0.0.4] - 2026-06-11

### Changed

- Modernized R code to use the native pipe (`|>`) and consolidated `mutate()` calls. (#365)

