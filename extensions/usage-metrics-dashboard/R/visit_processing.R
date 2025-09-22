# Removes visits that are within a specified time window of the previous visit
# for the same user and content.
filter_visits_by_time_window <- function(visits, session_window) {
  if (session_window == 0) {
    return(visits)
  } else {
    visits |>
      dplyr::group_by(content_guid, user_guid) |>
      # Compute time diffs and filter out hits within the session
      dplyr::mutate(time_diff = lubridate::seconds(timestamp - dplyr::lag(timestamp, 1))) |>
      tidyr::replace_na(list(time_diff = lubridate::seconds(Inf))) |>
      dplyr::filter(time_diff > session_window) |>
      dplyr::ungroup() |>
      dplyr::select(-time_diff)
  }
}
