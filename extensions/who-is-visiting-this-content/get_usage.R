library(connectapi)
library(pins)

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

to_iso8601 <- function(x) {
  strftime(x, "%Y-%m-%dT%H:%M:%S%z") |>
    sub("([+-]\\d{2})(\\d{2})$", "\\1:\\2", x = _)
}

# A rough implementation of how a new firehose usage function would work in
# `connectapi`.
get_usage_firehose <- function(client, from = NULL, to = NULL) {
  usage_raw <- client$GET(
    connectapi:::v1_url("instrumentation", "content", "hits"),
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

get_usage_pin <- function(client, from, to) {
  print(paste("Connect client is authenticated:", client$me()$username))
  allowed_guids <- get_content(client)$guid
  print(paste("Length of `allowed_guids`:", length(allowed_guids)))
  board <- pins::board_connect()
  PIN_NAME <- paste0(board$account, "/", "connect_metrics_usage_last_91_days")
  usage <- pin_read(board, PIN_NAME)
  usage |>
    filter(
      content_guid %in% allowed_guids,
      timestamp >= from,
      timestamp <= to
    )
}

get_usage <- function(client, from = NULL, to = NULL) {
  # Allow us to pass in either dates or specific timestamps.
  if (is.Date(from)) {
    from <- as.POSIXct(paste(from, "00:00:00"), tz = "")
  }
  if (is.Date(to)) {
    to <- as.POSIXct(paste(to, "23:59:59"), tz = "")
  }
  from_timestamp <- to_iso8601(from)
  to_timestamp <- to_iso8601(to)
  tryCatch(
    {
      print("Trying firehose usage endpoint.")
      get_usage_firehose(client, from_timestamp, to_timestamp)
    },
    error = function(e) {
      print("Could not use firehose endpoint; trying to fetch cached data from pin.")
      # get_usage_legacy(client, from_timestamp, to_timestamp)
      get_usage_pin(client, from, to)
    }
  )
}
