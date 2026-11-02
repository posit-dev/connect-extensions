# Try Connect's thumbnail (/content/<guid>/__thumbnail__); on 404 the
# <img onerror> swaps in the content-type icon. Shiny serves www/ at the
# root, so the icons/<file>.svg fallback path resolves in this app.
.thumb_or_icon_img <- function(guid, app_mode, connect_server, size = "44") {
  fallback <- content_icon_path(app_mode)
  src <- if (nzchar(guid) && nzchar(connect_server %||% "")) {
    paste0(sub("/$", "", connect_server), "/content/", guid, "/__thumbnail__")
  } else {
    fallback
  }
  shiny::tags$img(
    src = src, width = size, height = size,
    class = "rounded",
    style = "flex-shrink:0; object-fit:cover;",
    alt = "",
    onerror = sprintf("this.onerror=null;this.src='%s';", fallback)
  )
}

# Builds a "Type · Owner · M/D/YY H:MMam" meta line, dropping pieces that
# aren't available so a row with just app_mode still renders cleanly.
.row_meta <- function(item) {
  parts <- c(
    if (nzchar(content_type_label(item$app_mode %||% "")))
      content_type_label(item$app_mode %||% "") else NULL,
    if (nzchar(.owner_name(item)))                    .owner_name(item) else NULL,
    if (nzchar(.format_datetime(item$last_deployed_time)))
      .format_datetime(item$last_deployed_time) else NULL
  )
  paste(parts, collapse = " · ")
}

.result_row <- function(item, is_selected, connect_server = "") {
  guid  <- item$guid %||% ""
  title <- item$title %||% item$name %||% "Untitled"
  mode  <- item$app_mode %||% ""
  meta  <- .row_meta(item)
  # Use an actionButton so clicks fire as counter events. Stateful inputs
  # (raw checkboxes) misfire when the modal re-renders and the DOM rebinds —
  # they would silently remove guids on subtab switches.
  shiny::actionButton(
    paste0("toggle_", guid),
    shiny::tagList(
      shiny::tags$span(class = paste("row-check",
                                     if (is_selected) "checked" else "")),
      .thumb_or_icon_img(guid, mode, connect_server),
      shiny::tags$div(class = "flex-grow-1 row-info",
        shiny::tags$div(class = "fw-medium", title),
        shiny::tags$div(class = "text-muted small", shiny::HTML(meta))
      )
    ),
    class = paste("row-toggle", if (is_selected) "selected" else "")
  )
}

# A row in the "Selected" subtab. Shows the same icon+title+meta as a
# result row, plus an inline Remove button that drops the item from
# wizard_state$guids.
.selected_row <- function(item, connect_server = "") {
  guid  <- item$guid %||% ""
  title <- item$title %||% item$name %||% "Untitled"
  mode  <- item$app_mode %||% ""
  meta  <- .row_meta(item)
  shiny::tags$div(
    class = "d-flex align-items-center gap-3 py-2 px-3 border-top selected-row",
    .thumb_or_icon_img(guid, mode, connect_server),
    shiny::tags$div(class = "flex-grow-1 row-info",
      shiny::tags$div(class = "fw-medium", title),
      shiny::tags$div(class = "text-muted small", shiny::HTML(meta))
    ),
    shiny::actionButton(paste0("remove_", guid), "Remove",
                        class = "btn-sm btn-outline-danger")
  )
}

# Segmented "Select content / Use a tag" toggle. Implemented as a Bootstrap
# btn-group of two actionButtons so that the active state is rendered by
# Bootstrap's own .btn-primary and the buttons abut without any gap.
.source_type_toggle <- function(source_type) {
  is_manual <- !identical(source_type, "tag")
  shiny::tags$div(class = "btn-group", role = "group",
    shiny::actionButton("source_type_manual", "Select content",
      class = paste("btn btn-compact",
                    if (is_manual) "btn-primary" else "btn-outline-secondary")),
    shiny::actionButton("source_type_tag", "Use a tag",
      class = paste("btn btn-compact",
                    if (!is_manual) "btn-primary" else "btn-outline-secondary"))
  )
}

# Subtab nav for "Search results" / "Selected (N)" inside Select-content mode.
.subtab_nav <- function(active, n_selected) {
  shiny::tags$div(class = "btn-group", role = "group",
    shiny::actionButton("select_subtab_results", "Search results",
      class = paste("btn btn-compact",
                    if (identical(active, "selected"))
                      "btn-outline-secondary" else "btn-secondary")),
    shiny::actionButton("select_subtab_selected",
      sprintf("Selected (%d)", n_selected),
      class = paste("btn btn-compact",
                    if (identical(active, "selected"))
                      "btn-secondary" else "btn-outline-secondary"))
  )
}

step_select_ui <- function(state, search_query, search_results, all_tags,
                           subtab = "results", selected_items = list(),
                           connect_server = "") {
  source_type <- state$source_type %||% "manual"
  selected_guids <- state$guids %||% character(0)

  # Tag choices: only child tags (those with parent_id set)
  tag_choices <- c("Select a tag..." = "")
  for (t in all_tags) {
    if (!is.null(t$parent_id)) tag_choices[t$name] <- t$name
  }

  # ---- Search-results subtab body ----
  search_body <- shiny::tagList(
    shiny::textInput("search_query", label = NULL,
                     value = search_query %||% "",
                     placeholder = "Search for content to add...",
                     width = "100%"),
    if (length(search_results) == 0) {
      shiny::tags$div(class = "text-center text-muted my-4 p-4",
        style = "border:1px dashed #ced4da; border-radius:0.5rem;",
        if (nzchar(search_query %||% ""))
          "No content matches your search."
        else
          "Start typing to find content you've published or have access to"
      )
    } else {
      shiny::tagList(
        shiny::tags$div(
          class = "d-flex align-items-center justify-content-between py-2 px-3 border-top border-bottom",
          shiny::actionButton("select_all",
                              sprintf("Select all %d", length(search_results)),
                              class = "btn-link p-0"),
          shiny::tags$span(class = "text-muted small",
                           sprintf("%d selected", length(selected_guids)))
        ),
        shiny::tags$div(class = "result-list",
          lapply(search_results, function(item) {
            .result_row(item, (item$guid %||% "") %in% selected_guids,
                        connect_server = connect_server)
          })
        )
      )
    }
  )

  # ---- Selected subtab body ----
  selected_body <- if (length(selected_guids) == 0) {
    shiny::tags$div(class = "text-center text-muted my-4 p-4",
      style = "border:1px dashed #ced4da; border-radius:0.5rem;",
      "No items selected yet. Use the Search results tab to add some."
    )
  } else {
    # Render in the order of selected_guids; use cache for details, fall
    # back to a placeholder (just the guid) when details aren't loaded yet.
    rows <- lapply(selected_guids, function(g) {
      item <- selected_items[[g]] %||% list(guid = g, title = g,
                                             app_mode = "unknown")
      .selected_row(item, connect_server = connect_server)
    })
    shiny::tags$div(class = "result-list border-top",
      do.call(shiny::tagList, rows)
    )
  }

  # ---- Manual-mode body (just the chosen subtab body; subtab nav is hoisted
  # to the same row as the source-type toggle below) ----
  manual_body <- if (identical(subtab, "selected")) selected_body else search_body

  # ---- Tag-mode body ----
  tag_body <- shiny::tagList(
    shiny::selectInput("tag_select", "Select Tag",
                       choices = tag_choices,
                       selected = state$source_tag %||% ""),
    shiny::tags$p(class = "form-text",
      "Content tagged with this tag will be included automatically each time the collection renders. Newly tagged content shows up on the next render.")
  )

  # The "Select content / Use a tag" toggle sits on the left and (in manual
  # mode) the "Search results / Selected" subtab nav sits on the right —
  # both on the same row.
  toggles_row <- shiny::tags$div(
    class = "d-flex align-items-center justify-content-between mb-3",
    .source_type_toggle(source_type),
    if (identical(source_type, "manual"))
      .subtab_nav(subtab, length(selected_guids))
    else
      shiny::tags$div()  # empty spacer to keep the toggle on the left
  )

  shiny::tagList(
    shiny::tags$div(class = "wizard-step-body",
      toggles_row,
      if (identical(source_type, "manual")) manual_body else tag_body
    )
  )
}
