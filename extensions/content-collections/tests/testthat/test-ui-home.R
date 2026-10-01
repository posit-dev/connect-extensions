test_that("home_view shows the New collection button", {
  ui <- home_view(collections = list())
  html <- as.character(ui)
  expect_match(html, 'id="new_collection"', fixed = TRUE)
  expect_match(html, "New collection",      fixed = TRUE)
})

test_that("home_view shows an auth banner when auth_status is 'failed'", {
  ui <- home_view(collections = list(), auth_status = "failed")
  html <- as.character(ui)
  expect_match(html, "Couldn't authenticate to Connect", fixed = TRUE)
  expect_match(html, "Visitor API Key",                  fixed = TRUE)
  expect_match(html, "alert-warning",                    fixed = TRUE)
})

test_that("home_view omits the auth banner on every non-failed status", {
  for (s in c("ok", "fallback", "anonymous", "unknown")) {
    html <- as.character(home_view(collections = list(), auth_status = s))
    expect_false(grepl("Couldn't authenticate to Connect", html, fixed = TRUE),
                 info = paste("status =", s))
  }
})

test_that("home_view auth banner surfaces the diagnostic message in details", {
  ui <- home_view(collections = list(),
                  auth_status = "failed",
                  auth_message = "boom: integration missing")
  html <- as.character(ui)
  expect_match(html, "<details", fixed = TRUE)
  expect_match(html, "boom: integration missing", fixed = TRUE)
})

test_that("home_view shows a beta pill next to the title", {
  ui <- home_view(collections = list())
  html <- as.character(ui)
  expect_match(html, ">beta</span>", fixed = TRUE)
  # Pill sits between the title and the New collection button.
  title_pos  <- regexpr("My Content Collections", html, fixed = TRUE)
  pill_pos   <- regexpr(">beta</span>",           html, fixed = TRUE)
  button_pos <- regexpr('id="new_collection"',    html, fixed = TRUE)
  expect_true(title_pos < pill_pos)
  expect_true(pill_pos < button_pos)
})

test_that("home_view shows the empty-state when there are no collections", {
  ui <- home_view(collections = list())
  html <- as.character(ui)
  expect_match(html, "haven't created any collections", fixed = TRUE)
})

test_that("home_view renders the beta callout above the collection list", {
  ui <- home_view(collections = list())
  html <- as.character(ui)
  expect_match(html, "experimental feature", fixed = TRUE)
  expect_match(html, "Posit Community",      fixed = TRUE)
  # Callout sits between the heading row and the empty/list area.
  heading_pos <- regexpr("My Content Collections", html, fixed = TRUE)
  callout_pos <- regexpr("experimental feature",  html, fixed = TRUE)
  list_pos    <- regexpr("haven't created any collections",
                         html, fixed = TRUE)
  expect_true(heading_pos < callout_pos)
  expect_true(callout_pos < list_pos)
})

test_that("home_view renders 'Last published' with date and time", {
  collections <- list(
    list(guid = "g1", title = "Coll A",
         last_deployed_time = "2026-03-31T14:54:23Z")
  )
  ui <- home_view(collections = collections)
  html <- as.character(ui)
  expect_match(html, "Last published:", fixed = TRUE)
  # Format: M/D/YY H:MM(am|pm); exact hour depends on local TZ.
  expect_match(html,
    "[0-9]{1,2}/[0-9]{1,2}/[0-9]{2} [0-9]{1,2}:[0-9]{2}(am|pm)",
    perl = TRUE)
})

test_that("home_view renders one row per collection", {
  collections <- list(
    list(guid = "g1", title = "Coll A", last_deployed_time = "2026-01-01T00:00:00Z"),
    list(guid = "g2", title = "Coll B", last_deployed_time = "2026-02-02T00:00:00Z")
  )
  ui <- home_view(collections = collections)
  html <- as.character(ui)
  expect_match(html, "Coll A", fixed = TRUE)
  expect_match(html, "Coll B", fixed = TRUE)
  expect_match(html, 'id="edit_g1"', fixed = TRUE)
  expect_match(html, 'id="edit_g2"', fixed = TRUE)
})

test_that("home_view renders the title as a link to the Connect dashboard URL", {
  collections <- list(
    list(guid = "g1", title = "Coll A", last_deployed_time = "2026-01-01T00:00:00Z")
  )
  ui <- home_view(collections = collections,
                   connect_server = "https://connect.example.com")
  html <- as.character(ui)
  expect_match(html, 'href="https://connect.example.com/connect/#/apps/g1"', fixed = TRUE)
  expect_match(html, ">Coll A</a>", fixed = TRUE)
  # The standalone Open button is gone.
  expect_no_match(html, ">Open</a>")
})

test_that("home_view title link strips a trailing slash from connect_server", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  ui <- home_view(collections = collections,
                   connect_server = "https://connect.example.com/")
  html <- as.character(ui)
  expect_match(html, 'href="https://connect.example.com/connect/#/apps/g1"', fixed = TRUE)
})

test_that("home_view renders a Share-this-collection link with copy_<guid> id", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  ui <- home_view(collections = collections)
  html <- as.character(ui)
  expect_match(html, 'id="copy_g1"', fixed = TRUE)
  expect_match(html, "Share this collection", fixed = TRUE)
  # SVG clipboard icon is inlined alongside the label.
  expect_match(html, "<svg", fixed = TRUE)
})

test_that("home_view shows a loading placeholder when metadata is missing", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  ui <- home_view(collections = collections)
  html <- as.character(ui)
  expect_match(html, "Loading details", fixed = TRUE)
})

test_that("home_view shows item count for search-based collections", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  meta <- list(g1 = list(source_type = "manual", n_items = 5))
  ui <- home_view(collections = collections, collection_meta = meta)
  html <- as.character(ui)
  expect_match(html, ">5 items<", fixed = TRUE)
  # The old "Search-based" prefix is gone.
  expect_no_match(html, "Search-based")
})

test_that("home_view singularizes item count when there is one item", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  meta <- list(g1 = list(source_type = "manual", n_items = 1))
  ui <- home_view(collections = collections, collection_meta = meta)
  html <- as.character(ui)
  expect_match(html, ">1 item<", fixed = TRUE)
})

test_that("home_view shows tag name as 'Tag: <name>'", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  meta <- list(g1 = list(source_type = "tag", source_tag = "finance"))
  ui <- home_view(collections = collections, collection_meta = meta)
  html <- as.character(ui)
  expect_match(html, "Tag: finance", fixed = TRUE)
  expect_no_match(html, "Tag-based:")
})

test_that("home_view renders the collection description when present", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  meta <- list(g1 = list(source_type = "manual", n_items = 0,
                          description = "A short description."))
  ui <- home_view(collections = collections, collection_meta = meta)
  html <- as.character(ui)
  expect_match(html, "A short description.", fixed = TRUE)
})

test_that("home_view truncates long descriptions with an ellipsis", {
  long <- paste(rep("a", 200), collapse = "")
  collections <- list(list(guid = "g1", title = "Coll A"))
  meta <- list(g1 = list(source_type = "manual", n_items = 0,
                          description = long))
  ui <- home_view(collections = collections, collection_meta = meta)
  html <- as.character(ui)
  expect_match(html, paste0(paste(rep("a", 120), collapse = ""), "…"),
               fixed = TRUE)
})

test_that("home_view falls back to the Connect content description when meta is missing", {
  collections <- list(list(guid = "g1", title = "Coll A",
                           description = "from Connect"))
  ui <- home_view(collections = collections)
  html <- as.character(ui)
  expect_match(html, "from Connect", fixed = TRUE)
})

test_that("home_view renders the Connect __thumbnail__ URL for each row", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  ui <- home_view(collections = collections,
                   connect_server = "https://connect.example.com")
  html <- as.character(ui)
  expect_match(html,
    'src="https://connect.example.com/content/g1/__thumbnail__"',
    fixed = TRUE)
})

test_that("home_view strips a trailing slash from connect_server in the thumbnail URL", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  ui <- home_view(collections = collections,
                   connect_server = "https://connect.example.com/")
  html <- as.character(ui)
  expect_match(html,
    'src="https://connect.example.com/content/g1/__thumbnail__"',
    fixed = TRUE)
})

test_that("home_view ships the collection.svg fallback in <img onerror>", {
  collections <- list(list(guid = "g1", title = "Coll A"))
  ui <- home_view(collections = collections,
                   connect_server = "https://connect.example.com")
  html <- as.character(ui)
  expect_match(html, "icons/collection.svg", fixed = TRUE)
})

test_that("home_view no longer warns that Title and Description leak across access permissions", {
  ui <- home_view(collections = list())
  html <- as.character(ui)
  expect_false(grepl("regardless of the access permissions",
                     html, fixed = TRUE))
})
