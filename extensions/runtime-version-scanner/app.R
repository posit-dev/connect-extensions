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
library(future.mirai)
library(purrr)

# Special version that will be greater than any real version
ANY_VERSION <- "999.99.99"

plan(mirai_multisession)

files.sources = list.files("R", full.names = TRUE)
sapply(files.sources, source)

options(
  spinner.type = 1,
  spinner.color = "#7494b1"
)

app_mode_lookup <- with(
  stack(app_mode_groups()),
  setNames(as.character(ind), values)
)

to_iso8601 <- function(x) {
  strftime(x, "%Y-%m-%dT%H:%M:%S%z") |>
    sub("([+-]\\d{2})(\\d{2})$", "\\1:\\2", x = _)
}

# Shiny app definition

ui <- page_sidebar(
  useShinyjs(),
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),

  title = h1(
    "Runtime Version Scanner",
    actionLink(
      inputId = "show_runtime_help",
      label = bsicons::bs_icon("question-circle-fill"),
      class = "ms-2",
      `data-bs-toggle` = "tooltip",
      title = "Show Runtime Version Scanner help",
      style = "margin-left: 0 !important; color: black;"
    ),
    class = "bslib-page-title navbar-brand"
  ),

  sidebar = sidebar(
    open = TRUE,
    width = 275,

    title = "Filters",

    "Runtimes",

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
      options = list(
        placeholder = "All content types",
        plugins = list("remove_button")
      ),
      choices = names(app_mode_groups()),
      multiple = TRUE
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

runtime_help_modal <- function() {
  modalDialog(
    title = "About the Runtime Version Scanner",
    tagList(
      p(
        "The Runtime Version Scanner shows a table of content you own or collaborate ",
        "on, alongside the versions of R, Python, and/or Quarto their environments ",
        "were built with. Use this to help maintain your content on Connect — for ",
        "example, by surfacing items that are actively used but running older ",
        "versions."
      ),
      p(
        "You can filter the table by runtime version using the controls the sidebar. ",
        "The runtime filters let you select a version of R, Python, or Quarto to show ",
        "only the items running an older version than the one selected. Selecting a ",
        "version labeled 'EOL' will show content running end-of-life Python and R ",
        "versions, based on the oldest officially supported Python and tidyverse-",
        "supported R versions respectively."
      ),
      p(
        "You can also filter the list by content type and view count. For example, ",
        "you could show applications with at least one view in the last quarter, or ",
        "APIs with more than 100,000 hits in the last week."
      )
    ),
    easyClose = TRUE,
    footer = NULL
  )
}

server <- function(input, output, session) {
  client <- connectVisitorClient()
  if (is.null(client)) {
    return()
  }

  oldest_supported_r <- get_oldest_supported_r()
  oldest_supported_py <- get_oldest_supported_py()

  # Server runtime versions
  server_versions <- reactive({
    get_runtimes(client)
  })

  empty_content_df <- tibble::tibble(
    title = character(),
    dashboard_url = character(),
    guid = character(),
    owner_name = character(),
    app_mode = character(),
    content_type = character(),
    r_version = factor(),
    py_version = factor(),
    quarto_version = factor(),
    last_deployed_time = as.POSIXct(character())
  )

  content_task <- ExtendedTask$new(function(content_type_filter) {
    future({
      content_list <- fetch_content(client, content_type_filter = content_type_filter)
      content_df <- content_list_to_data_frame(content_list)|>
        mutate(
          owner_name = paste(
            map_chr(owner, "first_name"),
            map_chr(owner, "last_name")
          ),
          title = coalesce(title, ifelse(name != "", name, NA))
        )
      content_df
    })
  })

  observe({
    content_task$invoke(input$content_type_filter)
  })

  content <- reactive({
    if (content_task$status() != "success") {
      return(empty_content_df)
    }

    raw <- content_task$result()

    # Extract server runtime versions
    server_vers <- server_versions()
    r_additional_vers <- c(
      server_vers |> filter(runtime == "r") |> pull(version),
      oldest_supported_r,
      ANY_VERSION
    )
    py_additional_vers <- c(
      server_vers |> filter(runtime == "python") |> pull(version),
      oldest_supported_py,
      ANY_VERSION
    )
    quarto_additional_vers <- c(
      server_vers |> filter(runtime == "quarto") |> pull(version),
      ANY_VERSION
    )

    raw |>
      mutate(
        r_version = as_ordered_version_factor(r_version, r_additional_vers),
        py_version = as_ordered_version_factor(py_version, py_additional_vers),
        quarto_version = as_ordered_version_factor(
          quarto_version,
          quarto_additional_vers
        )
      )
  })

  observeEvent(input$show_runtime_help, {
    showModal(runtime_help_modal())
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
      r_eol_label <- paste0("tidyverse EOL (< ", oldest_supported_r, ")")
      py_eol_label <- paste0("Official EOL (< ", oldest_supported_py, ")")
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
      r_eol_index <- which(r_choices == oldest_supported_r)
      py_eol_index <- which(py_choices == oldest_supported_py)

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
      from <- as.POSIXct(
        paste(today() - days(window_days), "00:00:00"),
        tz = ""
      )
      to <- as.POSIXct(paste(today(), "00:00:00"), tz = "")

      usage_list <- get_usage(client, from = from, to = to)
      as_tibble(usage_list) |>
        select(content_guid) |>
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
    content() |>
      mutate(content_type = app_mode_lookup[app_mode]) |>
      select(
        title,
        dashboard_url,
        guid,
        owner_name,
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

    if (content_task$status() != "success") {
      return(
        div(
          style = "display: flex; align-items: center; gap: 0.5em; font-style: italic;",
          span(
            class = "spinner-border spinner-border-sm",
            role = "status",
            style = "width: 1rem; height: 1rem;"
          ),
          span("Loading content…")
        )
      )
    }

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

  observe({
    toggleState("export_data", condition = nrow(content_matching()) > 0)
  })

  # Format custom cells for display ----

  format_dashboard_link <- function(url) {
    ifelse(
      is.na(url) | url == "",
      "",
      paste0(
        "<div onclick='event.stopPropagation()'><a href='",
        url,
        "' target='_blank'>",
        bsicons::bs_icon("arrow-up-right-square"),
        "</a></div>"
      )
    )
  }

  format_guid_cell <- function(guid) {
    ifelse(
      is.na(guid) | guid == "",
      "",
      paste0(
        "<div style='white-space: normal; word-break: break-all;'>",
        guid,
        "</div>"
      )
    )
  }

  content_display <- reactive({
    content_matching() |>
      mutate(
        dashboard_url = format_dashboard_link(dashboard_url),
        guid = format_guid_cell(guid)
      )
  })

  output$content_table <- renderReactable({
    if (content_task$status() != "success") {
      return(NULL)
    }
    # Only actually *render* the reactable once.
    data <- isolate(content_display())

    tbl <- reactable(
      data,
      defaultPageSize = 15,
      showPageSizeOptions = TRUE,
      pageSizeOptions = c(15, 50, 100),
      defaultSorted = "last_deployed_time",
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
          minWidth = 125,
          na = "Untitled"
        ),

        dashboard_url = colDef(
          name = "",
          width = 32,
          sortable = FALSE,
          html = TRUE
        ),

        guid = colDef(
          name = "GUID",
          show = FALSE,
          class = "number-pre",
          html = TRUE
        ),

        owner_name = colDef(
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
    updateReactable("content_table", data = content_display())
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
