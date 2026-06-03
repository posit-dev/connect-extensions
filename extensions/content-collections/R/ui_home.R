# Truncate text after `max_chars` characters with a single-character ellipsis.
# Strips any HTML first so descriptions saved with stray markup display
# cleanly here on the home page.
.truncate_text <- function(s, max_chars = 120) {
  s <- .strip_html(s %||% "")
  if (!nzchar(s)) return("")
  if (nchar(s) <= max_chars) s
  else paste0(substr(s, 1, max_chars), "…")
}

# Human-readable summary of a collection's source: "N items" (manual) or
# "Tag: <tag>" (tag). Returns a "Loading..." placeholder when the metadata
# for this collection hasn't been fetched yet.
.home_details_text <- function(meta) {
  if (is.null(meta)) return("Loading details…")
  if (identical(meta$source_type, "tag")) {
    tag <- meta$source_tag %||% ""
    if (nzchar(tag)) sprintf("Tag: %s", tag) else "Tag-based"
  } else {
    n <- meta$n_items %||% NA_integer_
    if (is.na(n)) ""
    else sprintf("%d %s", n, if (n == 1) "item" else "items")
  }
}

# Build the Connect thumbnail URL for a collection. Connect serves
# thumbnails at /content/<guid>/__thumbnail__; non-2xx responses (no
# thumbnail set on the content) trigger the <img onerror> fallback to
# the bundled collection.svg.
.thumbnail_src <- function(coll, connect_server = "") {
  guid <- coll$guid %||% ""
  if (!nzchar(guid)) return("icons/collection.svg")
  server <- sub("/$", "", connect_server %||% "")
  paste0(server, "/content/", guid, "/__thumbnail__")
}

# Bootstrap Icons clipboard glyph, inlined so we don't add a dependency
# just for one icon. width/height match the surrounding text size.
.clipboard_icon <- function() {
  shiny::HTML(paste(
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"',
    '     fill="currentColor" viewBox="0 0 16 16"',
    '     style="vertical-align:-2px; margin-right:0.25rem;">',
    '  <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>',
    '  <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>',
    '</svg>'
  ))
}

.home_row <- function(coll, connect_server = "", meta = NULL) {
  guid  <- coll$guid %||% ""
  title <- coll$title %||% coll$name %||% guid
  date  <- .format_datetime(coll$last_deployed_time)
  # Title links to the Connect dashboard (not the standalone rendered URL)
  # so the publisher lands somewhere they can adjust metadata, sharing, and
  # scheduling. Same destination as the post-publish toast's button.
  base <- sub("/$", "", connect_server %||% "")
  open_url <- paste0(base, "/connect/#/apps/", guid)
  details <- .home_details_text(meta)
  raw_desc <- if (!is.null(meta) && nzchar(meta$description %||% "")) {
    meta$description
  } else {
    coll$description %||% ""
  }
  desc <- .truncate_text(raw_desc)

  shiny::tags$div(class = "d-flex align-items-center gap-3 py-3 px-3 border-bottom",
    shiny::tags$img(
      src = .thumbnail_src(coll, connect_server),
      width = "64", height = "64",
      class = "rounded",
      style = "object-fit: cover; flex-shrink: 0;",
      alt = "",
      onerror = "this.onerror=null;this.src='icons/collection.svg';"
    ),
    shiny::tags$div(class = "flex-grow-1",
      shiny::tags$div(class = "d-flex align-items-baseline gap-3 flex-wrap",
        shiny::tags$a(href = open_url, target = "_blank",
                      class = "fw-medium text-decoration-none",
                      title),
        shiny::actionLink(paste0("copy_", guid),
          shiny::tagList(.clipboard_icon(), "Share this collection"),
          class = "small text-muted")
      ),
      if (nzchar(desc))
        shiny::tags$div(class = "text-muted small mt-1", desc),
      if (nzchar(details))
        shiny::tags$div(class = "text-muted small", details),
      if (nzchar(date))
        shiny::tags$div(class = "text-muted small",
                        shiny::HTML(paste("Last published:", date)))
    ),
    shiny::tags$div(class = "d-flex gap-2",
      shiny::actionButton(paste0("edit_", guid), "Edit",
                          class = "btn-outline-secondary btn-compact")
    )
  )
}

.beta_callout <- function() {
  shiny::tags$div(
    class = "alert alert-secondary",
    style = "background-color:#eef2ff; color:#3730a3; border-color:#c7d2fe;",
    shiny::tags$div(class = "fw-medium",
                    "Collections is an experimental feature"),
    shiny::tags$div(class = "small mt-1",
                    "While in beta, please note these limitations:"),
    shiny::tags$ul(class = "small mb-4 mt-1",
      shiny::tags$li("Limited theming options."),
      shiny::tags$li("Sharing a collection only shares the collection itself — recipients still need access to each item inside it.")
    ),
    shiny::tags$div(class = "small mr-2",
      "Have feedback? ",
      shiny::tags$a(href = "https://forum.posit.co/", target = "_blank",
                    class = "alert-link", "Tell us on Posit Community ↗")
    )
  )
}

# Banner shown above the collection list when visitor token exchange
# failed. Helps a publisher distinguish "I own zero collections" from
# "the configurator can't authenticate to Connect."
.auth_failed_banner <- function(detail = NULL) {
  shiny::tags$div(class = "alert alert-warning mb-4", role = "alert",
    shiny::tags$div(
      shiny::tags$strong("Couldn't authenticate to Connect. "),
      "Your collections aren't appearing because the Configurator can't ",
      "mint a visitor API key. Confirm the ",
      shiny::tags$strong("Posit Connect API"),
      " (Visitor API Key) OAuth integration is attached to this content ",
      "in its Connect settings."
    ),
    if (!is.null(detail) && nzchar(detail)) {
      shiny::tags$details(class = "mt-2 small text-muted",
        shiny::tags$summary("Details"),
        shiny::tags$code(detail)
      )
    }
  )
}

home_view <- function(collections, connect_server = "",
                     collection_meta = list(),
                     auth_status = "ok",
                     auth_message = NULL) {
  shiny::tagList(
    shiny::tags$div(class = "container py-4",
      shiny::tags$div(class = "d-flex align-items-center justify-content-between mb-4",
        shiny::tags$div(class = "d-flex align-items-center",
          shiny::tags$h1(class = "h3 mb-0", "My Content Collections"),
          shiny::tags$span(class = "badge ms-3",
            style = paste("background-color: #72994e;",
                          "color: #fff;",
                          "font-weight: normal;",
                          "font-size: 14px;",
                          "border-radius: 8px;"),
            "beta")
        ),
        shiny::actionButton("new_collection", "+ New collection",
                            class = "btn-primary btn-compact")
      ),
      .beta_callout(),
      if (identical(auth_status, "failed")) .auth_failed_banner(auth_message),
      if (length(collections) == 0) {
        shiny::tags$div(class = "text-center text-muted py-5",
          style = "border:1px dashed #ced4da; border-radius:0.5rem;",
          "You haven't created any collections yet. Click 'New collection' to get started."
        )
      } else {
        shiny::tags$div(class = "border rounded",
          lapply(collections, function(coll) {
            .home_row(coll, connect_server = connect_server,
                      meta = collection_meta[[coll$guid %||% ""]])
          })
        )
      },
      shiny::tags$div(class = "mt-4 text-end",
        shiny::tags$a(href = "https://forum.posit.co/",
                      target = "_blank",
                      class = "text-muted small",
                      "Share feedback ↗")
      )
    )
  )
}
