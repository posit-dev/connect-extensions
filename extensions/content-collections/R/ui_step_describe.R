step_describe_ui <- function(state) {
  shiny::tagList(
    shiny::tags$div(class = "wizard-step-body",
      shiny::tags$div(class = "mb-3",
        shiny::textInput("collection_title", "Title",
                         value = state$title %||% "",
                         placeholder = "My Collection",
                         width = "100%"),
        shiny::tags$div(class = "form-text",
          "Shown as the collection's headline and as the Connect content's display name.")
      ),
      shiny::tags$div(class = "mb-3",
        shiny::textInput("collection_description", "Description",
                         value = state$description %||% "",
                         placeholder = "A short description",
                         width = "100%"),
        shiny::tags$div(class = "form-text",
          "A one-line summary shown under the title.")
      ),
      shiny::tags$div(class = "mb-3",
        shiny::textAreaInput("collection_intro",
                             "Introduction",
                             value = state$intro_markdown %||% "",
                             rows = 5,
                             placeholder = "Write an intro. Markdown is supported.",
                             width = "100%"),
        shiny::tags$div(class = "form-text",
          "Markdown supported (headings, lists, links). Appears in a panel above the items.")
      )
    )
  )
}
