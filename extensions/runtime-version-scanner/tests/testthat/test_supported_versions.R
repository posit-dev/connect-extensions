source("../../supported_versions.R")

test_that("pad_version() handles basic cases", {
  expect_equal(pad_version("4.1.2"), "4.1.2")
  expect_equal(pad_version("4.1"), "4.1.0")
  expect_equal(pad_version("4"), "4.0.0")

  # Doesn't handle more than four parts, which is fine.
  expect_error(pad_version("4.1.2.3"), "4.1.2")
})

# For the "fetch" function, we just want to make sure they make a successful
# request and parse it to a character vector.
test_that("fetch_r_versions() successfully returns text", {
  expect_equal(class(fetch_r_versions()), "character")
})

test_that("fetch_py_versions() successfully returns text", {
  expect_equal(class(fetch_py_versions()), "character")
})

# The parse tests load simplified JSON mocks.
test_that("parse_py_versions() works as expected", {
  py_version_text <- readLines("version_responses/py.json")
  expect_equal(parse_py_versions(py_version_text), "3.9.0")
})

test_that("parse_r_versions() works as expected", {
  r_version_text <- readLines("version_responses/r.json")
  expect_equal(parse_r_versions(r_version_text), "4.1.0")
})
