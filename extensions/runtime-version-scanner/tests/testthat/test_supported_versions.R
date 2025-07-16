source("../../supported_versions.R")

test_that("pad_version() handles basic cases", {
  expect_equal(pad_version("4.1.2"), "4.1.2")
  expect_equal(pad_version("4.1"), "4.1.0")
  expect_equal(pad_version("4"), "4.0.0")

  # Doesn't handle more than four parts, which is fine.
  expect_error(pad_version("4.1.2.3"))
})

# Test fetching and parsing against mock response.
with_mock_api({
  test_that("get_oldest_supported_r() fetches oldest version from API", {
    expect_message(
      rv <- get_oldest_supported_r(),
      "Fetched oldest supported R version"
    )
    expect_equal(
      rv,
      "4.0.0",
      info = .mockPaths()
    )
  })

  test_that("get_oldest_supported_r() fetches oldest version from API", {
    expect_message(
      pv <- get_oldest_supported_py(),
      "Fetched oldest supported Python version"
    )
    expect_equal(
      pv,
      "3.8.0",
      info = .mockPaths()
    )
  })
})

without_internet({
  test_that("get_oldest_supported_r() falls back without", {
    expect_message(
      rv <- get_oldest_supported_r(),
      "Failed to fetch oldest supported R version; using fallback"
    )
    expect_equal(
      rv,
      "4.1.0"
    )
  })

  test_that("get_oldest_supported_r() falls back without", {
    expect_message(
      pv <- get_oldest_supported_py(),
      "Failed to fetch oldest supported Python version; using fallback"
    )
    expect_equal(
      pv,
      "3.9.0"
    )
  })
})
