# Quarto: Presentation

## About this example

A reveal.js slide deck built with Quarto that showcases what you can put on a
slide and publish to Connect: formatted prose, syntax-highlighted code, diagrams,
interactive charts, and multi-column or incremental layouts. It's for anyone who
wants presentation slides that are version-controlled and reproducible, served
from Connect alongside their other content. The sample content carries a light
business flavor (a quarterly revenue readout) that you can swap for your own.

## How it works

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

## Customize it

Edit `index.qmd` to change the slides, swap the chart's `data.csv` for your own
figures, and replace the placeholder title, author, and footer. Preview your
changes with `quarto preview`.

## Deploy it

Deploy it straight from the Connect Gallery to get a copy running and try it
as-is. To run a customized version, get the
[example source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/quarto-presentation),
make your changes, and publish with
[`quarto publish connect`](https://quarto.org/docs/publishing/rstudio-connect.html)
or a [git-backed deployment](https://docs.posit.co/connect/user/git-backed/);
Connect serves it as static content. Rendering requires Quarto 1.6 or newer.

## Learn more

- [Quarto presentations](https://quarto.org/docs/presentations/)
- [reveal.js presentations](https://quarto.org/docs/presentations/revealjs/)
