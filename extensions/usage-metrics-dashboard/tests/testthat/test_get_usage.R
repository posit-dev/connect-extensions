test_that("to_iso8601 formats timestamps", {
  timestamp <- as.POSIXct("2023-01-15 14:30:45", tz = "UTC")

  formatted_utc <- to_iso8601(timestamp, tz = "UTC")
  expect_equal(formatted_utc, "2023-01-15T14:30:45+00:00")

  formatted_est <- to_iso8601(timestamp, tz = "EST")
  expect_equal(formatted_est, "2023-01-15T09:30:45-05:00")
})
