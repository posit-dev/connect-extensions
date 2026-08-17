WIZARD_STEP_TITLES <- c("Select content", "Describe", "Theme", "Preview")

.wizard_breadcrumb <- function(step) {
  parts <- lapply(seq_along(WIZARD_STEP_TITLES), function(i) {
    label <- sprintf("%d. %s", i, WIZARD_STEP_TITLES[i])
    cls <- if (i == step) "fw-bold text-dark" else "text-muted"
    shiny::tags$span(class = cls, label)
  })
  sep <- shiny::tags$span(class = "mx-2 text-muted", "›")
  interleaved <- list()
  for (i in seq_along(parts)) {
    interleaved[[length(interleaved) + 1]] <- parts[[i]]
    if (i < length(parts)) {
      interleaved[[length(interleaved) + 1]] <- sep
    }
  }
  shiny::tags$div(class = "border-bottom pb-2 mb-3",
                  do.call(shiny::tagList, interleaved))
}

.wizard_tabnav <- function(step) {
  tabs <- lapply(seq_along(WIZARD_STEP_TITLES), function(i) {
    label <- sprintf("%d. %s", i, WIZARD_STEP_TITLES[i])
    is_active <- (i == step)
    shiny::actionButton(
      paste0("wizard_tab_", i),
      label,
      class = paste("btn btn-compact",
                    if (is_active) "btn-primary" else "btn-outline-secondary"),
      style = "margin-right: 0.5rem;"
    )
  })
  shiny::tags$div(class = "border-bottom pb-3 mb-3 d-flex flex-wrap",
                  do.call(shiny::tagList, tabs))
}

.wizard_footer <- function(step, mode, busy = FALSE) {
  is_edit <- identical(mode, "edit")
  primary_label <- if (is_edit) "Update"
                    else if (step < 4) "Next"
                    else "Publish"
  primary_id <- if (is_edit) "wizard_publish"
                 else if (step < 4) "wizard_next"
                 else "wizard_publish"
  shiny::tags$div(
    class = "wizard-footer-row",
    style = "display:flex; align-items:center; justify-content:space-between; width:100%;",
    shiny::tags$a(href = "https://forum.posit.co/",
                  target = "_blank",
                  class = "text-muted small",
                  "Share feedback ↗"),
    shiny::tags$div(class = "d-flex gap-2 align-items-center",
      shiny::actionButton("wizard_cancel", "Cancel",
                          class = "btn-link btn-compact"),
      if (!is_edit && step > 1) shiny::actionButton("wizard_back", "Back",
                                        class = "btn-outline-secondary btn-compact"),
      shiny::actionButton(primary_id, primary_label, disabled = busy,
                          class = "btn-primary btn-compact")
    )
  )
}

wizard_modal_dialog <- function(step, mode, state, body, busy = FALSE) {
  title_text <- if (mode == "edit") {
    paste0("Edit collection: ", state$title %||% "")
  } else {
    "Add a content collection"
  }
  nav <- if (identical(mode, "edit")) .wizard_tabnav(step) else .wizard_breadcrumb(step)
  shiny::modalDialog(
    title = shiny::tags$div(
      class = "d-flex align-items-center justify-content-between w-100",
      shiny::tags$span(title_text),
      shiny::tags$span(class = "badge",
        style = paste("background-color: #72994e;",
                      "color: #fff;",
                      "font-weight: normal;",
                      "border-radius: 8px;"),
        "beta")
    ),
    nav,
    body,
    footer = .wizard_footer(step, mode, busy),
    size = "l",
    easyClose = FALSE,
    fade = FALSE
  )
}
