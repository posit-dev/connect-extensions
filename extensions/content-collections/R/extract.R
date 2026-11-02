# Extract collection.json from a Connect bundle tarball (a .tar.gz).
# Returns a list parsed from JSON, or NULL if the file is absent or unreadable.
extract_collection_json <- function(tarball_path) {
  tryCatch({
    tmp <- tempfile(); dir.create(tmp)
    on.exit(unlink(tmp, recursive = TRUE), add = TRUE)

    contents <- suppressWarnings(utils::untar(tarball_path, list = TRUE))
    if (isTRUE(attr(contents, "status") != 0L)) return(NULL)
    target <- contents[basename(contents) == "collection.json"]
    if (length(target) == 0) return(NULL)

    # Use the first match; bundles should never have more than one.
    utils::untar(tarball_path, files = target[[1]], exdir = tmp)
    extracted <- file.path(tmp, target[[1]])
    if (!file.exists(extracted)) return(NULL)

    jsonlite::fromJSON(extracted, simplifyVector = FALSE)
  }, error = function(e) {
    message("extract_collection_json: ", e$message)
    NULL
  })
}
