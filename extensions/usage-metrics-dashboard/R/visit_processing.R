library(dplyr)
library(lubridate)
library(tidyr)

# Removes visits that are within a specified time window of the previous visit
# for the same user and content.
filter_visits_by_time_window <- function(visits, session_window) {
  if (session_window == 0) {
    return(visits)
  } else {
    visits |>
      group_by(content_guid, user_guid) |>
      # Compute time diffs and filter out hits within the session
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > session_window) |>
      ungroup() |>
      select(-time_diff)
  }
}
