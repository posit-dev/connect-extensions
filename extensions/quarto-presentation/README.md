# Quarto: Presentation

## About this example

A reveal.js slide deck built with Quarto that showcases what you can put on a
slide and publish to Connect: formatted prose, syntax-highlighted code,
diagrams, interactive charts, and multi-column or incremental layouts. Use it as
a starting point for any presentation. The sample content carries a light
business flavor (a quarterly revenue readout) that you can swap for your own.

## Who it's for

Anyone who wants presentation slides that are version-controlled and
reproducible, and served from Connect alongside their other content.

## What's inside

The deck (`index.qmd`) is roughly one slide per capability, each linking to its
Quarto docs:

- **What goes on a slide**: an overview of the features, with links.
- **Show your work with code**: a syntax-highlighted code block (Quarto can also
  execute R, Python, and Julia and embed the output).
- **Diagrams**: a Mermaid diagram drawn from text.
- **Interactive charts**: an Observable JS chart with a segment filter, loaded
  from a bundled `data.csv` you can swap out.
- **Layout and reveals**: a multi-column slide with an incremental list.
- **Publish to Connect**: how to render and publish.

## Render and publish

Preview locally with `quarto preview`, render with `quarto render`, then publish
the directory to Connect, where it deploys as static content.

## Learn more

* [Quarto presentations](https://quarto.org/docs/presentations/)
* [reveal.js presentations](https://quarto.org/docs/presentations/revealjs/)
