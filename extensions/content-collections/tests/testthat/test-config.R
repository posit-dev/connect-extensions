test_that("build_config builds manual collection structure", {
  cfg <- build_config(
    title = "My Collection",
    description = "Some desc",
    intro_markdown = "# Hi",
    theme = "warm",
    source_type = "manual",
    guids = c("abc-123", "def-456"),
    tag = ""
  )

  expect_equal(cfg$title, "My Collection")
  expect_equal(cfg$description, "Some desc")
  expect_equal(cfg$intro_markdown, "# Hi")
  expect_equal(cfg$theme, "warm")
  expect_equal(cfg$source_type, "manual")
  expect_equal(cfg$guids, c("abc-123", "def-456"))
  expect_null(cfg$source_tag)
})

test_that("build_config builds tag collection structure (no guids key)", {
  cfg <- build_config(
    title = "Tag Coll",
    description = "",
    intro_markdown = "",
    theme = "minimal",
    source_type = "tag",
    guids = character(0),
    tag = "favorites"
  )

  expect_equal(cfg$source_type, "tag")
  expect_equal(cfg$source_tag, "favorites")
  expect_null(cfg$guids)
})

test_that("make_collection_name uses the marker prefix and a uuid", {
  name <- make_collection_name()
  expect_match(name, "^__content-collection__-[0-9a-fA-F-]{36}$")
})

test_that("parse_config restores defaults for missing fields", {
  parsed <- parse_config(list())
  expect_equal(parsed$title, "")
  expect_equal(parsed$description, "")
  expect_equal(parsed$intro_markdown, "")
  expect_equal(parsed$theme, "minimal")
  expect_equal(parsed$source_type, "manual")
  expect_equal(parsed$source_tag, "")
  expect_equal(parsed$guids, character(0))
})

test_that("parse_config preserves provided values", {
  parsed <- parse_config(list(
    title = "T", description = "D", intro_markdown = "I",
    theme = "bold", source_type = "tag", source_tag = "t1",
    guids = list("a", "b")
  ))
  expect_equal(parsed$title, "T")
  expect_equal(parsed$theme, "bold")
  expect_equal(parsed$source_type, "tag")
  expect_equal(parsed$source_tag, "t1")
  expect_equal(parsed$guids, c("a", "b"))
})

test_that("build_config includes owner_email when provided", {
  cfg <- build_config(title = "T", description = "", intro_markdown = "",
                      theme = "minimal", source_type = "manual",
                      guids = c("g1"), tag = "",
                      owner_email = "alice@example.com")
  expect_equal(cfg$owner_email, "alice@example.com")
})

test_that("build_config defaults owner_email to empty string when missing", {
  cfg <- build_config(title = "T", description = "", intro_markdown = "",
                      theme = "minimal", source_type = "manual",
                      guids = character(0), tag = "")
  expect_equal(cfg$owner_email, "")
})

test_that("parse_config preserves owner_email", {
  parsed <- parse_config(list(owner_email = "alice@example.com"))
  expect_equal(parsed$owner_email, "alice@example.com")
})

test_that("parse_config defaults owner_email to empty string", {
  parsed <- parse_config(list())
  expect_equal(parsed$owner_email, "")
})
