box::use(
  dplyr[mutate, select, tibble],
  lubridate[as_datetime],
  magrittr[`%>%`],
  testthat[describe, expect_equal, it],
  tools[toTitleCase],
)

box::use(
  app/logic/aggregation[format_agg_usage, process_agg_usage],
  app/logic/utils[week_start_day],
)

describe("process_agg_usage", {
  # Setup test data to match real data structure
  test_usage <- data.frame(
    content_guid = c("app1", "app1", "app1", "app2"),
    user_guid = c("user1", "user1", "user2", "user1"),
    started = as_datetime(c(
      "2024-01-01 10:00:00", "2024-01-01 11:00:00",
      "2024-01-01 12:00:00", "2024-01-02 10:00:00"
    )),
    ended = as_datetime(c(
      "2024-01-01 10:30:00", "2024-01-01 11:30:00",
      "2024-01-01 13:00:00", "2024-01-02 11:00:00"
    )),
    stringsAsFactors = FALSE
  ) %>%
    mutate(
      duration = as.numeric(ended - started, units = "secs"),
      start_date = as.Date(started),
      title = ifelse(content_guid == "app1", "App One", "App Two"),
      username = ifelse(user_guid == "user1", "User One", "User Two")
    )

  test_apps <- data.frame(
    guid = c("app1", "app2"),
    title = c("App One", "App Two"),
    stringsAsFactors = FALSE
  )

  test_users <- data.frame(
    guid = c("user1", "user2"),
    username = c("User One", "User Two"),
    stringsAsFactors = FALSE
  )

  it("aggregates by start_date", {
    result <- process_agg_usage(
      usage = test_usage,
      agg_levels = "start_date",
      date_aggregation = "day",
      apps = test_apps,
      users = test_users
    )

    expect_equal(nrow(result), 2) # One row per date
    expect_equal(as.character(sort(result$start_date)), c("2024-01-01", "2024-01-02"))
    expect_equal(sort(result$`Session count`), c(1, 3)) # 1 session on day 2, 3 on day 1
    expect_equal(sort(result$`Unique users`), c(1, 2)) # 1 user on day 2, 2 users on day 1
    expect_equal(
      sort(result$avg_duration), c(2400, 3600)
    ) # Day 1: avg(1800,1800,3600)=2400, Day 2: 3600
  })

  it("aggregates by content_guid and start_date", {
    result <- process_agg_usage(
      usage = test_usage,
      agg_levels = c("content_guid", "start_date"),
      date_aggregation = "day",
      apps = test_apps,
      users = test_users
    )

    expect_equal(nrow(result), 2) # app1-day1, app2-day2
    expect_equal(sort(result$title), c("App One", "App Two"))
    expect_equal(as.character(sort(unique(result$start_date))), c("2024-01-01", "2024-01-02"))
    expect_equal(sort(result$`Session count`), c(1, 3)) # app2-day2: 1, app1-day1: 3
    expect_equal(sort(result$`Unique users`), c(1, 2)) # app2-day2: 1 user, app1-day1: 2 users
  })

  it("aggregates by content_guid and user_guid", {
    result <- process_agg_usage(
      usage = test_usage,
      agg_levels = c("content_guid", "user_guid"),
      date_aggregation = "day",
      apps = test_apps,
      users = test_users
    )

    expect_equal(nrow(result), 3) # user1-app1, user2-app1, user1-app2
    expect_equal(sort(result$title), c("App One", "App One", "App Two"))
    expect_equal(sort(result$username), c("User One", "User One", "User Two"))
    expect_equal(
      sort(result$`Session count`), c(1, 1, 2)
    ) # user2-app1: 1, user1-app2: 1, user1-app1: 2
  })
})

describe("format_agg_usage", {
  # Setup test data
  test_agg_data <- tibble(
    title = c("App One", "App Two"),
    username = c("User One", "User Two"),
    start_date = as.Date(c("2024-01-01", "2024-01-02")),
    `Session count` = c(3, 1),
    `Unique users` = c(2, 1),
    avg_duration = c(2400, 3600),
    content_guid = c("abc123", "def456")
  )

  mock_format_duration <- function(x) {
    paste(round(x / 60), "minutes")
  }

  it("formats daily aggregation correctly", {
    result <- format_agg_usage(test_agg_data, "day", mock_format_duration)

    expect_equal(
      colnames(result),
      c(
        "Application", "Username", "Date", "Session count",
        "Unique users", "Average session duration"
      )
    )
    expect_equal(
      result$`Average session duration`,
      c("40 minutes", "60 minutes")
    )
  })

  it("formats weekly aggregation correctly", {
    result <- format_agg_usage(test_agg_data, "week", mock_format_duration)

    expect_equal(
      colnames(result),
      c(
        "Application", "Username",
        paste(toTitleCase(week_start_day), "Date"),
        "Session count", "Unique users", "Average session duration"
      )
    )
    expect_equal(
      result$`Average session duration`,
      c("40 minutes", "60 minutes")
    )
  })

  it("formats monthly aggregation correctly", {
    result <- format_agg_usage(test_agg_data, "month", mock_format_duration)
    expect_equal(
      colnames(result),
      c(
        "Application", "Username", "Month", "Session count",
        "Unique users", "Average session duration"
      )
    )
    expect_equal(
      result$`Average session duration`,
      c("40 minutes", "60 minutes")
    )
  })

  it("handles missing username column", {
    data_no_username <- test_agg_data %>%
      select(-username)

    result <- format_agg_usage(data_no_username, "day", mock_format_duration)
    expect_equal(
      colnames(result),
      c(
        "Application", "Date", "Session count",
        "Unique users", "Average session duration"
      )
    )
  })

  it("handles missing title column", {
    data_no_title <- test_agg_data %>%
      select(-title)

    result <- format_agg_usage(data_no_title, "day", mock_format_duration)
    expect_equal(
      colnames(result),
      c(
        "Username", "Date", "Session count",
        "Unique users", "Average session duration"
      )
    )
  })

  it("handles data with only required columns", {
    minimal_data <- tibble(
      start_date = as.Date(c("2024-01-01", "2024-01-02")),
      `Session count` = c(3, 1),
      `Unique users` = c(2, 1),
      avg_duration = c(2400, 3600)
    )

    result <- format_agg_usage(minimal_data, "day", mock_format_duration)
    expect_equal(
      colnames(result),
      c("Date", "Session count", "Unique users", "Average session duration")
    )
  })
})
