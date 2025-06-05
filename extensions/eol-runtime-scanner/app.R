library(shiny)
library(bslib)
library(connectapi)
library(reactable)
library(dplyr)
library(shinycssloaders)
library(lubridate)
library(bsicons)

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

    selectizeInput(
      "r_versions",
      label = "Select R Versions",
      choices = NULL,
      multiple = TRUE
    ),

    selectizeInput(
      "py_versions",
      label = "Select Python Versions",
      choices = NULL,
      multiple = TRUE
    ),

    selectizeInput(
      "quarto_versions",
      label = "Select Quarto Versions",
      choices = NULL,
      multiple = TRUE
    )
  ),

  withSpinner(reactableOutput("content_table"))
)

server <- function(input, output, session) {
  client <- connectVisitorClient()
  if (is.null(client)) {
    return()
  }

  content <- reactive({
    content <- get_content(client) |>
      filter(
        !if_all(c(r_version, py_version, quarto_version), is.na)
      )
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

  content_filtered <- reactive({
    df <- content()
    rv <- input$r_versions
    pv <- input$py_versions
    qv <- input$quarto_versions

    df |>
      filter(
        (length(rv) > 0 & r_version %in% rv) |
          (length(pv) > 0 & py_version %in% pv) |
          (length(qv) > 0 & quarto_version %in% qv) |
          (length(rv) == 0 & length(pv) == 0 & length(qv) == 0)
      )
  })

  content_table_data <- reactive({
    content_filtered() |>
      select(
        guid,
        title,
        app_mode,
        r_version,
        py_version,
        quarto_version,
        dashboard_url
      ) |>
      left_join(usage(), by = c("guid" = "content_guid"))
  })

  output$content_table <- renderReactable({
    data <- content_table_data()

    reactable(
      data,
      defaultPageSize = 25,
      columns = list(
        guid = colDef(name = "GUID"),
        title = colDef(name = "Title"),
        app_mode = colDef(name = "App Mode"),
        r_version = colDef(name = "R Version"),
        py_version = colDef(name = "Python Version"),
        quarto_version = colDef(name = "Quarto Version"),
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
        hits = colDef(name = "Hits in Last Week")
      )
    )
  })
}

shinyApp(ui, server)
