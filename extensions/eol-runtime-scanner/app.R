library(shiny)
library(bslib)
library(connectapi)
library(reactable)
library(dplyr)
library(shinycssloaders)
library(lubridate)
library(bsicons)
library(tidyr)
library(shinyWidgets)

source("get_usage.R")
source("connect_module.R")
source("version_ordering.R")

options(
  spinner.type = 1,
  spinner.color = "#7494b1"
)

app_mode_groups <- list(
  "API" = c("api", "python-fastapi", "python-api", "tensorflow-saved-model"),
  "Application" = c(
    "shiny",
    "python-shiny",
    "python-dash",
    "python-gradio",
    "python-streamlit",
    "python-bokeh"
  ),
  "Jupyter" = c("jupyter-static", "jupyter-voila"),
  "Quarto" = c("quarto-shiny", "quarto-static"),
  "R Markdown" = c("rmd-shiny", "rmd-static"),
  "Pin" = c("pin"),
  "Other" = c("unknown")
)

app_mode_lookup <- with(
  stack(app_mode_groups),
  setNames(as.character(ind), values)
)

# Shiny app definition

ui <- page_sidebar(
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),

  title = "Runtime Version Scanner",

  sidebar = sidebar(
    open = TRUE,
    width = 275,

    h5("Scan for Runtimes"),

    checkboxInput(
      "use_r_cutoff",
      "Match R versions…",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_r_cutoff == true",
      sliderTextInput(
        "min_r_version",
        label = NULL,
        choices = "...",
        pre = "≤ "
      )
    ),

    checkboxInput(
      "use_py_cutoff",
      "Match Python versions…",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_py_cutoff == true",
      sliderTextInput(
        "min_py_version",
        label = NULL,
        choices = "...",
        pre = "≤ "
      )
    ),

    checkboxInput(
      "use_quarto_cutoff",
      "Match Quarto versions…",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_quarto_cutoff == true",
      sliderTextInput(
        "min_quarto_version",
        label = NULL,
        choices = "...",
        pre = "≤ "
      )
    ),

    h5("Filters"),

    selectizeInput(
      "content_type_filter",
      label = "Content Type",
      options = list(placeholder = "All Content Types"),
      choices = names(app_mode_groups),
      multiple = TRUE,
    )
  ),

  uiOutput("selected_versions_html"),

  withSpinner(reactableOutput("content_table"))
)

server <- function(input, output, session) {
  client <- connectVisitorClient()
  if (is.null(client)) {
    return()
  }

  # User-scoped content data frame
  content <- reactive({
    content <- get_content(client) |>
      filter(app_role %in% c("owner", "editor")) |>
      mutate(
        r_version = as_ordered_version_factor(r_version),
        py_version = as_ordered_version_factor(py_version),
        quarto_version = as_ordered_version_factor(quarto_version),
      )
  })

  observeEvent(
    content(),
    {
      rv <- levels(content()$r_version)
      pv <- levels(content()$py_version)
      qv <- levels(content()$quarto_version)

      updateSliderTextInput(
        session,
        "min_r_version",
        choices = I(rv)
      )

      updateSliderTextInput(
        session,
        "min_py_version",
        choices = I(pv)
      )

      updateSliderTextInput(
        session,
        "min_quarto_version",
        choices = I(qv)
      )
    },
    ignoreNULL = TRUE
  )

  usage <- reactive({
    get_usage(
      client,
      from = today() - days(6),
      to = today()
    ) |>
      group_by(content_guid) |>
      summarize(hits = n())
  })

  content_table_data <- reactive({
    content_type_mask <- if (length(input$content_type_filter) == 0) {
      names(app_mode_groups)
    } else {
      input$content_type_filter
    }

    content() |>
      mutate(content_type = app_mode_lookup[app_mode]) |>
      filter(content_type %in% content_type_mask) |>
      left_join(usage(), by = c("guid" = "content_guid")) |>
      select(
        title,
        dashboard_url,
        content_type,
        r_version,
        py_version,
        quarto_version,
        hits
      ) |>
      replace_na(list(hits = 0))
  })

  content_matching <- reactive({
    # If no filters enabled, return all content
    if (
      all(!input$use_r_cutoff, !input$use_py_cutoff, !input$use_quarto_cutoff)
    ) {
      content_table_data()
    } else {
      content_table_data() |>
        # fmt: skip
        filter(
          (input$use_r_cutoff &
            r_version <= input$min_r_version) |
          (input$use_py_cutoff &
            py_version <= input$min_py_version) |
          (input$use_quarto_cutoff &
            quarto_version <= input$min_quarto_version)
        )
    }
  })

  output$selected_versions_html <- renderUI({
    rv <- input$min_r_version
    pv <- input$min_py_version
    qv <- input$min_quarto_version

    if (
      all(!input$use_r_cutoff, !input$use_py_cutoff, !input$use_quarto_cutoff)
    ) {
      tagList(
        tags$p(
          "Showing all your content."
        ),
        tags$p(
          "Please select the versions of R, Python, or Quarto you wish to scan for."
        )
      )
    } else {
      li_items <- list()
      if (input$use_r_cutoff) {
        li_items[[length(li_items) + 1]] <- tags$li(glue::glue(
          "R {rv} or older"
        ))
      }
      if (input$use_py_cutoff) {
        li_items[[length(li_items) + 1]] <- tags$li(glue::glue(
          "Python {pv} or older"
        ))
      }
      if (input$use_quarto_cutoff) {
        li_items[[length(li_items) + 1]] <- tags$li(glue::glue(
          "Quarto {qv} or older"
        ))
      }

      tagList(
        tags$p("Showing content with any runtimes matching:"),
        tags$ul(
          style = "margin-top: 0.25rem; margin-bottom: 0.5rem;",
          tagList(li_items)
        )
      )
    }
  })

  output$content_table <- renderReactable({
    data <- content_matching()
    rv <- input$r_versions
    pv <- input$py_versions
    qv <- input$quarto_versions

    reactable(
      data,
      defaultPageSize = 500,
      columns = list(
        title = colDef(name = "Title"),
        dashboard_url = colDef(
          name = "",
          width = 32,
          sortable = FALSE,
          cell = function(url) {
            if (is.na(url) || url == "") {
              return("")
            }
            HTML(as.character(tags$div(
              onclick = "event.stopPropagation()",
              tags$a(
                href = url,
                target = "_blank",
                bsicons::bs_icon("arrow-up-right-square")
              )
            )))
          },
          html = TRUE
        ),
        content_type = colDef(name = "Content Type"),
        r_version = colDef(
          name = "R Version",
          style = function(value) {
            if (!is.null(rv) && value %in% rv) {
              list(
                color = "#7D1A03",
                fontWeight = "bold"
              )
            }
          }
        ),
        py_version = colDef(
          name = "Python Version",
          style = function(value) {
            if (!is.null(pv) && value %in% pv) {
              list(
                color = "#7D1A03",
                fontWeight = "bold"
              )
            }
          }
        ),
        quarto_version = colDef(
          name = "Quarto Version",
          style = function(value) {
            if (!is.null(qv) && value %in% qv) {
              list(
                color = "#7D1A03",
                fontWeight = "bold"
              )
            }
          }
        ),

        hits = colDef(name = "Hits in Last Week")
      )
    )
  })
}

shinyApp(ui, server)
