# Changelog

All notable changes to the Landing Page example will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-25

### Changed

- Rewrote the title (`Static HTML: Landing Page`), description, and README so the example clearly explains the static organization-landing-page pattern and how to customize it. (#404)
- Replaced the placeholder FAQ (off-topic grant-policy boilerplate) with on-topic questions about finding, accessing, and publishing content on Connect, and added "replace this" comments at each customizable spot in `index.html`. (#404)

### Fixed

- Fixed the broken "contact us" link (`href="#"`). (#404)
- Fixed invalid FAQ markup (answer paragraphs were direct children of `<ul>`). (#404)
- Removed `maximum-scale=1.0` from the viewport meta so the page allows pinch-zoom (accessibility). (#404)
