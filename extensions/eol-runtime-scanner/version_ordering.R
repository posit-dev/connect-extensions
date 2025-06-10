# Functions to create ordered factors of versions.

# Turns a character vector of version numbers into a factor with levels
# appropriately ordered.
as_ordered_version_factor <- function(versions) {
  sanitized <- sanitize_versions(versions)
  factor(
    sanitized,
    levels = sort_unique_versions(sanitized),
    ordered = TRUE
  )
}


# Sanitize version inputs, because invalid versions cause as.numeric_version() to crash.
sanitize_versions <- function(versions) {
  vapply(
    versions,
    function(v) {
      tryCatch(
        as.character(as.numeric_version(v)),
        error = function(e) NA_character_
      )
    },
    character(1),
    USE.NAMES = FALSE
  )
}

# Takes a character vector of sanitized versions and returns a character vector
# of those versions, unique and sorted by version order.
sort_unique_versions <- function(versions) {
  versions |>
    na.omit() |>
    unique() |>
    as.numeric_version() |>
    sort() |>
    as.character()
}
