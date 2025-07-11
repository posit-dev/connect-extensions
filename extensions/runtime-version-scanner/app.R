library(shiny)
library(bslib)
library(connectapi)
library(reactable)
library(dplyr)
library(shinycssloaders)
library(lubridate)
library(bsicons)
library(tidyr)
library(shinyjs)
library(future)

# https://devguide.python.org/versions/
PY_OLDEST_SUPPORTED <- "3.9.0"

# https://www.tidyverse.org/blog/2019/04/r-version-support/, https://www.r-project.org/
R_OLDEST_SUPPORTED <- "4.1.0"

# Special version that will be greater than any real version
ANY_VERSION <- "999.99.99"

plan(multisession)

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
  useShinyjs(),
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),

  title = "Runtime Version Scanner",

  sidebar = sidebar(
    open = TRUE,
    width = 275,

    title = "Filters",

    div(
      "Runtimes",
      tooltip(
        bsicons::bs_icon("question-circle-fill"),
        tagList(
          p(
            "Enable a runtime filter and select a version range to ",
            "filter content by runtime version.",
          ),
        )
      )
    ),

    checkboxInput(
      "use_r_cutoff",
      label = "R",
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
      label = "Python",
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
      label = "Quarto",
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

    tags$hr(),

    selectizeInput(
      "content_type_filter",
      label = "Content types",
      options = list(placeholder = "All content types"),
      choices = names(app_mode_groups),
      multiple = TRUE,
    ),

    tags$hr(),

    div("Viewed at least…"),

    div(
      class = "form-group shiny-input-container",
      div(
        style = "display: flex; align-items: baseline; gap: 6px; height: 36.5px",
        numericInput(
          "min_views_filter",
          label = NULL,
          value = 0,
          min = 0,
          width = "80px",
        ),
        span("times")
      )
    ),

    div(
      class = "form-group shiny-input-container",
      div(
        style = "display: flex; align-items: baseline; gap: 6px; height: 36.5px",
        span("in the last"),
        selectizeInput(
          "views_window",
          label = NULL,
          choices = c(
            "week" = 7,
            "month" = 30,
            "quarter" = 90
          ),
          selected = 7,
          width = "110px",
        ),
      )
    ),

    conditionalPanel(
      condition = "output.usage_task_running",
      div(
        style = "display: flex; align-items: center; gap: 0.5em; font-style: italic;",
        span(
          class = "spinner-border spinner-border-sm",
          role = "status",
          style = "width: 1rem; height: 1rem;"
        ),
        span("Loading usage…")
      )
    ),

    tags$hr(),

    checkboxInput(
      "show_guid",
      label = "Show GUIDs"
    ),

    downloadButton(
      "export_data",
      class = "btn-sm",
      label = "Download Filtered Data"
    )
  ),

  uiOutput("selected_versions_html"),

  withSpinner(reactableOutput("content_table")),

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

    # Include EOL versions and ANY_VERSION in the additional versions
    r_additional_vers <- c(r_server_vers, R_OLDEST_SUPPORTED, ANY_VERSION)
    py_additional_vers <- c(py_server_vers, PY_OLDEST_SUPPORTED, ANY_VERSION)
    quarto_additional_vers <- c(quarto_server_vers, ANY_VERSION)

    content <- get_content(client) |>
      filter(app_role %in% c("owner", "editor")) |>
      mutate(
        owner_username = map_chr(owner, "username"),
        r_version = as_ordered_version_factor(r_version, r_additional_vers),
        py_version = as_ordered_version_factor(py_version, py_additional_vers),
        quarto_version = as_ordered_version_factor(
          quarto_version,
          quarto_additional_vers
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

      # Create named vectors for the dropdown choices
      r_choices <- rv
      py_choices <- pv
      quarto_choices <- qv

      # Special version labels
      r_eol_label <- paste0("tidyverse EOL (< ", R_OLDEST_SUPPORTED, ")")
      py_eol_label <- paste0("Official EOL (< ", PY_OLDEST_SUPPORTED, ")")
      any_version_label <- "Any version"

      # Format labels for all normal versions
      format_version_label <- function(version) {
        if (version == ANY_VERSION) {
          return(any_version_label)
        } else {
          return(paste0("< ", version))
        }
      }

      # Create names for all choices with formatted labels
      names(r_choices) <- sapply(r_choices, format_version_label)
      names(py_choices) <- sapply(py_choices, format_version_label)
      names(quarto_choices) <- sapply(quarto_choices, format_version_label)

      # Find the EOL versions and add special labels
      r_eol_index <- which(r_choices == R_OLDEST_SUPPORTED)
      py_eol_index <- which(py_choices == PY_OLDEST_SUPPORTED)

      if (length(r_eol_index) > 0) {
        names(r_choices)[r_eol_index] <- r_eol_label
      }
      if (length(py_eol_index) > 0) {
        names(py_choices)[py_eol_index] <- py_eol_label
      }

      # Update the R version input
      updateSelectizeInput(
        session,
        "r_version_cutoff",
        choices = r_choices,
        selected = if (length(rv) > 0) rv[r_eol_index] else NULL
      )

      # Update the Python version input
      updateSelectizeInput(
        session,
        "py_version_cutoff",
        choices = py_choices,
        selected = if (length(pv) > 0) pv[py_eol_index] else NULL
      )

      # Update the Quarto version input
      updateSelectizeInput(
        session,
        "quarto_version_cutoff",
        choices = quarto_choices,
        selected = if (length(qv) > 0) qv[length(qv)] else NULL
      )
    },
    ignoreNULL = TRUE
  )

  usage_task <- ExtendedTask$new(function(window_days) {
    future({
      get_usage(client, from = today() - days(window_days), to = today()) |>
        group_by(content_guid) |>
        summarize(views = n(), .groups = "drop")
    })
  })

  observeEvent(input$views_window, {
    usage_task$invoke(as.integer(input$views_window))
  })

  output$usage_task_running <- reactive({
    usage_task$status() == "running"
  })
  outputOptions(output, "usage_task_running", suspendWhenHidden = FALSE)

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
        quarto_version,
        last_deployed_time
      )
  })

  content_matching <- reactive({
    base <- content_table_data()

    if (usage_task$status() != "success") {
      base <- base |> mutate(views = NA_integer_)
    } else {
      base <- base |>
        left_join(usage_task$result(), by = c("guid" = "content_guid")) |>
        mutate(views = replace_na(views, 0)) |>
        filter(views >= input$min_views_filter)
    }

    base <- relocate(base, last_deployed_time, .after = last_col())

    if (
      all(!input$use_r_cutoff, !input$use_py_cutoff, !input$use_quarto_cutoff)
    ) {
      return(base)
    }

    # Apply filters based on runtime version cutoffs

    # Apply the filter
    result <- base |>
      # fmt: skip
      filter(
        (input$use_r_cutoff & r_version < input$r_version_cutoff) |
        (input$use_py_cutoff & py_version < input$py_version_cutoff) |
        (input$use_quarto_cutoff & quarto_version < input$quarto_version_cutoff)
      )

    # Return the filtered results

    result
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
        label <- if (rv == ANY_VERSION) {
          "any R version"
        } else {
          paste0("R version < ", rv)
        }
        return(tags$p(HTML(glue::glue(
          "Showing {total_count} items using {label}."
        ))))
      }
      if (input$use_py_cutoff) {
        label <- if (pv == ANY_VERSION) {
          "any Python version"
        } else {
          paste0("Python version < ", pv)
        }
        return(tags$p(HTML(glue::glue(
          "Showing {total_count} items using {label}."
        ))))
      }
      if (input$use_quarto_cutoff) {
        label <- if (qv == ANY_VERSION) {
          "any Quarto version"
        } else {
          paste0("Quarto version < ", qv)
        }
        return(tags$p(HTML(glue::glue(
          "Showing {total_count} items using {label}."
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
      r_label <- if (rv == ANY_VERSION) {
        "Any R version"
      } else {
        paste0("R version < ", rv)
      }
      li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
        "{r_label} ({r_count} items)"
      )))
    }
    if (input$use_py_cutoff) {
      py_label <- if (pv == ANY_VERSION) {
        "Any Python version"
      } else {
        paste0("Python version < ", pv)
      }
      li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
        "{py_label} ({py_count} items)"
      )))
    }
    if (input$use_quarto_cutoff) {
      quarto_label <- if (qv == ANY_VERSION) {
        "Any Quarto version"
      } else {
        paste0("Quarto version < ", qv)
      }
      li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
        "{quarto_label} ({quarto_count} items)"
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
        title = colDef(
          name = "Title",
          minWidth = 125
        ),

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
          na = "—"
        ),
        py_version = colDef(
          name = "Python",
          width = 100,
          class = "number-pre",
          na = "—"
        ),
        quarto_version = colDef(
          name = "Quarto",
          width = 100,
          class = "number-pre",
          na = "—"
        ),

        views = colDef(
          name = "Views",
          minWidth = 75,
          maxWidth = 100,
          class = "number-pre",
          defaultSortOrder = "desc"
        ),

        last_deployed_time = colDef(
          name = "Last Published",
          width = 170,
          format = colFormat(datetime = TRUE),
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


  # Download handler
  output$export_data <- downloadHandler(
    filename = function() {
      paste0("connect_content_runtimes_filtered", Sys.Date(), ".csv")
    },
    content = function(file) {
      write.csv(content_matching(), file, row.names = FALSE)
    }
  )
}

shinyApp(ui, server)
