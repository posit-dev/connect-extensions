library(shiny)
library(bslib)
library(connectapi)
library(reactable)
library(dplyr)
library(shinycssloaders)
library(lubridate)
library(bsicons)
library(tidyr)

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

# Helper function to style versions based on server availability
style_version_by_availability <- function(server_versions) {
  function(value) {
    value_str <- as.character(value)
    if (!is.na(value_str)) {
      # Check if version doesn't exist in server versions
      if (!(value_str %in% server_versions)) {
        return(list(
          color = "#7D1A03", # Red color for versions not on server
          fontWeight = "bold",
          background = "#FFF0F0" # Light red background
        ))
      } else {
        return(list(
          color = "#276749" # Green color for versions on server
        ))
      }
    }
  }
}

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
      label = "R versions",
      value = FALSE
    ),
    conditionalPanel(
      condition = "input.use_r_cutoff == true",
      uiOutput("r_version_selector")
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

    checkboxInput(
      "highlight_stale_builds",
      "Highlight stale builds",
      value = FALSE
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

  # Reactive value to store selected R version
  selected_r_version <- reactiveVal()

  # Version selector helpers
  create_r_version_buttons <- function(versions, selected_version) {
    if (length(versions) == 0) {
      return(NULL)
    }

    div(
      class = "version-selector",
      lapply(versions, function(version) {
        is_selected <- !is.null(selected_version) && version <= selected_version
        is_max <- !is.null(selected_version) && version == selected_version

        # Three possible states: not selected, selected below max, or the max version
        btn_class <- if (!is_selected) {
          "btn-version"
        } else if (is_max) {
          "btn-version selected max"
        } else {
          "btn-version selected"
        }

        actionButton(
          inputId = paste0("r_version_", gsub("\\.", "_", version)),
          label = version,
          class = btn_class
        )
      })
    )
  }

  # Generate the version selector UI
  output$r_version_selector <- renderUI({
    rv <- levels(content()$r_version)
    create_r_version_buttons(rv, selected_r_version())
  })

  # Initialize with content and set default selected versions
  observeEvent(
    content(),
    {
      rv <- levels(content()$r_version)
      pv <- levels(content()$py_version)
      qv <- levels(content()$quarto_version)

      # Set initial R version (highest available)
      if (length(rv) > 0) {
        selected_r_version(rv[length(rv)])
      }

      # Use the highest version for Python and Quarto (still using selectizeInput)
      updateSelectizeInput(
        session,
        "py_version_cutoff",
        choices = I(pv),
        selected = if (length(pv) > 0) pv[length(pv)] else NULL
      )

      updateSelectizeInput(
        session,
        "quarto_version_cutoff",
        choices = I(qv),
        selected = if (length(qv) > 0) qv[length(qv)] else NULL
      )
    },
    ignoreNULL = TRUE
  )

  # Handle button clicks for R version selection
  observe({
    rv <- levels(content()$r_version)

    lapply(rv, function(version) {
      btn_id <- paste0("r_version_", gsub("\\.", "_", version))
      observeEvent(
        input[[btn_id]],
        {
          selected_r_version(version)
        },
        ignoreInit = TRUE
      )
    })
  })

  usage <- reactive({
    get_usage(
      client,
      from = today() - days(6),
      to = today()
    ) |>
      group_by(content_guid) |>
      summarize(hits = n())
  })

  server_versions <- reactive({
    get_runtimes(client)
  })

  content_table_data <- reactive({
    # Filter by content type
    content_type_mask <- if (length(input$content_type_filter) == 0) {
      names(app_mode_groups)
    } else {
      input$content_type_filter
    }

    # Get min hits for filtering
    min_hits <- input$min_hits_filter

    content() |>
      mutate(content_type = app_mode_lookup[app_mode]) |>
      filter(content_type %in% content_type_mask) |>
      left_join(usage(), by = c("guid" = "content_guid")) |>
      select(
        title,
        dashboard_url,
        guid,
        content_type,
        r_version,
        py_version,
        quarto_version,
        hits
      ) |>
      replace_na(list(hits = 0)) |>
      filter(hits >= min_hits)
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
            r_version <= selected_r_version()) |
          (input$use_py_cutoff &
            py_version < input$py_version_cutoff) |
          (input$use_quarto_cutoff &
            quarto_version < input$quarto_version_cutoff)
        )
    }
  })

  output$selected_versions_html <- renderUI({
    rv <- selected_r_version()
    pv <- input$py_version_cutoff
    qv <- input$quarto_version_cutoff

    # Get the total count of filtered content
    total_count <- nrow(content_matching())

    if (
      all(!input$use_r_cutoff, !input$use_py_cutoff, !input$use_quarto_cutoff)
    ) {
      tagList(
        tags$p(
          glue::glue("Showing {total_count} items.")
        ),
        tags$p(
          "Please select cutoff versions of R, Python, or Quarto."
        )
      )
    } else {
      # Calculate counts for each runtime version filter
      r_count <- if (input$use_r_cutoff) {
        nrow(content_table_data() |> filter(r_version <= selected_r_version()))
      } else {
        0
      }

      py_count <- if (input$use_py_cutoff) {
        nrow(
          content_table_data() |> filter(py_version < input$py_version_cutoff)
        )
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

      li_items <- list()
      if (input$use_r_cutoff) {
        li_items[[length(li_items) + 1]] <- tags$li(HTML(glue::glue(
          "R version {rv} and earlier ({r_count} items)"
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
        tags$p(glue::glue("Showing {total_count} items with any of:")),
        tags$ul(
          style = "margin-top: 0.25rem; margin-bottom: 0.5rem;",
          tagList(li_items)
        )
      )
    }
  })

  output$content_table <- renderReactable({
    data <- content_matching()

    # Extract available server runtime versions by type
    server_vers <- server_versions()
    r_server_vers <- server_vers |> filter(runtime == "r") |> pull(version)
    py_server_vers <- server_vers |>
      filter(runtime == "python") |>
      pull(version)
    quarto_server_vers <- server_vers |>
      filter(runtime == "quarto") |>
      pull(version)

    # Extract server versions for styling

    reactable(
      data,
      defaultPageSize = 15,
      showPageSizeOptions = TRUE,
      pageSizeOptions = c(15, 50, 100),
      wrap = FALSE,
      class = "content-tbl",
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
          show = input$show_guid,
          class = "number-pre",
          cell = function(value) {
            div(
              style = list(whiteSpace = "normal", wordBreak = "break-all"),
              value
            )
          }
        ),

        content_type = colDef(name = "Content Type", width = 125),

        r_version = colDef(
          name = "R",
          width = 100,
          class = "number-pre",
          style = if (input$highlight_stale_builds) {
            style_version_by_availability(r_server_vers)
          } else {
            NULL
          }
        ),
        py_version = colDef(
          name = "Python",
          width = 100,
          class = "number-pre",
          style = if (input$highlight_stale_builds) {
            style_version_by_availability(py_server_vers)
          } else {
            NULL
          }
        ),
        quarto_version = colDef(
          name = "Quarto",
          width = 100,
          class = "number-pre",
          style = if (input$highlight_stale_builds) {
            style_version_by_availability(quarto_server_vers)
          } else {
            NULL
          }
        ),

        hits = colDef(
          name = "Views (Last Week)",
          width = 125,
          class = "number-pre",
        )
      )
    )
  })
}

shinyApp(ui, server)
