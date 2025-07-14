library(httr)
library(jsonlite)

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
  r_versions <- r_versions[r_versions != "3.6"]
  min_ver <- as.character(min(as_ordered_version_factor(r_versions)))
  pad_version(min_ver)
}

parse_py_versions <- function(json_text) {
  releases_table <- fromJSON(json_text)$result$releases
  min_ver <- releases_table |>
    filter(isMaintained) |>
    arrange(releaseDate) |>
    slice(1) |>
    pull(name)
  pad_version(min_ver)
}

get_oldest_supported_r <- function() {
  json_text <- fetch_r_versions()
  parse_r_versions(json_text)
}

get_oldest_supported_py <- function() {
  json_text <- fetch_py_versions()
  parse_py_versions(json_text)
}
