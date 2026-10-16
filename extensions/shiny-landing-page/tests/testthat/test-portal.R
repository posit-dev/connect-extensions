source(test_path("..", "..", "R", "content_hub.R"))
source(test_path("..", "..", "R", "portal.R"))

# A stand-in for GET /v1/tags: two top-level tags, with Finance and Marketing
# under Departments, Reports under Finance, and a second, unrelated Reports
# tag under Projects.
fake_tags <- function() {
  tag <- function(id, name, parent_id = NULL) list(id = id, name = name, parent_id = parent_id)
  tag_table(list(
    tag("1", "Departments"),
    tag("2", "Projects"),
    tag("3", "Marketing", "1"),
    tag("4", "Finance", "1"),
    tag("5", "Reports", "4"),
    tag("6", "Reports", "2")
  ))
}

# Items with only the columns the tag helpers read.
fake_items <- function(tag_ids) {
  items <- data.frame(title = names(tag_ids))
  items$tag_ids <- unname(tag_ids)
  items
}

test_that("tag_table() marks top-level tags with an NA parent", {
  tags <- fake_tags()
  expect_equal(tags$parent_id[1:3], c(NA, NA, "1"))
})

test_that("child_tags() lists a tag's children, or the top-level tags, by name", {
  tags <- fake_tags()
  expect_equal(child_tags(tags)$name, c("Departments", "Projects"))
  expect_equal(child_tags(tags, "1")$name, c("Finance", "Marketing"))
  expect_equal(nrow(child_tags(tags, "3")), 0)
})

test_that("descendant_ids() finds tags at any depth", {
  tags <- fake_tags()
  expect_setequal(descendant_ids(tags, "1"), c("3", "4", "5"))
  expect_equal(descendant_ids(tags, "5"), character(0))
})

test_that("tag_path() joins names from the top of the tree", {
  tags <- fake_tags()
  expect_equal(tag_path(tags, "5"), "Departments/Finance/Reports")
  expect_equal(tag_path(tags, "1"), "Departments")
})

test_that("find_tag() matches paths or names, ignoring case", {
  tags <- fake_tags()
  expect_equal(find_tag(tags, "departments"), "1")
  expect_equal(find_tag(tags, " Projects/Reports "), "6")
  expect_equal(find_tag(tags, "finance"), "4")
  expect_true(is.na(find_tag(tags, "nope")))
})

test_that("find_tag() prefers the shallowest of several same-named tags", {
  tags <- fake_tags()
  expect_equal(find_tag(tags, "reports"), "6")
})

test_that("tag_query() quotes and escapes the tag name", {
  expect_equal(tag_query("Finance"), 'tag:"Finance"')
  expect_equal(tag_query('say "hi"'), 'tag:"say \\"hi\\""')
  expect_equal(tag_query("back\\slash"), 'tag:"back\\\\slash"')
})

test_that("tab_sections() groups by the tags under the tab, then Other", {
  tags <- fake_tags()
  items <- fake_items(list(
    budget = "5",
    campaign = "3",
    both = c("3", "4"),
    general = "1"
  ))
  sections <- tab_sections(items, tags, "1")

  expect_equal(vapply(sections, `[[`, "", "heading"), c("Finance", "Marketing", "Other"))
  expect_equal(sections[[1]]$items$title, c("budget", "both"))
  expect_equal(sections[[2]]$items$title, c("campaign", "both"))
  expect_equal(sections[[3]]$items$title, "general")
})

test_that("tab_sections() uses one unheaded section when there are no subtags", {
  tags <- fake_tags()
  items <- fake_items(list(budget = "5"))
  sections <- tab_sections(items, tags, "5")

  expect_length(sections, 1)
  expect_null(sections[[1]]$heading)
  expect_equal(sections[[1]]$items$title, "budget")
})
