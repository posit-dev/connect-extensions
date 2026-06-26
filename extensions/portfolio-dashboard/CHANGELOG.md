# Changelog

All notable changes to the Portfolio Dashboard extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.5] - 2026-06-26

### Changed

- Retitled to `R Shiny: Portfolio Dashboard`, rewrote the description and README, and added explanatory comments to `app.R` (the Sortino ratio, the MAR, and the input throttle). (#406)
- Switched the sample data from `returns.rds` to `returns.csv` (columns: date, portfolio, returns), refreshed it through 2025, and made the portfolio selector read its options from the file so you can swap in your own data. (#406)

### Fixed

- Removed the dated 2016 election marker and annotation, the unused `dygraphs` import, and the dead daily-returns series; added the explicit `ggplot2` import; fixed the hardcoded rolling-window label to follow the window input; and replaced the deprecated `size` aesthetic with `linewidth`. (#406)
- Showed a message instead of a blank Rolling Sortino plot when the start date leaves fewer months than the rolling window. (#406)
- Removed an unused by-hand Sortino calculation, and named the scatterplot colors so up and down months stay correctly colored even when a selection contains only one. (#406)

## [0.0.4] - 2026-06-11

### Changed

- Modernized R code to use the native pipe (`|>`) and consolidated `mutate()` calls. (#365)

