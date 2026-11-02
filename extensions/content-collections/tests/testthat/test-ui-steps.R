test_that("step_describe_ui returns a tag containing all three input ids", {
  ui <- step_describe_ui(state = list(title = "", description = "",
                                      intro_markdown = ""))
  html <- as.character(ui)
  expect_match(html, 'id="collection_title"',       fixed = TRUE)
  expect_match(html, 'id="collection_description"', fixed = TRUE)
  expect_match(html, 'id="collection_intro"',       fixed = TRUE)
})

test_that("step_describe_ui prefills inputs from state", {
  ui <- step_describe_ui(state = list(title = "My title",
                                      description = "Short",
                                      intro_markdown = "# Hi"))
  html <- as.character(ui)
  expect_match(html, "My title", fixed = TRUE)
  expect_match(html, "Short",    fixed = TRUE)
  expect_match(html, "# Hi",     fixed = TRUE)
})

test_that("step_theme_ui renders one button per theme", {
  ui <- step_theme_ui(state = list(theme = "minimal"))
  html <- as.character(ui)
  for (name in names(THEME_COLORS)) {
    expect_match(html, sprintf('id="theme_%s"', name), fixed = TRUE,
                 info = sprintf("missing theme button: %s", name))
  }
})

test_that("step_theme_ui marks the selected theme with an aria pressed attribute", {
  ui <- step_theme_ui(state = list(theme = "warm"))
  html <- as.character(ui)
  expect_match(html, 'aria-pressed="true"[^>]*id="theme_warm"',
               perl = TRUE)
  expect_match(html, 'aria-pressed="false"[^>]*id="theme_minimal"',
               perl = TRUE)
})

test_that("step_select_ui renders the source-type toggle (no beta callout)", {
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = character(0)),
    search_query = "", search_results = list(), all_tags = list()
  )
  html <- as.character(ui)
  expect_match(html, 'id="source_type_manual"', fixed = TRUE)
  expect_match(html, 'id="source_type_tag"',    fixed = TRUE)
  expect_match(html, "Select content",          fixed = TRUE)
  expect_match(html, "Use a tag",               fixed = TRUE)
  # Beta callout moved to the home page.
  expect_no_match(html, "experimental feature")
})

test_that("step_select_ui shows the search/selected subtab nav with current count", {
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = c("a", "b", "c")),
    search_query = "", search_results = list(), all_tags = list(),
    subtab = "results"
  )
  html <- as.character(ui)
  expect_match(html, 'id="select_subtab_results"',  fixed = TRUE)
  expect_match(html, 'id="select_subtab_selected"', fixed = TRUE)
  expect_match(html, "Selected (3)",                fixed = TRUE)
})

test_that("step_select_ui Selected subtab renders one row per selected guid with remove buttons", {
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = c("g1", "g2")),
    search_query = "", search_results = list(), all_tags = list(),
    subtab = "selected",
    selected_items = list(
      g1 = list(guid = "g1", title = "Alpha", app_mode = "shiny"),
      g2 = list(guid = "g2", title = "Beta",  app_mode = "quarto-static")
    )
  )
  html <- as.character(ui)
  expect_match(html, "Alpha",            fixed = TRUE)
  expect_match(html, "Beta",             fixed = TRUE)
  expect_match(html, 'id="remove_g1"',   fixed = TRUE)
  expect_match(html, 'id="remove_g2"',   fixed = TRUE)
})

test_that("step_select_ui shows search input + empty hint in manual mode with no results", {
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = character(0)),
    search_query = "", search_results = list(), all_tags = list()
  )
  html <- as.character(ui)
  expect_match(html, 'id="search_query"', fixed = TRUE)
  expect_match(html, "Start typing",      fixed = TRUE)
})

test_that("step_select_ui renders one row per result with checkbox and icon", {
  results <- list(
    list(guid = "g1", title = "First", description = "Hello",
         app_mode = "quarto-static"),
    list(guid = "g2", title = "Second", description = "",
         app_mode = "shiny")
  )
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = c("g1")),
    search_query = "x", search_results = results, all_tags = list()
  )
  html <- as.character(ui)
  expect_match(html, "First",  fixed = TRUE)
  expect_match(html, "Second", fixed = TRUE)
  expect_match(html, "Quarto", fixed = TRUE)
  expect_match(html, "Shiny",  fixed = TRUE)
  # Without a connect_server the primary src is the icon path; onerror
  # also points at it (defensive).
  expect_match(html, "icons/quarto.svg", fixed = TRUE)
  expect_match(html, "icons/shiny.svg",  fixed = TRUE)
  # The "Select all" checkbox uses a fixed input id
  expect_match(html, 'id="select_all"', fixed = TRUE)
})

test_that("step_select_ui meta line shows type, owner, and date+time when available", {
  results <- list(
    list(guid = "g1", title = "First",
         app_mode = "rmd-static",
         owner = list(first_name = "David", last_name = "McGaffin"),
         last_deployed_time = "2026-03-31T14:54:23Z")
  )
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = character(0)),
    search_query = "x", search_results = results, all_tags = list()
  )
  html <- as.character(ui)
  expect_match(html, "R Markdown · David McGaffin · ", fixed = TRUE)
  expect_match(html,
    "[0-9]{1,2}/[0-9]{1,2}/[0-9]{2} [0-9]{1,2}:[0-9]{2}(am|pm)",
    perl = TRUE)
})

test_that("step_select_ui meta line falls back to type when owner/date are missing", {
  results <- list(
    list(guid = "g1", title = "First", app_mode = "shiny")
  )
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = character(0)),
    search_query = "x", search_results = results, all_tags = list()
  )
  html <- as.character(ui)
  # Just the type label, no trailing separator.
  expect_match(html, ">Shiny<", fixed = TRUE)
  expect_no_match(html, "Shiny ·", fixed = TRUE)
})

test_that("step_select_ui uses Connect __thumbnail__ URLs when connect_server is given", {
  results <- list(
    list(guid = "g1", title = "First", description = "",
         app_mode = "quarto-static")
  )
  ui <- step_select_ui(
    state = list(source_type = "manual", source_tag = "",
                 guids = character(0)),
    search_query = "x", search_results = results, all_tags = list(),
    connect_server = "https://connect.example.com"
  )
  html <- as.character(ui)
  expect_match(html,
    'src="https://connect.example.com/content/g1/__thumbnail__"',
    fixed = TRUE)
  # onerror falls back to the content-type icon path (Shiny serves www/).
  expect_match(html, "this.src=&#39;icons/quarto.svg&#39;", fixed = TRUE)
})

test_that("step_select_ui shows tag selector in tag mode", {
  ui <- step_select_ui(
    state = list(source_type = "tag", source_tag = "",
                 guids = character(0)),
    search_query = "", search_results = list(),
    all_tags = list(list(name = "favorites", parent_id = "1"),
                    list(name = "research", parent_id = "1"))
  )
  html <- as.character(ui)
  expect_match(html, 'id="tag_select"', fixed = TRUE)
  expect_match(html, "favorites",       fixed = TRUE)
  expect_match(html, "research",        fixed = TRUE)
})

test_that("step_preview_ui shows the rendered HTML when not busy", {
  ui <- step_preview_ui(html_string = "<h1>Hello</h1>",
                        source_type = "manual", busy = FALSE)
  html <- as.character(ui)
  expect_match(html, "<h1>Hello</h1>", fixed = TRUE)
  expect_no_match(html, "Generating preview", fixed = TRUE)
})

test_that("step_preview_ui shows a busy spinner when busy", {
  ui <- step_preview_ui(html_string = "", source_type = "manual", busy = TRUE)
  html <- as.character(ui)
  expect_match(html, "Generating preview", fixed = TRUE)
})

test_that("step_preview_ui shows the tag-mode caveat in tag mode", {
  ui <- step_preview_ui(html_string = "<p>X</p>",
                        source_type = "tag", busy = FALSE)
  html <- as.character(ui)
  expect_match(html, "snapshot from now", fixed = TRUE)
})
