box::use(
  lubridate[as_date, days],
  testthat[expect_equal, expect_null, test_that],
)

box::use(
  app/logic/utils,
)

impl <- attr(utils, "namespace")

test_that("map_wday gives monday as one", {
  expect_equal(utils$map_wday(c("Monday")), c(1))
})

test_that("map_wday is case insensitive", {
  expect_equal(utils$map_wday(c("Monday", "monday", "mOnDaY")), c(1, 1, 1))
})

test_that("map_wday sets sunday as 7", {
  expect_equal(utils$map_wday(c("Sunday")), c(7))
})

test_that("get_goal_spec works for basic example", {
  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("start_date"),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(test_goal_df, agg_levels = c("start_date"), date_agg = c("day"))
  )
})

test_that("get_goal_spec gives NULL for non existent goals", {
  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("start_date"),
    goal = c("28")
  )
  expect_null(impl$get_goal_spec(test_goal_df, agg_levels = c("start_date"), date_agg = c("week")))
  expect_null(impl$get_goal_spec(test_goal_df, agg_levels = c("content_guid"), date_agg = c("day")))

  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("start_date,content_guid"),
    goal = c("28")
  )
  expect_null(impl$get_goal_spec(test_goal_df, agg_levels = c("start_date"), date_agg = c("day")))
  expect_null(impl$get_goal_spec(test_goal_df, agg_levels = c("content_guid"), date_agg = c("day")))
})

test_that("get_goal_spec captures comma separated lists", {
  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("start_date,content_guid"),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(
      test_goal_df,
      agg_levels = c("start_date", "content_guid"),
      date_agg = c("day")
    )
  )
})

test_that("get_goal_spec avoids whitespace in user input", {
  test_goal_df <- data.frame(
    freq = c("day"),
    per = c(" start_date , content_guid "),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(
      test_goal_df,
      agg_levels = c("start_date", "content_guid"),
      date_agg = c("day")
    )
  )
})

test_that("get_goal_spec is robust to ordering of agg_level in input_df", {
  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("content_guid,start_date"),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(
      test_goal_df,
      agg_levels = c("start_date", "content_guid"),
      date_agg = c("day")
    )
  )

  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("content_guid,start_date,user_guid"),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(
      test_goal_df,
      agg_levels = c("start_date", "content_guid", "user_guid"),
      date_agg = c("day")
    )
  )
})

test_that("get_goal_spec is robust to ordering of agg_level in func args", {
  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("start_date,content_guid"),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(
      test_goal_df,
      agg_levels = c("content_guid", "start_date"),
      date_agg = c("day")
    )
  )

  test_goal_df <- data.frame(
    freq = c("day"),
    per = c("content_guid,start_date,user_guid"),
    goal = c("28")
  )
  expect_equal(
    28,
    impl$get_goal_spec(
      test_goal_df,
      agg_levels = c("start_date", "user_guid", "content_guid"),
      date_agg = c("day")
    )
  )
})

test_that("process_chart_goal handles numeric input", {
  expect_equal(
    42,
    utils$process_chart_goal(42, agg_levels = c("start_date"), date_aggregation = "day")
  )
})

test_that("process_chart_goal handles NULL input", {
  expect_null(
    utils$process_chart_goal(NULL, agg_levels = c("start_date"), date_aggregation = "day")
  )
})

test_that("create_image_path returns image path when image filename is given as an input", {
  image_filename <- "image.jpeg"

  expect_equal(
    as.character(utils$create_image_path(image_filename)),
    "static/images/image.jpeg"
  )
})

test_that("create_image_path returns image path when image is located in sub-folder", {
  image_filename <- "test/image.jpeg"

  expect_equal(
    as.character(utils$create_image_path(image_filename)),
    "static/images/test/image.jpeg"
  )
})

test_that("get_app_titles returns app titles if they exist", {
  apps <- data.frame(
    guid = c("test_guid_1", "test_guid_2", "test_guid_3"),
    name = c("test_name_1", "test_name_2", "test_name_3"),
    title = c("test_title_1", "test_title_2", "test_title_3")
  )

  expect_equal(
    c("test_title_1", "test_title_2", "test_title_3"),
    utils$get_app_titles(apps$guid, apps$title, apps$name)
  )
})

test_that("get_app_titles returns app names instead of NA titles", {
  apps <- data.frame(
    guid = c("test_guid_1", "test_guid_2", "test_guid_3"),
    name = c("test_name_1", "test_name_2", "test_name_3"),
    title = c("test_title_1", NA, "test_title_3")
  )

  expect_equal(
    c("test_title_1", "test_name_2", "test_title_3"),
    utils$get_app_titles(apps$guid, apps$title, apps$name)
  )
})

test_that("get_app_titles returns app names instead of empty titles", {
  apps <- data.frame(
    guid = c("test_guid_1", "test_guid_2", "test_guid_3"),
    name = c("test_name_1", "test_name_2", "test_name_3"),
    title = c("", "test_title_2", "")
  )

  expect_equal(
    c("test_name_1", "test_title_2", "test_name_3"),
    utils$get_app_titles(apps$guid, apps$title, apps$name)
  )
})

test_that("get_app_titles returns guid when both name and title is NA or empty", {
  apps <- data.frame(
    guid = c("test_guid_1", "test_guid_2", "test_guid_3", "test_guid_4", NA),
    name = c("test_name_1", NA, "", "test_name_4", NA),
    title = c("test_title_1", NA, "", "", NA)
  )

  expect_equal(
    c("test_title_1", "test_guid_2", "test_guid_3", "test_name_4", NA),
    utils$get_app_titles(apps$guid, apps$title, apps$name)
  )
})

test_that("get_date_range_length_in_units returns zero when start date is greater than end date", {
  expect_equal(
    0,
    utils$get_date_range_length_in_units(
      start_date = "2025-04-01",
      end_date = "2025-03-01",
      unit = "day"
    )
  )
})

test_that("get_date_range_length_in_units returns difference between two dates in days", {
  expect_equal(
    1,
    utils$get_date_range_length_in_units(
      start_date = "2025-03-01",
      end_date = "2025-03-01",
      unit = "day"
    )
  )

  expect_equal(
    32,
    utils$get_date_range_length_in_units(
      start_date = "2025-03-01",
      end_date = "2025-04-01",
      unit = "day"
    )
  )
})

test_that("get_date_range_length_in_units returns difference between two dates in weeks", {
  week_day_ids <- seq(1:7)
  names(week_day_ids) <- c(
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
  )

  # Check each day in the period of two calendar weeks
  for (i in 0:13) {
    initial_monday <- as_date("2025-03-03")

    expect_equal(
      utils$get_date_range_length_in_units(
        start_date = initial_monday,
        end_date = initial_monday + days(i),
        unit = "week",
        week_start = week_day_ids["Monday"]
      ),
      1 + i %/% 7
    )
  }

  # Check same date range with different week start days
  expect_equal(
    6,
    utils$get_date_range_length_in_units(
      start_date = "2025-03-02", # Sunday
      end_date = "2025-04-01",
      unit = "week",
      week_start = week_day_ids["Monday"]
    )
  )

  expect_equal(
    5,
    utils$get_date_range_length_in_units(
      start_date = "2025-03-02", # Sunday
      end_date = "2025-04-01",
      unit = "week",
      week_start = week_day_ids["Sunday"]
    )
  )
})

test_that("get_date_range_length_in_units returns difference between two dates in months", {
  # Each day in the same month return same length in months
  for (i in 0:30) {
    initial_day <- as_date("2025-03-01")

    expect_equal(
      1,
      utils$get_date_range_length_in_units(
        start_date = initial_day,
        end_date = initial_day + days(i),
        unit = "month"
      )
    )
  }

  # Date range of two calendar months
  expect_equal(
    2,
    utils$get_date_range_length_in_units(
      start_date = "2025-03-01",
      end_date = "2025-04-01",
      unit = "month"
    )
  )
})
