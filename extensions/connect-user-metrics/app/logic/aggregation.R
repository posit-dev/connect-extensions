box::use(
  dplyr,
  lubridate[floor_date],
  magrittr[`%>%`],
  stats[setNames],
  tools[toTitleCase],
)

box::use(
  app/logic/utils[
    week_start_day,
    week_start_id
  ],
)

#' Aggregate usage data based on specified levels and time period
#' @param usage Usage data frame
#' @param agg_levels Aggregation levels
#' @param date_aggregation Time period for aggregation
#' @return Aggregated data frame
aggregate_usage <- function(usage, agg_levels, date_aggregation) {
  usage$day <- floor_date(usage$start_date, "day")
  usage$week <- floor_date(usage$start_date, "week",
    week_start = week_start_id
  )
  usage$month <- floor_date(usage$start_date, "month")

  if (date_aggregation == "day") {
    usage$start_date <- usage$start_date
  } else if (date_aggregation == "week") {
    usage$start_date <- usage$week
  } else if (date_aggregation == "month") {
    usage$start_date <- usage$month
  }

  if (!is.null(agg_levels)) {
    usage <- usage %>%
      dplyr$group_by(dplyr$across(dplyr$all_of(agg_levels)))
  }

  user_in_agg_levels <- "user_guid" %in% agg_levels
  if (user_in_agg_levels) {
    usage <- usage %>%
      dplyr$filter(!is.na(user_guid))
  }

  usage %>%
    dplyr$summarise(
      avg_duration = mean(duration, na.rm = TRUE),
      "Session count" = dplyr$n(),
      "Unique users" = dplyr$n_distinct(user_guid)
    ) %>%
    dplyr$ungroup()
}

#' Add metadata to aggregated usage data
#' @param agg_usage Aggregated usage data
#' @param apps Apps data frame
#' @param users Users data frame
#' @param content_guid_present Whether content_guid is in aggregation levels
#' @param user_guid_present Whether user_guid is in aggregation levels
#' @return Aggregated usage data with metadata
add_metadata <- function(agg_usage, apps, users, content_guid_present, user_guid_present) {
  if (content_guid_present) {
    agg_usage <- agg_usage %>%
      dplyr$left_join(apps, by = c("content_guid" = "guid"))
  }
  if (user_guid_present) {
    agg_usage <- agg_usage %>%
      dplyr$left_join(users, by = c("user_guid" = "guid"))
  }
  agg_usage
}

#' Process aggregated usage data
#' @param usage Usage data frame
#' @param agg_levels Vector of aggregation levels
#' @param date_aggregation Date aggregation level
#' @param apps Apps data frame
#' @param users Users data frame
#' @return Aggregated usage data frame
#' @export
process_agg_usage <- function(usage, agg_levels, date_aggregation, apps, users) {
  content_guid_present <- "content_guid" %in% agg_levels
  user_guid_present <- "user_guid" %in% agg_levels

  # If neither content_guid nor user_guid is present, just do basic aggregation
  if (!content_guid_present && !user_guid_present) {
    return(aggregate_usage(usage, agg_levels, date_aggregation))
  }

  # If no start_date in agg_levels and only one of content/user guid,
  # force both to be present
  if (!"start_date" %in% agg_levels && xor(content_guid_present, user_guid_present)) {
    agg_levels <- c("content_guid", "user_guid")
    content_guid_present <- user_guid_present <- TRUE
  }

  # Do the aggregation and add metadata
  agg_usage <- aggregate_usage(usage, agg_levels, date_aggregation)
  add_metadata(agg_usage, apps, users, content_guid_present, user_guid_present)
}

#' Format aggregated usage data for display
#' @param agg_usage Aggregated usage data frame
#' @param date_aggregation Date aggregation level ("week", "month", or "day")
#' @param format_duration Function to format duration values
#' @return Formatted data frame for display
#' @export
format_agg_usage <- function(agg_usage, date_aggregation, format_duration) {
  date_col <- switch(date_aggregation,
    "week" = paste(toTitleCase(week_start_day), "Date"),
    "month" = "Month",
    "Date"
  )

  # Create ordered column mapping
  cols <- c(
    setNames("title", "Application"),
    setNames("username", "Username"),
    setNames("start_date", date_col),
    "Session count",
    "Unique users",
    setNames("avg_duration", "Average session duration")
  )

  agg_usage %>%
    dplyr$mutate(avg_duration = format_duration(avg_duration)) %>%
    dplyr$select(dplyr$any_of(cols))
}
