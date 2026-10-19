source(test_path("..", "..", "R", "content_hub.R"))

# A minimal stand-in for connectapi::get_content() output: only the columns
# hub_items() reads, with owner and tags as list-columns of API records.
fake_content <- function() {
  content <- data.frame(
    name = c("sales", "churn-api", "forecast", "pin-1", "draft"),
    title = c("Quarterly Sales Report", "Churn API", "Forecast App", NA, "Draft"),
    description = c("Revenue by region", NA, "", NA, NA),
    app_mode = c("quarto-static", "python-fastapi", "python-shiny", "static", "shiny"),
    content_category = c(NA, NA, NA, "pin", NA),
    bundle_id = c("1", "2", "3", "4", NA),
    dashboard_url = paste0("https://connect.example.com/connect/#/apps/", 1:5),
    last_deployed_time = as.POSIXct("2026-01-01", tz = "UTC") + (1:5) * 86400
  )
  ada <- list(first_name = "Ada", last_name = "Lovelace", username = "ada")
  content$owner <- list(ada, list(first_name = "", last_name = "", username = "grace"), ada, NULL, ada)
  content$tags <- list(
    list(list(id = "1", name = "Showcase")),
    list(),
    list(list(id = "2", name = "finance"), list(id = "1", name = "showcase")),
    list(),
    list()
  )
  content
}

test_that("content_type() groups app modes into familiar types", {
  expect_equal(
    content_type(
      c("api", "python-fastapi", "shiny", "rmd-shiny", "quarto-shiny", "python-streamlit", "quarto-static", "static", "static", "tensorflow-saved-model", "something-new", NA),
      c(NA, NA, NA, NA, NA, NA, NA, "pin", "plot", NA, NA, NA)
    ),
    c("API", "API", "Application", "Application", "Application", "Application", "Document", "Pin", "Plot", "Model", "Document", "Document")
  )
})

test_that("hub_items() normalizes content and drops never-deployed items", {
  items <- hub_items(fake_content())

  expect_equal(items$title, c("pin-1", "Forecast App", "Churn API", "Quarterly Sales Report"))
  expect_equal(items$owner, c("", "Ada Lovelace", "grace", "Ada Lovelace"))
  expect_equal(items$type, c("Pin", "Application", "API", "Document"))
  expect_equal(items$icon[[1]], "pin-angle")
  expect_equal(items$description[[3]], "")
  expect_equal(items$tags[[2]], c("finance", "showcase"))
  expect_equal(items$tags[[3]], character(0))
  expect_equal(items$tag_ids[[2]], c("2", "1"))
})

test_that("parse_tags() trims, lowercases, and drops empty entries", {
  expect_equal(parse_tags(" Showcase , ,Onboarding,"), c("showcase", "onboarding"))
  expect_equal(parse_tags(""), character(0))
})

test_that("featured_items() matches tags case-insensitively", {
  items <- hub_items(fake_content())
  featured <- featured_items(items, parse_tags("SHOWCASE"))

  expect_equal(featured$heading, "Featured")
  expect_equal(featured$items$title, c("Forecast App", "Quarterly Sales Report"))
})

test_that("featured_items() caps featured content at the most recent", {
  items <- hub_items(fake_content())
  featured <- featured_items(items, "showcase", max_featured = 1)

  expect_equal(featured$items$title, "Forecast App")
})

test_that("featured_items() falls back to recent content", {
  items <- hub_items(fake_content())

  for (featured_tags in list(character(0), "no-such-tag")) {
    featured <- featured_items(items, featured_tags, n = 2)
    expect_equal(featured$heading, "Recently updated")
    expect_equal(featured$items$title, c("pin-1", "Forecast App"))
  }
})

test_that("filter_items() requires every search term, in any order", {
  items <- hub_items(fake_content())

  expect_equal(filter_items(items, "sales quarterly")$title, "Quarterly Sales Report")
  expect_equal(filter_items(items, "REGION")$title, "Quarterly Sales Report")
  expect_equal(filter_items(items, "grace")$title, "Churn API")
  expect_equal(nrow(filter_items(items, "sales churn")), 0)
  expect_equal(nrow(filter_items(items, "")), 4)
})

test_that("filter_items() filters by type and tag", {
  items <- hub_items(fake_content())

  expect_equal(filter_items(items, types = c("API", "Pin"))$title, c("pin-1", "Churn API"))
  expect_equal(filter_items(items, tags = "finance")$title, "Forecast App")
  expect_equal(filter_items(items, "report", types = "API")$title, character(0))
})

test_that("the table escapes content from the API", {
  items <- hub_items(fake_content())
  items$title[[1]] <- "<script>alert(1)</script>"
  items$url[[1]] <- "https://x/\"onmouseover=alert(2)"
  html <- as.character(htmltools::renderTags(content_table(items))$html)

  # The raw title also travels in the widget's JSON data, but only as text,
  # and htmlwidgets escapes its "</" so it can't close the <script> tag.
  expect_false(grepl("<script>alert(1)</script>", html, fixed = TRUE))
  expect_true(grepl("&lt;script&gt;alert(1)&lt;/script&gt;", html, fixed = TRUE))
  expect_true(grepl("https://x/&quot;onmouseover=alert(2)", html, fixed = TRUE))
})

test_that("cards escape content from the API", {
  items <- hub_items(fake_content())
  items$title[[1]] <- "<script>alert(1)</script>"
  html <- as.character(content_card(items[1, , drop = FALSE]))

  expect_false(grepl("<script>", html, fixed = TRUE))
  expect_true(grepl("&lt;script&gt;", html, fixed = TRUE))
})
