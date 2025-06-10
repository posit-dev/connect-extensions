box::use(
  connectapi[get_content, get_usage_shiny, get_users],
  dplyr,
  lubridate,
  magrittr[`%>%`],
  purrr,
  rlang,
  utils[write.table],
)

#' Check if x is a non trivial string
#' @details Returns FALSE if `x` is NULL, NA or a zero-length character.
#'  This function is used when splitting the GUIDs: we don't want
#'  NULLs, NAs or trivial strings appearing in the filters.
#'
#'  Important: this function accepts only vectors of length 1, which is fine:
#'  it was made to be used only inside a `purrr::map`
#' @export
is_non_trivial_string <- function(x) {
  !rlang$is_empty(x) && !rlang$is_na(x) && nzchar(x)
}

#' Split GUIDs string into a vector
#' @param guids Comma-separated string of GUIDs
#' @return Vector of GUIDs
#' @export
split_guids <- function(guids) {
  if (is.na(guids)) {
    return(NULL)
  }

  splitted_guids <- strsplit(guids, ",", fixed = TRUE)[[1]]

  clean_guids <- purrr$keep(splitted_guids, is_non_trivial_string)

  if (rlang$is_empty(clean_guids)) {
    return(NULL)
  }

  clean_guids
}

#' Given a client, what is the most recent date of activity in a Shiny app?
#' @param client Connect API client
#' @return A date (today, if none found)
#' @export
get_latest_date_from_client <- function(client, guids = NULL) {
  # get the most recent start date
  latest_date_from_client <-
    get_usage_shiny(
      client, limit = 1, asc_order = FALSE, content_guid = guids
    )$started[1]

  # if somehow can't find the latest usage, return today
  if (rlang$is_empty(latest_date_from_client) || rlang$is_na(latest_date_from_client)) {
    return(lubridate$today())
  }

  lubridate$as_date(latest_date_from_client)
}

#' Get usage data from a client
#' @param client Connect API client
#' @param from,to Date to filter start and end of data
#' @param guids Optional: filter results by content GUID
#' @export
get_usage_from_client <- function(client, from = NULL, to = NULL, guids = NULL) {
  usage <- get_usage_shiny(
    client,
    limit = Inf, content_guid = guids, from = from, to = to
  )

  usage
}

#' Get apps data from a client
#' @param client Connect API client
#' @param guids Optional: filter results by content GUID
#' @export
get_apps_from_client <- function(client, guids = NULL) {
  apps <-
    get_content(client, owner_guid = client$me()$guid) |>
    dplyr$mutate(title = dplyr$case_when(
      is.na(title) ~ name,
      TRUE ~ title
    ))

  if (!rlang$is_empty(guids)) {
    apps <- apps %>%
      dplyr$filter(guid %in% guids)
  }

  apps
}

#' Get users data from a client
#' @param client Connect API client
#' @export
get_users_from_client <- function(client) {
  users <- get_users(client, page_size = Inf, limit = Inf)

  users
}

#' Write data frame to CSV
#' @param data Data frame to write
#' @param file Output file path
#' @export
write_csv <- function(data, file) {
  write.table(data, file, sep = ",", na = "", row.names = FALSE)
}
