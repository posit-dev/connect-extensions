library(shiny)
library(bslib)
library(connectapi)
library(reactable)
library(dplyr)
library(shinycssloaders)
library(lubridate)
library(bsicons)
library(tidyr)
library(future)

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

    h5(
      "Scan for Runtimes",
      tooltip(
        bsicons::bs_icon("question-circle-fill"),
        tagList(
          p(
            "Enable a runtime filter and select a version to show ",
            "items using versions older than the selected version.",
          ),
        )
      )
    ),

    checkboxInput(
      "use_r_cutoff",
      label = "R older than…",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_r_cutoff == true",
      selectizeInput(
        "r_version_cutoff",
        label = NULL,
        choices = NULL
      )
    ),

    checkboxInput(
      "use_py_cutoff",
      label = "Python older than…",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_py_cutoff == true",
      selectizeInput(
        "py_version_cutoff",
        label = NULL,
        choices = NULL
      )
    ),

    checkboxInput(
      "use_quarto_cutoff",
      label = "Quarto older than…",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_quarto_cutoff == true",
      selectizeInput(
        "quarto_version_cutoff",
        label = NULL,
        choices = NULL
      )
    ),

    h5("Filters"),

    selectizeInput(
      "content_type_filter",
      label = "Content Type",
      options = list(placeholder = "All Content Types"),
      choices = names(app_mode_groups),
      multiple = TRUE,
    ),

    selectizeInput(
      "views_window",
      label = "Views Window",
      choices = c(
        "Last Week" = 7,
        "Last Month" = 30,
        "Last Quarter" = 90
      ),
      selected = 7
    ),

    numericInput(
      "min_hits_filter",
      label = "Minimum Views",
      value = 0,
      min = 0,
      step = 1
    ),

    h5("View"),

    checkboxInput(
      "show_guid",
      label = "Show GUIDs"
    ),
  ),

  uiOutput("selected_versions_html"),

  withSpinner(reactableOutput("content_table")),

  uiOutput("usage_loading_message"),

  tags$script(HTML(
    "
  Shiny.addCustomMessageHandler('setGuidVisible', function(visible) {
    Reactable.setHiddenColumns('content_table', prev => {
      const cols = prev.filter(c => c !== 'guid');
      return visible ? cols : [...cols, 'guid'];
    });
  });
"
  ))
)

server <- function(input, output, session) {
  client <- connectVisitorClient()
  if (is.null(client)) {
    return()
  }

  # Server runtime versions
  server_versions <- reactive({
    get_runtimes(client)
  })

  # User-scoped content data frame
  content <- reactive({
    # Extract server runtime versions by type
    server_vers <- server_versions()
    r_server_vers <- server_vers |> filter(runtime == "r") |> pull(version)
    py_server_vers <- server_vers |>
      filter(runtime == "python") |>
      pull(version)
    quarto_server_vers <- server_vers |>
      filter(runtime == "quarto") |>
      pull(version)

    content <- get_content(client) |>
      filter(app_role %in% c("owner", "editor")) |>
      mutate(
        owner_username = map_chr(owner, "username"),
        r_version = as_ordered_version_factor(r_version, r_server_vers),
        py_version = as_ordered_version_factor(py_version, py_server_vers),
        quarto_version = as_ordered_version_factor(
          quarto_version,
          quarto_server_vers
        ),
      )
  })

  # Initialize the version selectize inputs when content is loaded
  observeEvent(
    content(),
    {
      rv <- levels(content()$r_version)
      pv <- levels(content()$py_version)
      qv <- levels(content()$quarto_version)

      # Update the R version input
      updateSelectizeInput(
        session,
        "r_version_cutoff",
        choices = I(rv),
        selected = if (length(rv) > 0) rv[length(rv)] else NULL
      )

      # Update the Python version input
      updateSelectizeInput(
        session,
        "py_version_cutoff",
        choices = I(pv),
        selected = if (length(pv) > 0) pv[length(pv)] else NULL
      )

      # Update the Quarto version input
      updateSelectizeInput(
        session,
        "quarto_version_cutoff",
        choices = I(qv),
        selected = if (length(qv) > 0) qv[length(qv)] else NULL
      )
    },
    ignoreNULL = TRUE
  )

  usage_task <- ExtendedTask$new(function(window_days) {
    future({
      get_usage(client, from = today() - days(window_days), to = today()) |>
        group_by(content_guid) |>
        summarize(hits = n(), .groups = "drop")
    })
  })

  observeEvent(input$views_window, {
    usage_task$invoke(as.integer(input$views_window))
  })

  output$usage_loading_message <- renderUI({
    if (usage_task$status() %in% c("initial", "pending", "running")) {
      div(
        style = "font-style: italic;",
        "Loading usage..."
      )
    } else {
      NULL
    }
  })

  content_table_data <- reactive({
    # Filter by content type
    content_type_mask <- if (length(input$content_type_filter) == 0) {
      names(app_mode_groups)
    } else {
      input$content_type_filter
    }

    content() |>
      mutate(content_type = app_mode_lookup[app_mode]) |>
      filter(content_type %in% content_type_mask) |>
      select(
        title,
        dashboard_url,
        guid,
        owner_username,
        content_type,
        r_version,
        py_version,
        quarto_version
      )
  })

  content_matching <- reactive({
    base <- content_table_data()

    if (usage_task$status() != "success") {
      base <- base |> mutate(hits = NA_integer_)
    } else {
      base <- base |>
        left_join(usage_task$result(), by = c("guid" = "content_guid")) |>
        mutate(hits = replace_na(hits, 0))
    }

    # fmt: skip
    if (all(!input$use_r_cutoff, !input$use_py_cutoff, !input$use_quarto_cutoff)) {
    return(base)
  }

    base |>
      filter(
        (input$use_r_cutoff & r_version < input$r_version_cutoff) |
          (input$use_py_cutoff & py_version < input$py_version_cutoff) |
          (input$use_quarto_cutoff &
            quarto_version < input$quarto_version_cutoff)
      )
  })

  output$selected_versions_html <- renderUI({
    rv <- input$r_version_cutoff
    pv <- input$py_version_cutoff
    qv <- input$quarto_version_cutoff

    # Get the total count of filtered content
    total_count <- nrow(content_matching())

    if (
      all(!input$use_r_cutoff, !input$use_py_cutoff, !input$use_quarto_cutoff)
    ) {
      return(tagList(
        tags$p(glue::glue("Showing {total_count} items.")),
        tags$p("Please select cutoff versions of R, Python, or Quarto.")
      ))
    }

    # Count active filters
    active_filters <- sum(
      input$use_r_cutoff,
      input$use_py_cutoff,
      input$use_quarto_cutoff
    )

    # Single filter case
    if (active_filters == 1) {
      if (input$use_r_cutoff) {
        return(tags$p(HTML(glue::glue(
          "Showing {total_count} items using R older than <span class='number-pre'>{rv}</span>."
        ))))
      }
      if (input$use_py_cutoff) {
        return(tags$p(HTML(glue::glue(
          "Showing {total_count} items using Python older than <span class='number-pre'>{pv}</span>."
        ))))
      }
      if (input$use_quarto_cutoff) {
        return(tags$p(HTML(glue::glue(
          "Showing {total_count} items using Quarto older than <span class='number-pre'>{qv}</span>."
        ))))
      }
    }

    # Multiple filters case
    # Calculate counts for each runtime version filter
    r_count <- if (input$use_r_cutoff) {
      nrow(content_table_data() |> filter(r_version < input$r_version_cutoff))
    } else {
      0
    }

    py_count <- if (input$use_py_cutoff) {
      nrow(content_table_data() |> filter(py_version < input$py_version_cutoff))
    } else {
      0
    }

    quarto_count <- if (input$use_quarto_cutoff) {
      nrow(
        content_table_data() |>
          filter(quarto_version < input$quarto_version_cutoff)
      )
    } else {
      0
    }

    # Create list items for multiple filters
    li_items <- list()
    if (input$use_r_cutoff) {
      li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
        "R older than <span class='number-pre'>{rv}</span> ({r_count} items)"
      )))
    }
    if (input$use_py_cutoff) {
      li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
        "Python older than <span class='number-pre'>{pv}</span> ({py_count} items)"
      )))
    }
    if (input$use_quarto_cutoff) {
      li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
        "Quarto older than <span class='number-pre'>{qv}</span> ({quarto_count} items)"
      )))
    }

    tagList(
      tags$p(glue::glue("Showing {total_count} items using any of:")),
      tags$ul(
        style = "margin-top: 0.25rem; margin-bottom: 0.5rem;",
        tagList(li_items)
      )
    )
  })

  output$content_table <- renderReactable({
    # Only actually *render* the reactable once.
    data <- isolate(content_matching())

    tbl <- reactable(
      data,
      defaultPageSize = 15,
      showPageSizeOptions = TRUE,
      pageSizeOptions = c(15, 50, 100),
      class = "content-tbl",
      defaultColDef = colDef(
        headerVAlign = "bottom",
        headerStyle = list(
          whiteSpace = "normal"
        ),
        style = list(whiteSpace = "nowrap")
      ),
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

        guid = colDef(
          name = "GUID",
          show = FALSE,
          class = "number-pre",
          cell = function(value) {
            div(
              style = list(whiteSpace = "normal", wordBreak = "break-all"),
              value
            )
          }
        ),

        owner_username = colDef(
          name = "Owner",
          defaultSortOrder = "asc",
          minWidth = 75,
          maxWidth = 175
        ),

        content_type = colDef(name = "Content Type", width = 125),

        r_version = colDef(
          name = "R",
          width = 100,
          class = "number-pre",
        ),
        py_version = colDef(
          name = "Python",
          width = 100,
          class = "number-pre",
        ),
        quarto_version = colDef(
          name = "Quarto",
          width = 100,
          class = "number-pre",
        ),

        hits = colDef(
          name = "Views \n(Last Week)",
          width = 135,
          class = "number-pre",
          defaultSortOrder = "desc"
        )
      )
    )

    htmlwidgets::onRender(
      tbl,
      "() => {
        Shiny.setInputValue('content_table_ready', Math.random())
      }"
    )
  })

  observe({
    updateReactable("content_table", data = content_matching())
  })
  observe({
    req(input$content_table_ready)
    session$sendCustomMessage("setGuidVisible", input$show_guid)
  })
}

shinyApp(ui, server)
