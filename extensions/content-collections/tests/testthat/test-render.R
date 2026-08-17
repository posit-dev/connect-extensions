test_that("THEME_COLORS exposes all six themes with required color keys", {
  expect_setequal(names(THEME_COLORS),
                  c("warm", "cool", "minimal", "fun", "bold", "earth"))
  for (name in names(THEME_COLORS)) {
    t <- THEME_COLORS[[name]]
    expect_true(all(c("label", "bg", "accent", "border", "text") %in% names(t)),
                info = sprintf("theme %s missing keys", name))
  }
})

test_that("build_collection_html returns non-empty HTML with the title", {
  cfg <- list(title = "My Collection", description = "",
              intro_markdown = "", theme = "minimal",
              source_type = "manual", guids = character(0))
  html <- build_collection_html(cfg, items = list(), theme_colors = THEME_COLORS)
  expect_type(html, "character")
  expect_gt(nchar(html), 100)
  expect_match(html, "My Collection", fixed = TRUE)
})

test_that("build_collection_html escapes HTML in the title", {
  cfg <- list(title = "<script>alert(1)</script>", description = "",
              intro_markdown = "", theme = "minimal",
              source_type = "manual", guids = character(0))
  html <- build_collection_html(cfg, items = list(), theme_colors = THEME_COLORS)
  expect_no_match(html, "<script>alert", fixed = TRUE)
  expect_match(html, "&lt;script&gt;", fixed = TRUE)
})

test_that("build_collection_html renders one card per item", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual",
              guids = c("a", "b"))
  items <- list(
    list(guid = "a", title = "Alpha", description = "first item",
         app_mode = "shiny", last_deployed_time = "2026-01-01T00:00:00Z"),
    list(guid = "b", title = "Beta",  description = "second item",
         app_mode = "quarto-static", last_deployed_time = "2026-02-02T00:00:00Z")
  )
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS)
  expect_match(html, "Alpha", fixed = TRUE)
  expect_match(html, "Beta",  fixed = TRUE)
  expect_match(html, "2 item", fixed = TRUE)
})

test_that("build_collection_html renders intro markdown when present", {
  cfg <- list(title = "T", description = "", intro_markdown = "# Hello\n\nWorld",
              theme = "minimal", source_type = "manual", guids = character(0))
  html <- build_collection_html(cfg, items = list(), theme_colors = THEME_COLORS)
  expect_match(html, "<h1", fixed = TRUE)
  expect_match(html, "Hello", fixed = TRUE)
})

test_that("build_collection_html renders an icon image per card from app_mode", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual",
              guids = c("a"))
  items <- list(
    list(guid = "a", title = "Q", description = "",
         app_mode = "quarto-static", last_deployed_time = "2026-01-01T00:00:00Z")
  )
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS)
  expect_match(html, 'class="collection-card__icon"', fixed = TRUE)
  # Without a connect_server, the primary src is the icon's data URI.
  expect_match(html, "data:image/svg+xml;base64,", fixed = TRUE)
})

test_that("build_collection_html uses Connect's __thumbnail__ URL when connect_server is given", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual",
              guids = c("a"))
  items <- list(
    list(guid = "a", title = "Q", description = "",
         app_mode = "quarto-static", last_deployed_time = "2026-01-01T00:00:00Z")
  )
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS,
                                 connect_server = "https://connect.example.com")
  expect_match(html,
    'src="https://connect.example.com/content/a/__thumbnail__"',
    fixed = TRUE)
  # onerror falls back to the icon data URI so the deployed embed-resources
  # HTML still has a working fallback when the thumbnail 404s.
  expect_match(html, "onerror=", fixed = TRUE)
  expect_match(html, "data:image/svg+xml;base64,", fixed = TRUE)
})

test_that("build_collection_html strips a trailing slash from connect_server in the thumbnail URL", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual", guids = c("a"))
  items <- list(list(guid = "a", title = "Q", description = "",
                     app_mode = "quarto-static",
                     last_deployed_time = ""))
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS,
                                 connect_server = "https://connect.example.com/")
  expect_match(html,
    'src="https://connect.example.com/content/a/__thumbnail__"',
    fixed = TRUE)
})

test_that("build_collection_html emits a <time> element with ISO datetime; viewer JS reformats locally", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual", guids = c("a"))
  items <- list(
    list(guid = "a", title = "Q", description = "",
         app_mode = "quarto-static",
         last_deployed_time = "2026-03-31T14:54:23Z")
  )
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS)
  # The viewer's browser is responsible for the final TZ + locale display;
  # we just need the <time> tag with an ISO datetime to be present.
  expect_match(html, '<time datetime="2026-03-31T14:54:23Z">', fixed = TRUE)
  # And the localizer script must be in the rendered output.
  expect_match(html, "toLocaleString", fixed = TRUE)
})

test_that("build_collection_html renders 'type · owner' as a single byline", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual",
              guids = c("a"))
  items <- list(
    list(guid = "a", title = "Q", description = "",
         app_mode = "quarto-static", last_deployed_time = "2026-01-23T00:00:00Z",
         owner = list(first_name = "Admin", last_name = "McAdmin"))
  )
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS)
  expect_match(html, "Quarto · Admin McAdmin", fixed = TRUE)
  # The old type-badge span is gone.
  expect_no_match(html, "collection-card__type")
})

test_that("build_collection_html omits the separator when there is no owner", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "minimal", source_type = "manual",
              guids = c("a"))
  items <- list(
    list(guid = "a", title = "Q", description = "",
         app_mode = "quarto-static", last_deployed_time = "")
  )
  html <- build_collection_html(cfg, items = items, theme_colors = THEME_COLORS)
  expect_no_match(html, "Quarto ·")
  expect_match(html, ">Quarto<",  fixed = TRUE)
})

test_that("build_collection_html applies theme background color", {
  cfg <- list(title = "T", description = "", intro_markdown = "",
              theme = "warm", source_type = "manual", guids = character(0))
  html <- build_collection_html(cfg, items = list(), theme_colors = THEME_COLORS)
  expect_match(html, THEME_COLORS$warm$bg, fixed = TRUE)
})

test_that("empty_state_html shows a mailto link when owner_email is present", {
  html <- empty_state_html(
    config = list(title = "Big Collection", owner_email = "owner@example.com"),
    theme_colors = THEME_COLORS
  )
  # The "don't have access" message is present; the apostrophe may be encoded
  # as &#39; or similar — match the surrounding text without the apostrophe.
  expect_match(html, "don.*t have access", fixed = FALSE)
  expect_match(html,
               'href="mailto:owner@example.com?subject=Requesting%20access%20to%20collection%3A%20Big%20Collection"',
               fixed = TRUE)
})

test_that("empty_state_html falls back to a static line when owner_email is empty", {
  html <- empty_state_html(
    config = list(title = "Big Collection", owner_email = ""),
    theme_colors = THEME_COLORS
  )
  expect_match(html, "contact the collection owner", fixed = TRUE)
  expect_false(grepl("mailto:", html, fixed = TRUE))
})

test_that("build_collection_html omits header and intro when include_chrome = FALSE", {
  cfg <- list(title = "Big Collection",
              description = "A description",
              intro_markdown = "# Intro\n\nBody text.",
              theme = "minimal",
              source_type = "manual",
              guids = c("a"))
  items <- list(list(guid = "a", title = "Q", description = "",
                     app_mode = "quarto-static",
                     last_deployed_time = "2026-01-01T00:00:00Z"))
  html <- build_collection_html(cfg, items, THEME_COLORS,
                                include_chrome = FALSE)

  # Chrome is gone:
  expect_false(grepl('class="collection-header"', html, fixed = TRUE))
  expect_false(grepl('class="collection-title"', html, fixed = TRUE))
  expect_false(grepl('class="collection-description"', html, fixed = TRUE))
  expect_false(grepl('class="collection-panel collection-intro"',
                     html, fixed = TRUE))

  # Grid is still there:
  expect_match(html, 'class="collection-grid"', fixed = TRUE)
  expect_match(html, 'class="collection-card"', fixed = TRUE)
  expect_match(html, "Q", fixed = TRUE)  # item title
})
