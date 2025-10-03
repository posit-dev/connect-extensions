library(httr)
library(jsonlite)
library(dplyr)

# Functions to fetch the oldest officially-supported versions of R and Python
# from APIs, so we don't have to rely on hard-coded local versions. Hard-coded
# local versions are used as a fallback. We pad to a three-part version for the
# sake of comparison logic.

# https://devguide.python.org/versions/
OLDEST_SUPPORTED_PY_FALLBACK <- "3.9.0"

# https://www.tidyverse.org/blog/2019/04/r-version-support/, https://www.r-project.org/
OLDEST_SUPPORTED_R_FALLBACK <- "4.1.0"

# Pads a version to three parts, e.g. "4.1" -> "4.1.0"
pad_version <- function(x) {
  parts <- strsplit(x, "\\.")[[1]]
  padded <- c(parts, rep("0", 3 - length(parts)))
  paste(padded[1:3], collapse = ".")
}

fetch_r_versions <- function(
  url = "https://packagemanager.posit.co/__api__/status"
) {
  res <- GET(url)
  content(res, as = "text")
}

fetch_py_versions <- function(
  url = "https://endoflife.date/api/v1/products/python/"
) {
  res <- GET(url)
  content(res, as = "text", encoding = "UTF-8")
}

parse_r_versions <- function(json_text) {
  r_versions <- fromJSON(json_text)$r_versions
  # P3M can't stop supporting 3.6 yet due to some institutions continuing to use
  # it, but otherwise follows the tidyverse support window.
  r_versions <- r_versions[r_versions != "3.6"]
  min_ver <- as.character(min(as_ordered_version_factor(r_versions)))
  pad_version(min_ver)
}

parse_py_versions <- function(json_text) {
  releases_table <- fromJSON(json_text)$result$releases
  min_ver <- releases_table |>
    filter(!isEol) |>
    arrange(releaseDate) |>
    slice(1) |>
    pull(name)
  pad_version(min_ver)
}

# Load and parse the oldest supported R if possible, fall back to local if
# unable. Message either way.
get_oldest_supported_r <- function() {
  tryCatch(
    {
      json_text <- fetch_r_versions()
      version <- parse_r_versions(json_text)
      message("Fetched oldest supported R version: ", version)
      version
    },
    error = function(e) {
      message(
        "Failed to fetch oldest supported R version; using fallback: ",
        OLDEST_SUPPORTED_R_FALLBACK
      )
      message("Error: ", e$message)
      OLDEST_SUPPORTED_R_FALLBACK
    }
  )
}

# Load and parse the oldest supported Python if possible, fall back to local if
# unable. Message either way.
get_oldest_supported_py <- function() {
  tryCatch(
    {
      json_text <- fetch_py_versions()
      version <- parse_py_versions(json_text)
      message("Fetched oldest supported Python version: ", version)
      version
    },
    error = function(e) {
      message(
        "Failed to fetch oldest supported Python version; using fallback: ",
        OLDEST_SUPPORTED_PY_FALLBACK
      )
      message("Error: ", e$message)
      OLDEST_SUPPORTED_PY_FALLBACK
    }
  )
}
