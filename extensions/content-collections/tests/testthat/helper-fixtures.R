# Test fixtures and shared helpers. Loaded automatically by testthat.

# Source all helper modules under R/ so test_dir() finds them.
# Path is relative to configurator/ (two levels up from tests/testthat/).
helpers <- list.files(
  file.path(dirname(dirname(getwd())), "R"),
  pattern = "\\.R$",
  full.names = TRUE
)
for (f in helpers) source(f, local = FALSE)

# Build a tarball that resembles a Connect source bundle.
# `files` is a named list: name -> content string. NULL value means skip the file.
make_bundle_tarball <- function(files) {
  staging <- tempfile(); dir.create(staging)
  on.exit(unlink(staging, recursive = TRUE), add = TRUE)
  for (name in names(files)) {
    content <- files[[name]]
    if (is.null(content)) next
    path <- file.path(staging, name)
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    writeLines(content, path)
  }
  tarball <- tempfile(fileext = ".tar.gz")
  old_wd <- setwd(staging); on.exit(setwd(old_wd), add = TRUE)
  utils::tar(tarball, files = ".", compression = "gzip", tar = "internal")
  tarball
}
