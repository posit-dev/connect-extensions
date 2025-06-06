box::use(
  testthat[expect_equal, expect_error, test_that],
)

box::use(
  app/logic/data_utils,
)

test_that("is_non_trivial_string works", {

  # true ones ---
  expect_equal(data_utils$is_non_trivial_string(1), TRUE)

  expect_equal(data_utils$is_non_trivial_string("a"), TRUE)

  expect_equal(data_utils$is_non_trivial_string("abcdef"), TRUE)

  expect_equal(data_utils$is_non_trivial_string(TRUE), TRUE)

  # false ones ----
  expect_equal(data_utils$is_non_trivial_string(""), FALSE)

  expect_equal(data_utils$is_non_trivial_string(NA), FALSE)

  expect_equal(data_utils$is_non_trivial_string(NA_character_), FALSE)

  expect_equal(data_utils$is_non_trivial_string(NULL), FALSE)

  # error ones ----
  # we don't expect vectors of lenght > 1
  expect_error(data_utils$is_non_trivial_string(1:5))
})

test_that("split_guids works", {

  guids <- ""
  expect_equal(data_utils$split_guids(guids), NULL)

  guids <- "a"
  expect_equal(data_utils$split_guids(guids), "a")

  guids <- "a,b"
  expect_equal(data_utils$split_guids(guids), c("a", "b"))

  # we are not trimming whitespaces in the strings
  guids <- "a, b"
  expect_equal(data_utils$split_guids(guids), c("a", " b"))

  guids <- "a,,b"
  expect_equal(data_utils$split_guids(guids), c("a", "b"))

  guids <- ",,b"
  expect_equal(data_utils$split_guids(guids), "b")

  guids <- ",,,,,,"
  expect_equal(data_utils$split_guids(guids), NULL)

  guids <- NA
  expect_equal(data_utils$split_guids(guids), NULL)

  guids <- NA_character_
  expect_equal(data_utils$split_guids(guids), NULL)
})
