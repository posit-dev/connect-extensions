library(connectapi)

# This file contains functions that ultimately will more likely be part of
# connectapi. As such, I'm not using dplyr or pipes here.

NA_datetime_ <- # nolint: object_name_linter
  vctrs::new_datetime(NA_real_, tzone = "UTC")
NA_list_ <- # nolint: object_name_linter
  list(list())

usage_dtype <- tibble::tibble(
  "id" = NA_integer_,
  "user_guid" = NA_character_,
  "content_guid" = NA_character_,
  "timestamp" = NA_datetime_,
  "data" = NA_list_
)

# A rough implementation of how a new firehose usage function would work in
# `connectapi`.
get_usage_firehose <- function(client, from = NULL, to = NULL) {
  usage_raw <- client$GET(
    connectapi:::unversioned_url("instrumentation", "content", "hits"),
    query = list(
      from = from,
      to = to
    )
  )

  # FIXME for connectapi: This is slow, it's where most of the slowness is with
  # the new endpoint.
  usage_parsed <- connectapi:::parse_connectapi_typed(usage_raw, usage_dtype)

  usage_parsed[c("user_guid", "content_guid", "timestamp")]
}

get_usage_legacy <- function(client, from = NULL, to = NULL) {
  shiny_usage <- get_usage_shiny(client, limit = Inf, from = from, to = to)
  shiny_usage_cols <- shiny_usage[c("user_guid", "content_guid")]
  shiny_usage_cols$timestamp <- shiny_usage$started

  static_usage <- get_usage_static(client, limit = Inf, from = from, to = to)
  static_usage_cols <- static_usage[c("user_guid", "content_guid")]
  static_usage_cols$timestamp <- static_usage$time

  bind_rows(shiny_usage_cols, static_usage_cols)
}

get_usage <- function(client, from = NULL, to = NULL) {
  tryCatch(
    {
      print("Trying firehose usage endpoint.")
      get_usage_firehose(client, from, to)
    },
    error = function(e) {
      print("Could not use firehose endpoint; trying legacy usage endpoints.")
      get_usage_legacy(client, from, to)
    }
  )
}
