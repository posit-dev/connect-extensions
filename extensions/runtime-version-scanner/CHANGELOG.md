# Changelog

All notable changes to the Runtime Version Scanner extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-06-05

### Changed

- Modernized R code to use the native pipe (`|>`) instead of the magrittr pipe (`%>%`), and replaced `sapply()` with `vapply()`/`lapply()` for type-stable and side-effect-only iteration.

## [1.0.1]

### Added

- Added CHANGELOG.md to the repo.
- Reorganized code to use an R package-like structure.

## [1.0.0]

### Added

- Initial release.
