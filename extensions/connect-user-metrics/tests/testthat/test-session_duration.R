box::use(
  testthat[expect_equal, test_that],
)

box::use(
  app/view/session_duration,
)

test_that("min_time is correctly used in session_duration", {
  default_return <- session_duration$default_min_time_list

  min_time <- "00:00:00"
  expect_equal(session_duration$get_min_time(min_time), default_return)

  min_time <- "00:00:-10"
  expect_equal(session_duration$get_min_time(min_time), default_return)

  min_time <- "00:00:10"
  expect_equal(session_duration$get_min_time(min_time), list(number = 10, unit = "seconds"))

  min_time <- "00:00:90"
  expect_equal(session_duration$get_min_time(min_time), list(number = 90, unit = "seconds"))

  min_time <- "00:01:00"
  expect_equal(session_duration$get_min_time(min_time), list(number = 1, unit = "minutes"))

  min_time <- "00:01:20"
  expect_equal(session_duration$get_min_time(min_time), list(number = 80, unit = "seconds"))

  min_time <- "01:01:01"
  expect_equal(session_duration$get_min_time(min_time), list(number = 3661, unit = "seconds"))

  min_time <- "01:01:00"
  expect_equal(session_duration$get_min_time(min_time), list(number = 61, unit = "minutes"))

  min_time <- "01:00:00"
  expect_equal(session_duration$get_min_time(min_time), list(number = 1, unit = "hours"))

  min_time <- "11:00:00"
  expect_equal(session_duration$get_min_time(min_time), list(number = 11, unit = "hours"))

  # wrong formats of string ----
  min_time <- "00:AA:00"
  expect_equal(suppressWarnings(session_duration$get_min_time(min_time)), default_return)

  min_time <- ""
  expect_equal(suppressWarnings(session_duration$get_min_time(min_time)), default_return)

  min_time <- "a,b,c,d,e"
  expect_equal(suppressWarnings(session_duration$get_min_time(min_time)), default_return)

  min_time <- "MY_DATETIME"
  expect_equal(suppressWarnings(session_duration$get_min_time(min_time)), default_return)

  min_time <- "10:20"
  expect_equal(suppressWarnings(session_duration$get_min_time(min_time)), default_return)
})
