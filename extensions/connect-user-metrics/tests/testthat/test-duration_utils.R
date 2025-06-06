box::use(
  testthat[context, expect_equal, expect_length, test_that],
)

box::use(
  app/logic/duration_utils[format_duration],
)


context("Test duration_utils$format_duration()")

test_that("format_duration returns empty string when passed duration is not valid", {
  expect_equal(format_duration(NA), c(""))
  expect_equal(format_duration(c(NA, NA, NA)), c("", "", ""))
  expect_equal(format_duration(NaN), c(""))
})

test_that("format_duration returns zero length vector when receives zero length vector", {
  expect_equal(format_duration(numeric(0)), character(0))
  expect_equal(format_duration(c()), character(0))
})


test_that("format_duration rounds floating point values", {
  expect_equal(format_duration(10.5), "00:00:10")
  expect_equal(format_duration(10.3), "00:00:10")
  expect_equal(format_duration(10.7), "00:00:11")
})

test_that("format_duration combinations of NaN/NA return empty string at proper positions", {
  input <- c(56, NA, 79, 245, NaN, 90)
  output <- format_duration(input)
  expect_length(output, length(input))
  expect_equal(output[1], "00:00:56")
  expect_equal(output[2], "")
  expect_equal(output[3], "00:01:19")
  expect_equal(output[4], "00:04:05")
  expect_equal(output[5], "")
  expect_equal(output[6], "00:01:30")
})

test_that("format_duration outputs the same legth as input's", {
  for (n in c(1:10, 15, 30, 90, 200, 500)) {
    input <- sample(1:10000, size = n)
    expect_length(format_duration(input), n)
  }
})

test_that("format_duration output proper strings", {
  input <- c(0, 1, 30, 60, 55, 180, 185, 250, 3600, 3620, 4859, 3600 * 24 + 60 * 2 + 55)
  output <- c(
    "00:00:00", "00:00:01", "00:00:30", "00:01:00", "00:00:55", "00:03:00", "00:03:05",
    "00:04:10", "01:00:00", "01:00:20", "01:20:59", "24:02:55"
  )
  expect_equal(format_duration(input), output)
})

test_that("format_duration outputs 00:00:00 for negative numbers", {
  input <- c(-1, -10, -3600)
  output <- rep("00:00:00", length(input))
  expect_equal(format_duration(input), output)
})
