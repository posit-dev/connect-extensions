library(connectapi)

# This file contains functions that ultimately will more likely be part of
# connectapi. As such, I'm not using dplyr or pipes here.

NA_datetime_ <- vctrs::new_datetime(NA_real_, tzone = "UTC")
NA_list_ <- list(list())

usage_dtype <- tibble::tibble(
  "id" = NA_integer_,
  "user_guid" = NA_character_,
  "content_guid" = NA_character_,
  "timestamp" = NA_datetime_,
  "data" = NA_list_
)

# A rough implementation of how a new firehose usage function would work in
# `connectapi`.
get_usage_firehose <- function(client) {
  usage_raw <- client$GET(
    connectapi:::unversioned_url("instrumentation", "content", "hits"),
  )

  # FIXME for connectapi: This is slow, it's where most of the slowness is with
  # the new endpoint.
  usage_parsed <- connectapi:::parse_connectapi_typed(usage_raw, usage_dtype)

  usage_parsed[c("user_guid", "content_guid", "timestamp")]
}

get_usage_legacy <- function(client) {
  shiny_usage <- get_usage_shiny(client, limit = Inf)
  shiny_usage_cols <- shiny_usage[c("user_guid", "content_guid")]
  shiny_usage_cols$timestamp <- shiny_usage$started

  static_usage <- get_usage_static(client, limit = Inf)
  static_usage_cols <- static_usage[c("user_guid", "content_guid")]
  static_usage_cols$timestamp <- static_usage$time

  bind_rows(shiny_usage_cols, static_usage_cols)
}

get_usage <- function(client) {
  tryCatch(
    {
      print("Trying firehose usage endpoint.")
      get_usage_firehose(client)
    },
    error = function(e) {
      print("Could not use firehose endpoint; trying legacy usage endpoints.")
      get_usage_legacy(client)
    }
  )
}
