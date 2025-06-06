library(connectapi)

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

  usage_raw <- client$GET(
    connectapi:::v1_url("instrumentation", "content", "hits"),
    query = list(
      from = from_timestamp,
      to = to_timestamp
    )
  )
  usage_parsed <- connectapi:::parse_connectapi_typed(usage_raw, usage_dtype)
  usage_parsed[c("user_guid", "content_guid", "timestamp")]
}
