NA_datetime_ <- vctrs::new_datetime(NA_real_, tzone = "UTC")
NA_list_ <- list(list())

usage_dtype <- tibble::tibble(
  "id" = NA_integer_,
  "user_guid" = NA_character_,
  "content_guid" = NA_character_,
  "timestamp" = NA_datetime_,
  "data" = NA_list_
)

to_iso8601 <- function(x, tz = "") {
  base::strftime(x, "%Y-%m-%dT%H:%M:%S%z", tz = tz) |>
    base::sub("([+-]\\d{2})(\\d{2})$", "\\1:\\2", x = _)
}

get_usage <- function(client, from = NULL, to = NULL) {
  # Allow us to pass in either dates or specific timestamps.
  if (lubridate::is.Date(from)) {
    from <- base::as.POSIXct(base::paste(from, "00:00:00"), tz = "")
  }
  if (lubridate::is.Date(to)) {
    to <- base::as.POSIXct(base::paste(to, "23:59:59"), tz = "")
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

  # Filter out hits from the Content Health Monitor
  usage_parsed$user_agent <- base::vapply(
    usage_parsed$data,
    function(x) if (!is.null(x$user_agent)) x$user_agent else NA_character_,
    FUN.VALUE = character(1)
  )
  usage_parsed <- dplyr::filter(usage_parsed, !base::grepl("^ContentHealthMonitor/", user_agent))

  usage_parsed[c("user_guid", "content_guid", "timestamp", "user_agent")]
}
