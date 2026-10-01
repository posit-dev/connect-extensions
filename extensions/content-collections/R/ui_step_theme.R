step_theme_ui <- function(state) {
  selected <- state$theme %||% "minimal"
  buttons <- lapply(names(THEME_COLORS), function(id) {
    t <- THEME_COLORS[[id]]
    is_sel <- identical(id, selected)
    style <- sprintf(
      paste("background:%s; color:%s; border:2px solid %s;",
            "font-weight:500; padding:1rem; border-radius:0.5rem;",
            "min-height:80px; text-align:center;",
            if (is_sel) sprintf("box-shadow: 0 0 0 1px %s, 0 0 0 4px %s;",
                                t$accent, t$bg) else ""),
      t$bg, t$accent, if (is_sel) t$accent else "#dee2e6"
    )
    shiny::actionButton(
      paste0("theme_", id),
      shiny::tagList(
        shiny::tags$div(t$label),
        shiny::tags$div(class = "small mt-1",
          shiny::tags$span(style = sprintf(
            "display:inline-block; width:8px; height:8px; border-radius:50%%; background:%s; margin-right:2px;",
            t$accent)),
          shiny::tags$span(style = sprintf(
            "display:inline-block; width:8px; height:8px; border-radius:50%%; background:%s; margin-right:2px;",
            t$border)),
          shiny::tags$span(style = sprintf(
            "display:inline-block; width:8px; height:8px; border-radius:50%%; background:%s;",
            t$bg))
        )
      ),
      class = "btn",
      style = style,
      `aria-pressed` = if (is_sel) "true" else "false"
    )
  })
  shiny::tagList(
    shiny::tags$div(class = "wizard-step-body",
      shiny::tags$p(class = "text-muted",
        "Pick a theme. You can change it any time."),
      shiny::tags$div(
        style = "display:grid; grid-template-columns:repeat(3, 1fr); gap:1rem;",
        buttons
      )
    )
  )
}
