source("../../version_ordering.R")

versions <- c(
  "3.8.2",
  "2.8.9",
  NA,
  "",
  "three",
  "4.0.1",
  "3.11.3",
  "3.11.2",
  "3.11.3",
  "a.b.c",
  "3.12.1"
)

test_that("sanitize_versions replaces malformed versions wth NA", {
  expect_equal(
    sanitize_versions(versions),
    c(
      "3.8.2",
      "2.8.9",
      NA,
      NA,
      NA,
      "4.0.1",
      "3.11.3",
      "3.11.2",
      "3.11.3",
      NA,
      "3.12.1"
    )
  )
})

test_that("sort_unique_versions returns a sorted vector of unique versions", {
  sanitized <- sanitize_versions(versions)
  expect_equal(
    sort_unique_versions(sanitized),
    c("2.8.9", "3.8.2", "3.11.2", "3.11.3", "3.12.1", "4.0.1")
  )

  # The input vector must already be sanitized.
  expect_error(
    sort_unique_versions(versions),
    "invalid version specification ‘’, ‘three’, ‘a.b.c’"
  )
})

test_that("as_ordered_version_factor produces properly ordered versions of character vectors.", {
  vf <- as_ordered_version_factor(versions)

  expect_equal(
    vf,
    structure(
      c(2L, 1L, NA, NA, NA, 6L, 4L, 3L, 4L, NA, 5L),
      levels = c("2.8.9", "3.8.2", "3.11.2", "3.11.3", "3.12.1", "4.0.1"),
      class = c("ordered", "factor")
    )
  )
})

test_that("as_ordered_version_factor includes additional_versions in factor levels", {
  # Test with additional versions that don't exist in the main versions
  additional_vers <- c("3.9.0", "4.1.0")
  vf <- as_ordered_version_factor(versions, additional_vers)

  # Check that levels include both the original versions and the additional ones
  expect_equal(
    levels(vf),
    c("2.8.9", "3.8.2", "3.9.0", "3.11.2", "3.11.3", "3.12.1", "4.0.1", "4.1.0")
  )

  # Check that the original values are assigned the correct factor levels
  expect_equal(
    as.character(vf)[!is.na(vf)],
    c("3.8.2", "2.8.9", "4.0.1", "3.11.3", "3.11.2", "3.11.3", "3.12.1")
  )
})
