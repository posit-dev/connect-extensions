# Changelog

All notable changes to the Quarto: Content Hub extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-10-16

### Changed

- Rebuilt the Quarto Website example as the Quarto: Content Hub extension, in
  R with connectapi, bslib, and reactable. It replaces the Connect Widgets
  example, which is removed from the gallery. (#385)
- Combined the Featured and All pages into one page: featured content as
  cards, above a table of all content with search, per-column filters, and
  sorting. (#385)
- The hub needs no configuration: it uses the server address and API key
  Connect supplies at render time. (#385)
- Up to 12 tagged items are featured. When `FEATURED_TAGS` is unset or
  matches no content, the six most recently updated items are featured. Tag
  names match case-insensitively. (#385)
- Content that has never been deployed is left out of the hub. (#385)

### Removed

- Removed the About page and the Python dependency. (#385)

## [1.0.2] - 2026-10-15

### Changed

- Pinned the Python package versions in `requirements.txt`, compiled from a
  new `requirements.in`. (#475)

## [1.0.1] - 2026-06-09

### Changed

- Used an f-string and removed a dead comment. (#365)
