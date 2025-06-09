source("../version_ordering.R")

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
  expect_error(sort_unique_versions(versions))
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

  # Comparisons work as expected
  expect_true(
    all(c(
      vf[1] > vf[2],
      vf[2] < vf[6],
      vf[6] > vf[11],
      vf[7] > vf[8],
      vf[7] == vf[9]
    ))
  )
})
