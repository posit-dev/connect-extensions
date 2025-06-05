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

options(
  spinner.type = 1,
  spinner.color = "#7494b1"
)

# Shiny app definition

ui <- page_sidebar(
  title = "End-of-Life Runtime Scanner",

  sidebar = sidebar(
    open = TRUE,
    width = 275,

    h5("Select EOL Versions"),

    selectizeInput(
      "r_versions",
      label = "R Versions",
      choices = NULL,
      multiple = TRUE
    ),

    selectizeInput(
      "py_versions",
      label = "Python Versions",
      choices = NULL,
      multiple = TRUE
    ),

    selectizeInput(
      "quarto_versions",
      label = "Quarto Versions",
      choices = NULL,
      multiple = TRUE
    )
  ),

  textOutput("selected_versions_text"),
  textOutput("n_eol_content_text"),

  withSpinner(reactableOutput("content_table"))
)

server <- function(input, output, session) {
  client <- connectVisitorClient()
  if (is.null(client)) {
    return()
  }

  content <- reactive({
    content <- get_content(client) |>
      filter(app_role %in% c("owner", "editor"))
  })

  observeEvent(
    content(),
    {
      rv <- sort(unique(content()$r_version))
      pv <- sort(unique(content()$py_version))
      qv <- sort(unique(content()$quarto_version))

      updateSelectizeInput(
        session,
        "r_versions",
        choices = rv,
        selected = character(0)
      )
      updateSelectizeInput(
        session,
        "py_versions",
        choices = pv,
        selected = character(0)
      )
      updateSelectizeInput(
        session,
        "quarto_versions",
        choices = qv,
        selected = character(0)
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
    content() |>
      left_join(usage(), by = c("guid" = "content_guid")) |>
      select(
        title,
        dashboard_url,
        app_mode,
        r_version,
        py_version,
        quarto_version,
        hits
      ) |>
      replace_na(list(hits = 0))
  })

  content_eol <- reactive({
    df <- content_table_data()
    rv <- input$r_versions
    pv <- input$py_versions
    qv <- input$quarto_versions

    df |>
      filter(
        (length(rv) > 0 & r_version %in% rv) |
          (length(pv) > 0 & py_version %in% pv) |
          (length(qv) > 0 & quarto_version %in% qv)
      )
  })

  output$selected_versions_text <- renderText({
    rv <- input$r_versions
    pv <- input$py_versions
    qv <- input$quarto_versions

    if (length(rv) == 0 & length(pv) == 0 & length(qv) == 0) {
      paste0(
        "Please select the versions of R, Python, and Quarto you ",
        "wish to scan for."
      )
    } else {
      parts <- c(
        if (length(rv) > 0) glue::glue("R: {paste(rv, collapse = ', ')}"),
        if (length(pv) > 0) glue::glue("Python: {paste(pv, collapse = ', ')}"),
        if (length(qv) > 0) glue::glue("Quarto: {paste(qv, collapse = ', ')}")
      )
      glue::glue("Selected runtimes: {paste(parts, collapse = '; ')}.")
    }
  })

  output$n_eol_content_text <- renderText({
    rv <- input$r_versions
    pv <- input$py_versions
    qv <- input$quarto_versions

    n_eol_content <- nrow(content_eol())

    if (length(rv) == 0 & length(pv) == 0 & length(qv) == 0) {
      NULL
    } else if (n_eol_content == 0) {
      "You don't have any content using the selected end-of-life runtimes."
    } else {
      glue::glue(
        "You have {n_eol_content} ",
        "{ifelse(n_eol_content == 1, 'piece', 'pieces')} ",
        "of content using the selected end-of-life runtimes."
      )
    }
  })

  output$content_table <- renderReactable({
    data <- content_eol()
    rv <- input$r_versions
    pv <- input$py_versions
    qv <- input$quarto_versions

    reactable(
      data,
      pagination = FALSE,
      columns = list(
        title = colDef(name = "Title"),
        dashboard_url = colDef(
          name = "",
          width = 32,
          sortable = FALSE,
          cell = function(url) {
            if (is.na(url) || url == "") return("")
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
        app_mode = colDef(name = "App Mode"),
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
