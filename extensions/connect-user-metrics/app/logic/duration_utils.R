box::use(
  lubridate[day, hour, minute, second, seconds_to_period],
)

#' Convert seconds to HH:MM:SS format
#' @param s Vector of seconds
#' @return Vector of formatted duration strings
#' @export
format_duration <- function(s) {
  if (length(s) == 0) return(character(0))

  # vector of periods
  periods <- seconds_to_period(round(s, digits = 0))

  formatted <- sprintf(
    "%02d:%02d:%02d",
    day(periods) * 24 + hour(periods),
    minute(periods),
    second(periods)
  )

  # when negative, set to default
  formatted[s < 0] <- "00:00:00"

  # when NA, return ""
  formatted[is.na(s)] <- ""

  formatted
}
