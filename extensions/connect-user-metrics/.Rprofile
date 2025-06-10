if (file.exists("renv")) {
  source("renv/activate.R")
} else {
  # The `renv` directory is automatically skipped when deploying with rsconnect.
  message("No 'renv' directory found; renv won't be activated.")
}

# Allow absolute module imports (relative to the app root).
options(box.path = getwd())

if (nzchar(system.file(package = "box.lsp"))) {
  options(
    languageserver.parser_hooks = list(
      "box::use" = box.lsp::box_use_parser
    )
  )
}

options(repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
