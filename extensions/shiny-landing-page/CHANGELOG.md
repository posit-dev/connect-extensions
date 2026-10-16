# Changelog

All notable changes to the R Shiny: Custom Landing Page example will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-16

### Added

- Initial release: a custom landing page with a tab for each tag, grouping
  each tab's content into sections by the tags under it, and search within
  each tab. Content is listed with each viewer's own permissions, and each
  tab's content is fetched when the viewer first opens it. `PARENT_TAG`
  chooses which tag's children become the tabs. (#385)
