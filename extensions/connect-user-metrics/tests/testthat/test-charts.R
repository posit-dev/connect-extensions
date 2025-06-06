box::use(
  checkmate[expect_data_frame],
  testthat[context, test_that],
)

box::use(
  app/logic/charts,
)

impl <- attr(charts, "namespace")

context("charts date_zero_value_fillter()")

test_that("returns data as is when start date equals to end date", {
  test_data <- data.frame(
    start_date = as.Date(c("2022-10-01")),
    values = 5
  )

  date_range <- as.Date(c("2022-10-01", "2022-10-01")) # 1 day

  result <- impl$date_zero_value_filler(test_data, date_range, "day")

  expect_data_frame(result, nrows = 1)
})

test_that("it fills up by day", {
  test_data <- data.frame(
    start_date = as.Date(c("2022-10-04", "2022-10-11", "2022-10-27")),
    values = c(5, 3, 10)
  )

  date_range <- as.Date(c("2022-10-02", "2022-10-29")) # 28 days

  result <- impl$date_zero_value_filler(test_data, date_range, "day")

  expect_data_frame(result, nrows = 28)
})

test_that("it fills up by week", {
  test_data <- data.frame(
    start_date = as.Date(c("2022-10-03", "2022-10-10", "2022-10-24")),
    values = c(5, 3, 10)
  )

  date_range <- as.Date(c("2022-10-02", "2022-10-29")) # 5 calendar weeks

  result <- impl$date_zero_value_filler(
    test_data,
    date_range,
    "week",
    week_start = 1 # week starts from Monday
  )

  expect_data_frame(result, nrows = 5)
})

test_that("it fills up by month", {
  test_data <- data.frame(
    start_date = as.Date(c("2022-09-01", "2022-11-01", "2022-12-01")),
    values = c(5, 3, 10)
  )

  date_range <- as.Date(c("2022-09-01", "2022-12-01")) # 4 months

  result <- impl$date_zero_value_filler(test_data, date_range, "month")

  expect_data_frame(result, nrows = 4)
})
