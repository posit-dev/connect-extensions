box::use(
  dplyr[arrange, group_by, mutate, summarise],
  echarts4r,
  glue[glue],
  htmlwidgets[JS],
  lubridate[floor_date],
  magrittr[`%>%`],
  timetk[pad_by_time],
)

box::use(
  app/logic/utils,
)

# Sessions ----

#' @title Plots chart for aggregated metrics in a given period grouped by chosen columns by user
#' @param agg_usage tibble with metrics columns avg_duration and `Session count`, varying grouping
#'   columns as in agg_levels parameter, possible content_guid, user_guid, start_date, if
#'   content_guid present also additional dictionary column: title if user_guid present also
#'   additional dictionary column: username
#' @param agg_levels Vector with names of columns for which agg_usage was grouped and metric
#'   columns calculated. utils$MAX_AGG_LEVELS stores current maximal number of columns used for
#'   grouping. Currently used columns for grouping are: c("content_guid", "user_guid",
#'   start_date"). Minimal number of columns used is zero and represented by NULL value of
#'   parameter. This means the maximum aggregation for the whole period.
#' @param date_range date_range[1] <- from date, date_range[2] <- to_date. Used to explicitly
#'   show the period in the title [TODO]
#' @param date_aggregation Used for line charts to fill up zero values for dates without
#'   observations. Acceptable values are "day", "week", "month".
#'
#' @export
plot_session_chart <- function(agg_usage, agg_levels, date_range,
                               date_aggregation,
                               goal_line) {
  if (nrow(agg_usage) > 0) {
    if (is.null(agg_levels)) {
      plot_session_summary_chart(agg_usage, date_range)
    } else {
      if ("start_date" %in% agg_levels) {
        plot_session_line_chart(
          agg_usage, agg_levels, date_range,
          date_aggregation,
          goal_line
        )
      } else {
        plot_session_bar_chart(agg_usage, agg_levels, date_range)
      }
    }
  }
}

#' @title Plot summary bar chart for Session Count and Average Duration metrics
#' @description Plot bar charts of Session Count and Average Duration metrics when there is no
#'   columns in grouping
#'
#' @param agg_usage tibble with metrics columns avg_duration and `Session count`. For Summary chart
#'   we assume no grouping columns
#' @param date_range date_range[1] <- from date, date_range[2] <- to_date. Used to explicitly show
#'   the period in the title [TODO]
#'
#' @return "echarts4r"  "htmlwidget" bar chart object
plot_session_summary_chart <- function(agg_usage, date_range) {
  agg_usage$title <- c("All")
  agg_usage %>%
    mutate(avg_duration = ifelse(is.finite(avg_duration), round(avg_duration / 60), 0)) %>%
    echarts4r$e_charts(x = title, height = "auto") %>%
    echarts4r$e_theme("charts_theme") %>%
    chart_title_helper(
      title = "Total number of sessions and average session duration in minutes for all applications", # nolint: line_length
      date_range = date_range
    ) %>%
    echarts4r$e_bar(serie = `Session count`, barMaxWidth = "30%") %>%
    echarts4r$e_bar(
      serie = avg_duration,
      barMaxWidth = "30%",
      name = "Avg session duration",
      y_index = 1
    ) %>%
    echarts4r$e_y_axis(name = "Minutes", nameLocation = "middle", index = 1, nameGap = 30) %>%
    echarts4r$e_y_axis(
      name = "Count", nameLocation = "middle", index = 0, nameGap = 30,
      splitLine = list(show = FALSE)
    ) %>%
    echarts4r$e_legend(bottom = 0) %>%
    echarts4r$e_tooltip()
}

#' @title Plot line charts for Session Count metric
#' @description Plot line charts of Session Count metric when there is start_date in grouping
#'
#' @param agg_usage tibble with metrics columns avg_duration and `Session count`, varying grouping
#'   columns as in agg_levels parameter, possible content_guid, user_guid, start_date, if
#'   content_guid present also additional dictionary column: title if user_guid present also
#'   additional dictionary column: username
#' @param agg_levels Vector with names of columns for which agg_usage was grouped and metric columns
#'   calculated. utils$MAX_AGG_LEVELS stores current maximal number of columns used for grouping.
#'   Currently used columns for grouping are: c("content_guid", "user_guid", start_date"). For
#'   plotting lines we assume there is start_date column and additional one of two other columns for
#'   series. If only start_date is present or all 3 columns are present one aggregated serie is
#'   presented over the timeline.
#' @param date_range date_range[1] <- from date, date_range[2] <- to_date. Used to explicitly show
#'   the period in the title [TODO]
#' @param date_aggregation Time period ("day", "week", "month") to fill up with zero values for time
#'   periods without observations.
#'
#' @return "echarts4r"  "htmlwidget" bar chart object
plot_session_line_chart <- function(agg_usage, agg_levels,
                                    date_range,
                                    date_aggregation,
                                    goal_line) {
  if (identical(c("content_guid", "start_date"), agg_levels)) {
    agg_usage %>%
      mutate(content_guid = title) %>%
      group_by(title) %>%
      arrange(start_date) %>%
      date_zero_value_filler(date_range, date_aggregation) %>%
      line_chart_helper(
        title = "Number of sessions per interval for chosen applications",
        date_range = date_range,
        goal_line = goal_line
      )
  } else if (identical(c("user_guid", "start_date"), agg_levels)) {
    agg_usage %>%
      mutate(user_guid = username) %>%
      group_by(username) %>%
      arrange(start_date) %>%
      date_zero_value_filler(date_range, date_aggregation) %>%
      line_chart_helper(
        title = "Total number of sessions per interval of selected users",
        date_range = date_range,
        goal_line = goal_line
      )
  } else if (identical(c("start_date"), agg_levels) || length(agg_levels) == utils$MAX_AGG_LEVELS) {
    agg_usage %>%
      group_by(start_date) %>%
      arrange(start_date) %>%
      summarise(`Session count` = sum(`Session count`)) %>%
      date_zero_value_filler(date_range, date_aggregation) %>%
      line_chart_helper(
        title = "Total number of sessions per interval for all applications",
        date_range = date_range,
        goal_line = goal_line
      )
  }
}

#' @title Plot bar charts
#' Plot bar charts for Session Count metric when there is no start_date in grouping
#'
#' @param agg_usage tibble with metrics columns avg_duration and `Session count`, varying grouping
#'   columns as in agg_levels parameter, possible content_guid, user_guid, start_date, if
#'   content_guid present also additional dictionary column: title if user_guid present also
#'   additional dictionary column: username
#' @param agg_levels Vector with names of columns for which agg_usage was grouped and metric columns
#'   calculated. utils$MAX_AGG_LEVELS stores current maximal number of columns used for grouping.
#'   Currently used columns for grouping are: c("content_guid", "user_guid", start_date"). For
#'   plotting bars we assume one or two column grouping but no start_date column.
#' @param date_range date_range[1] <- from date, date_range[2] <- to_date. Used to explicitly show
#'   the period in the title [TODO]
#'
#' @return "echarts4r"  "htmlwidget" bar chart object
plot_session_bar_chart <- function(agg_usage, agg_levels, date_range) {
  if (identical(c("content_guid"), agg_levels)) {
    agg_usage %>%
      bar_chart_helper("title",
        title = "Total number of sessions per application",
        date_range = date_range
      )
  } else if (identical(c("user_guid"), agg_levels)) {
    agg_usage %>%
      bar_chart_helper("username",
        title = "Total number of sessions per user",
        date_range = date_range
      )
  } else if (identical(c("content_guid", "user_guid"), agg_levels)) {
    agg_usage %>%
      group_by(title, username) %>%
      bar_chart_helper("title",
        title = "Total number of sessions per user and application",
        date_range = date_range
      )
  }
}

# Unique Users ----

#' @export
#' Wrapper function to select and plot the unique users line and bar charts
#' @param agg_usage identical to definition in plot_session_line_chart()
#' @param agg_levels identical to definition in plot_session_line_chart()
#' @param date_range identical to definition in plot_session_line_chart()
#' @param date_aggregation identical to definition in plot_session_line_chart()
#'
#' @return "echarts4r"  "htmlwidget" bar chart object
plot_unique_chart <-
  function(agg_usage,
           agg_levels,
           date_range,
           date_aggregation,
           goal_line) {
    if (nrow(agg_usage) > 0) {
      if ("start_date" %in% agg_levels) {
        # Note: When "user_guid" is present in agg_levels, we cannot truly
        # calculate the number of unique users since we cannot aggregate by a
        # variable and show it at the same time. Therefore, for Unique User plots
        # we show generic plots pretending as if User was not selected.

        # Remove User (user_guid) from agg_levels when plotting the Unique Users
        # line chart -- which is virtually the same as the line chart where User
        # was not selected.

        # Combinations:

        # - User, Date
        # - User, Application, Date

        if ("user_guid" %in% agg_levels) {
          agg_levels <- agg_levels[!agg_levels %in% c("user_guid")]
        }

        plot_unique_line_chart(
          agg_usage,
          agg_levels,
          date_range,
          date_aggregation,
          goal_line
        )
      } else {
        # Change agg_levels to Application (content_guid) when only
        # User (user_guid) is selected

        # Combinations:

        # - User

        if (identical(c("user_guid"), agg_levels)) {
          agg_levels <- c("content_guid")
        }

        # Otherwise, plot as it should be plotted

        # Combinations:

        # - Application, User

        plot_unique_bar_chart(agg_usage, agg_levels, date_range)
      }
    }
  }

#' Function to plot the unique users line charts (Date, Application & Date)
#' @param agg_usage identical to definition in plot_session_line_chart()
#' @param agg_levels identical to definition in plot_session_line_chart()
#' @param date_range identical to definition in plot_session_line_chart()
#' @param date_aggregation identical to definition in plot_session_line_chart()
#'
#' @return "echarts4r"  "htmlwidget" bar chart object
plot_unique_line_chart <- function(agg_usage,
                                   agg_levels,
                                   date_range,
                                   date_aggregation,
                                   goal_line) {
  if ("Unique users" %in% colnames(agg_usage)) {
    if (identical(c("content_guid", "start_date"), agg_levels)) {
      agg_usage %>%
        mutate(content_guid = title) %>%
        group_by(title, start_date) %>%
        summarise(`Unique users` = sum(`Unique users`)) %>%
        arrange(start_date) %>%
        date_zero_value_filler(date_range, date_aggregation) %>%
        line_chart_helper(
          title = "Number of unique users per interval for chosen applications",
          date_range = date_range,
          goal_line = goal_line,
          unique = TRUE,
          disclaimer = TRUE
        )
    } else if (identical(c("start_date"), agg_levels) || length(agg_levels) == utils$MAX_AGG_LEVELS) { # nolint: line_length
      agg_usage %>%
        group_by(start_date) %>%
        summarise(`Unique users` = sum(`Unique users`)) %>%
        arrange(start_date) %>%
        date_zero_value_filler(date_range, date_aggregation) %>%
        line_chart_helper(
          title = "Total number of unique users per interval for all applications",
          date_range = date_range,
          goal_line = goal_line,
          unique = TRUE,
          disclaimer = TRUE
        )
    }
  }
}

#' Function to plot the unique users bar chart (Application)
#' @param agg_usage identical to definition in plot_session_line_chart()
#' @param agg_levels identical to definition in plot_session_line_chart()
#' @param date_range identical to definition in plot_session_line_chart()
#'
#' @return "echarts4r"  "htmlwidget" bar chart object
plot_unique_bar_chart <- function(agg_usage, agg_levels, date_range) {
  if (any(c("content_guid", "user_guid") %in% agg_levels)) {
    agg_usage %>%
      mutate(content_guid = title) %>%
      group_by(title) %>%
      summarise(`Unique users` = sum(`Unique users`)) %>%
      bar_chart_helper("title",
        title = "Total number of unique users per application",
        date_range = date_range,
        unique = TRUE,
        disclaimer = TRUE
      )
  }
}

# Helpers ----

chart_title_helper <- function(obj, title, date_range, disclaimer = FALSE) {
  subtext <- glue("Period of {date_range[1]} - {date_range[2]}")

  if (disclaimer) {
    subtext <- paste0(
      subtext,
      " | Note: The plot always assumes User is not selected"
    )
  }

  echarts4r$e_title(
    obj,
    text = title,
    textStyle = list(
      overflow = "break",
      width = 600
    ),
    subtextStyle = list(fontSize = 14)
  )
}

line_chart_helper <- function(obj, title,
                              date_range,
                              goal_line,
                              unique = FALSE,
                              disclaimer = FALSE) {
  plot <- echarts4r$e_charts(obj, start_date) %>%
    echarts4r$e_theme("charts_theme") %>%
    chart_title_helper(
      title = title,
      date_range = date_range,
      disclaimer = disclaimer
    )

  if (unique == TRUE) {
    plot <- plot %>%
      echarts4r$e_line(serie = `Unique users`)

    if (!is.null(goal_line)) {
      if (max(obj$`Unique users`) < goal_line) {
        plot <- plot %>%
          # -1 rounds it to the nearest 10
          echarts4r$e_y_axis(max = round(goal_line + 10, -1))
      }
    }
  } else {
    plot <- plot %>%
      echarts4r$e_line(serie = `Session count`)

    if (!is.null(goal_line)) {
      if (max(obj$`Session count`) < goal_line) {
        plot <- plot %>%
          # -1 rounds it to the nearest 10
          echarts4r$e_y_axis(max = round(goal_line + 10, -1))
      }
    }
  }

  if (!is.null(goal_line)) {
    line_coords <- list(
      xAxis = max(obj$start_date),
      yAxis = goal_line
    )
    plot <- plot %>%
      echarts4r$e_mark_line(
        data = line_coords,
        itemStyle = list(color = "#ff364a"),
        title = "GOAL",
        symbol = "none"
      )
  }
  plot %>%
    echarts4r$e_x_axis(
      type = "category",
      axisLabel = list(
        # Change format to YYYY/MM/DD
        formatter = JS("function(value) { return value.replace(/-/g, '/'); }")
      )
    ) %>%
    echarts4r$e_legend(top = "bottom") %>%
    echarts4r$e_tooltip(trigger = "axis")
}

bar_chart_helper <- function(obj, x, title, date_range,
                             unique = FALSE,
                             disclaimer = FALSE) {
  plot <- obj %>%
    echarts4r$e_charts_(x = x) %>%
    echarts4r$e_theme("charts_theme") %>%
    chart_title_helper(
      title = title,
      date_range = date_range,
      disclaimer = disclaimer
    )

  if (unique == TRUE) {
    plot <- plot %>%
      echarts4r$e_bar(serie = `Unique users`)
  } else {
    if ("username" %in% colnames(obj)) {
      plot <- plot %>%
        echarts4r$e_bar(serie = `Session count`, username)
    } else {
      plot <- plot %>%
        echarts4r$e_bar(serie = `Session count`)
    }
  }

  plot <- plot %>%
    echarts4r$e_legend(top = "bottom") %>%
    echarts4r$e_tooltip()
}

date_zero_value_filler <- function(
  agg_usage,
  date_range,
  date_aggregation,
  week_start = utils$week_start_id
) {
  if (nrow(agg_usage) == 0) {
    return(agg_usage)
  }

  start_date <- floor_date(date_range[1], date_aggregation, week_start)

  end_date <- date_range[2]

  if (start_date == end_date) {
    return(agg_usage)
  }

  agg_usage %>%
    pad_by_time(
      "start_date",
      .by = date_aggregation,
      .pad_value = 0,
      .start_date = start_date,
      .end_date = end_date
    )
}
