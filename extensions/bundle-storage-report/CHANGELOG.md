# Changelog

All notable changes to the Bundle Storage Report extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial version: bundle storage per content item with a pins-only filter,
  CSV export, and bulk bundle retention limits. (#488)
- Support for servers with thousands of content items: parallel, cached,
  background data loading; a capped table with a minimum inactive storage
  filter; and bulk changes to all items matching the filters.
