# Changelog

All notable changes to the Quarto Presentation example will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-06-25

### Changed

- Retitled to `Quarto: Presentation` and rewrote the description and README around the reveal.js slide-deck pattern.
- Reworked the deck into a teaching showcase of what a Quarto slide can hold: an overview with doc links, a syntax-highlighted code block, a Mermaid diagram, an interactive Observable JS chart, a multi-column and incremental-reveal slide, and a publish-to-Connect slide. The sample content carries a light business flavor (a quarterly revenue readout). (#405)
- Loaded the chart from a small bundled `data.csv` you can swap out, instead of Observable's external `olympians` sample dataset. (#405)
- Pinned the Quarto project to render only `index.qmd` so the changelog is not rendered as a stray page, and added explanatory comments. (#405)
