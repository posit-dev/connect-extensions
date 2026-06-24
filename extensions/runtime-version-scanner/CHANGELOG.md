# Changelog

All notable changes to the Runtime Version Scanner extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] - 2026-06-23

### Fixed

- Fixed the content table failing to load (and the resulting `map_chr` crash) when scanning content. The content list was being parsed directly off connectapi's R6 objects, which left every column empty; it now parses via `as_tibble()`, and missing owner names fall back to an empty string. (#391)

### Changed

- Removed the extension's reliance on unexported connectapi internals (`connectapi:::unversioned_url()` and `connectapi:::v1_url()`), which could be renamed or removed in a future connectapi release and silently break the scanner. URL construction now uses connectapi's public client methods and base R. (#391)

## [1.0.4] - 2026-06-11

### Changed

- Modernized R code to use the native pipe (`|>`) and replaced `sapply()` with `vapply()`/`lapply()`. (#365)

## [1.0.1]

### Added

- Added CHANGELOG.md to the repo.
- Reorganized code to use an R package-like structure.

## [1.0.0]

### Added

- Initial release.
