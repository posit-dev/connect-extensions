# Contributing to Usage Metrics Dashboard

## Organization

- The app's core code lives in `app.R`.
- Supporting functions live in `R/`.

## Tests

- Run `make test` to run tests.
- Tests live in `tests/testthat`, and run against the code in `R/`.

## Updating the manifest

If updating package versions, update them and call `renv::snapshot()` first.
Then update the manifest:

```r
rsconnect::writeManifest(
  appFiles = c(
    "app.R",
    "R/integrations.R",
    "R/ui_components.R",
    "R/visit_processing.R",
    "README.md",
    "renv.lock",
    "www/styles.css"
  )
)
```

By default rsconnect will adjust the `environment.r.requires` section as well as
the `extension` section. Do not commit these changes, but _do_ manually bump
`extension.version` as well as the `Version` field in the `DESCRIPTION` file.
