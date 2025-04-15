library(shiny)
library(bslib)
library(reactable)
library(connectapi)
library(dplyr)
library(purrr)
library(lubridate)
library(tidyr)
library(sparkline)
library(htmltools)
library(bsicons)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

app_mode_groups <- list(
  "API" = c("api", "python-fastapi", "python-api", "tensorflow-saved-model"),
  "Application" = c("shiny", "python-shiny", "python-dash", "python-gradio", "python-streamlit", "python-bokeh"),
  "Jupyter" = c("jupyter-static", "jupyter-voila"),
  "Quarto" = c("quarto-shiny", "quarto-static"),
  "R Markdown" = c("rmd-shiny", "rmd-static"),
  "Pin" = c("pin"),
  "Other" = c("unknown")
)

bar_chart <- function(value, max_val, height = "1rem", fill = "#00bfc4", background = NULL) {
  width <- paste0(value * 100 / max_val, "%")
  value <- format(value, width = nchar(max_val), justify = "right")
  bar <- div(class = "bar", style = list(background = fill, width = width))
  chart <- div(class = "bar-chart", style = list(background = background), bar)
  label <- span(class = "number", value)
  div(class = "bar-cell", label, chart)
}

ui <- page_sidebar(
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),
  theme = bs_theme(version = 5),
  title = "Most Used Content",
  sidebar = sidebar(
    # title = "Controls",
    open = "desktop",
    width = 275,

    selectInput(
      "date_range_choice",
      label = "Date Range",
      choices = c("1 Week", "30 Days", "90 Days", "Custom"),
      selected = "1 Week"
    ),

    conditionalPanel(
      condition = "input.date_range_choice === 'Custom'",
      dateRangeInput(
        "date_range",
        label = NULL,
        start = today() - ddays(6),
        end = today(),
        max = today()
      )
    ),

    selectizeInput(
      "app_mode_filter",
      label = "Filter by Content Type",
      options = list(placeholder = "All Content Types"),
      choices = list(
        "API",
        "Application",
        "Jupyter",
        "Quarto",
        "R Markdown",
        "Pin",
        "Other"
      ),
      multiple = TRUE
    ),

    sliderInput(
      "visit_merge_window",
      label = "Visit Merge Window (sec)",
      min = 0,
      max = 180,
      value = 0,
      step = 1
    ),

    checkboxInput(
      "show_guid",
      label = "Show GUID"
    ),

    downloadButton(
      "export_raw_visits",
      label = "Export Raw Visits"
    ),
    downloadButton(
      "export_visit_totals",
      label = "Export Visit Totals"
    ),
    actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
  ),
  textOutput("summary_text"),
  reactableOutput("content_usage_table")
)

server <- function(input, output, session) {
  # Cache invalidation
  cache <- cachem::cache_disk("./app_cache/cache/")
  observeEvent(input$clear_cache, {
    cache$reset()
    session$reload()
  })

  client <- connect()

  content <- reactive({
    get_content(client)
  }) |> bindCache("static_key")

  date_range <- reactive({
    switch(input$date_range_choice,
            "1 Week" = c(today() - ddays(6), today()),
            "30 Days" = c(today() - ddays(29), today()),
            "90 Days" = c(today() - ddays(89), today()),
            "Custom" = input$date_range)
  })

  usage_data_raw <- reactive({
    get_usage(
      client,
      from = as.POSIXct(date_range()[1]),
      to = as.POSIXct(date_range()[2]) + hours(23) + minutes(59) + seconds(59)
    )
  }) |> bindCache(date_range())

  # Apply client-side data filters (app mode)
  usage_data_filtered <- reactive({
    print(input$app_mode_filter)
    if (length(input$app_mode_filter ) == 0) {
      usage_data_raw()
    } else {
      app_modes <- unlist(app_mode_groups[input$app_mode_filter])
      filter_guids <- content() |>
        filter(app_mode %in% app_modes) |>
        pull(guid)
      usage_data_raw() |>
        filter(content_guid %in% filter_guids)
    }
  })

  # Merge usage data hits into visits based on input.
  usage_data_visits <- reactive({
    req(input$visit_merge_window)
    if (input$visit_merge_window == 0) {
      usage_data_filtered()
    } else {
      usage_data_filtered() |>
        group_by(content_guid, user_guid) |>

        # Compute time diffs and filter out hits within the session
        mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
        replace_na(list(time_diff = seconds(Inf))) |>
        filter(time_diff > input$visit_merge_window) |>
        ungroup() |>
        select(-time_diff)
    }
  })

  # Create data for the main table and summary export.
  content_usage_data <- reactive({
    usage_summary <- usage_data_visits() |>
      group_by(content_guid) |>
      summarize(
        total_views = n(),
        unique_viewers = n_distinct(user_guid, na.rm = TRUE),
        .groups = "drop"
      )

    # Prepare sparkline data as a list column of numeric vectors.
    all_dates <- seq.Date(date_range()[1], date_range()[2], by = "day")
    daily_usage <- usage_data_visits() |>
      count(content_guid, date = date(timestamp)) |>
      complete(date = all_dates, nesting(content_guid), fill = list(n = 0)) |>
      group_by(content_guid) |>
      summarize(sparkline = list(n), .groups = "drop")

    content() |>
      mutate(owner_username = map_chr(owner, "username")) |>
      select(title, content_guid = guid, owner_username, dashboard_url) |>
      replace_na(list(title = "[Untitled]")) |>
      right_join(usage_summary, by = "content_guid") |>
      right_join(daily_usage, by = "content_guid") |>
      replace_na(list(title = "[Deleted]")) |>
      arrange(desc(total_views)) |>
      select(title, dashboard_url, content_guid, owner_username, total_views, sparkline, unique_viewers)
  })

  output$summary_text <- renderText(
    glue::glue(
      "{nrow(usage_data_visits())} visits ",
      "across {nrow(content_usage_data())} content items."
    )
  )

  content_link <- renderUI({
    req(selected_content_info())
    title_text <- selected_content_info()$title
    open_url <- selected_content_info()$dashboard_url
    icon_html <- bs_icon("arrow-up-right-square")
    HTML(glue::glue(
      "<h3>{title_text} <a href='{open_url}' target='_blank'>{icon_html}</a></h3>"
    ))
  })

  # Render main content table ----

  output$content_usage_table <- renderReactable({
    data <- content_usage_data()

    reactable(
      data,
      defaultSortOrder = "desc",
      pagination = FALSE,
      sortable = TRUE,
      highlight = TRUE,
      defaultSorted = "total_views",
      # filterable = TRUE,
      wrap = FALSE,
      class = "content-tbl",

      onClick = JS("function(rowInfo, colInfo) {
        if (rowInfo) {
          Shiny.setInputValue('row_click', rowInfo.index + 1, {priority: 'event'});
        }
      }"),

      columns = list(
        title = colDef(
          name = "Content",
          defaultSortOrder = "asc",
          filterable = TRUE,
          style = function(value) {
            switch(value,
              "[Untitled]" = list(fontStyle = "italic"),
              "[Deleted]" = list(fontStyle = "italic", color = "#808080"),
              NULL
            )
          }
        ),

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
                bs_icon("arrow-up-right-square")
              )
            )))
          },
          html = TRUE
        ),

        content_guid = colDef(
          name = "GUID",
          show = input$show_guid,
          cell = function(value) {
            div(style = list(whiteSpace = "normal", wordBreak = "break-all"), value)
          }
        ),

        owner_username = colDef(name = "Owner", defaultSortOrder = "asc", minWidth = 75, filterable = TRUE),

        total_views = colDef(
          name = "Visits",
          align = "left",
          minWidth = 75,
          maxWidth = 150,
          cell = function(value) {
            max_val <- max(data$total_views, na.rm = TRUE)
            bar_chart(value, max_val, fill = "#7494b1", background = "#e1e1e1")
          }
        ),

        sparkline = colDef(
          name = "By Day",
          align = "left",
          width = 90,
          sortable = FALSE,
          cell = function(value) {
            sparkline::sparkline(
              value,
              type = "bar",
              barColor = "#7494b1",
              disableTooltips = TRUE,
              barWidth = 8,
              chartRangeMin = TRUE
            )
          }
        ),

        unique_viewers = colDef(
          name = "Unique Visitors",
          align = "left",
          minWidth = 70,
          maxWidth = 135,
          cell = function(value) {
            max_val <- max(data$total_views, na.rm = TRUE)
            format(value, width = nchar(max_val), justify = "right")
          },
          class = "number"
        )
      )
    )
  })

  # Download handlers ---

  output$export_raw_visits <- downloadHandler(
    filename = function() {
      paste0("content_raw_visits_", Sys.Date(), ".csv")
    },
    content = function(file) {
      write.csv(usage_data_raw(), file, row.names = FALSE)
    }
  )

  output$export_visit_totals <- downloadHandler(
    filename = function() {
      paste0("content_visit_totals_", Sys.Date(), ".csv")
    },
    content = function(file) {
      to_export <- content_usage_data() |>
        select(-sparkline)
      write.csv(to_export, file, row.names = FALSE)
    }
  )

  # Observe table click
  observeEvent(input$row_click, {
    showModal(modalDialog(
      title = paste("Content details", input$row_click),
      "Shiny UI goes here",
      easyClose = TRUE
    ))
  })
}

shinyApp(ui, server)
