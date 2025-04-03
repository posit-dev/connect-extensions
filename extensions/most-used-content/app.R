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

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

# bar <- div(
#   class = "bar-chart",
#   style = list(marginRight = "0.375rem"),
#   div(class = "bar", style = list(width = width, backgroundColor = "#3fc1c9"))
# )
# div(class = "bar-cell", span(class = "number", value), bar)

bar_chart <- function(value, max_val, height = "1rem", fill = "#00bfc4", background = NULL) {
  width <- paste0(value * 100 / max_val, "%")
  value <- format(value, width = nchar(max_val), justify = "right")
  bar <- div(class = "bar", style = list(background = fill, width = width))
  chart <- div(class = "bar-chart", style = list(background = background), bar)
  label <- span(class = "number", value)
  div(class = "bar-cell", label, chart)
}

ui <- page_fillable(
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),
  theme = bs_theme(version = 5),
  card(
    card_header("Most Used Content"),
    layout_sidebar(
      sidebar = sidebar(
        # title = "Controls",
        open = TRUE,
        width = 275,

        dateRangeInput(
          "date_range",
          label = "Select Date Range",
          start = today() - ddays(6),
          end = today(),
          max = today()
        ),

        selectizeInput(
          "app_mode_filter",
          label = "Filter by Content Type",
          options = list(placeholder = "All Content Types"),
          choices = list(
            "Python Bokeh" = "python-bokeh",
            "Python Dash" = "python-dash",
            "Python FastAPI" = "python-fastapi",
            "Python Flask API" = "python-api",
            "Python Gradio" = "python-gradio",
            "Python Jupyter Notebook" = "jupyter-static",
            "Python Jupyter Voila" = "jupyter-voila",
            "Python Shiny" = "python-shiny",
            "Python Streamlit" = "python-streamlit",
            "Quarto" = "quarto-static",
            "Quarto (Interactive)" = "quarto-shiny",
            "R Markdown" = "rmd-static",
            "R Markdown (Interactive)" = "rmd-shiny",
            "R Plumber API" = "api",
            "R Shiny" = "shiny",
            "Static HTML" = "static",
            "Tensorflow Model" = "tensorflow-saved-model",
            "Unknown" = "unknown"
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
      card(
        reactableOutput("content_usage_table")
      )
    )
  )
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

  usage_data_raw <- reactive({
    get_usage(
      client,
      from = as.POSIXct(input$date_range[1]),
      to = as.POSIXct(input$date_range[2]) + hours(23) + minutes(59) + seconds(59)
    )
  }) |> bindCache(input$date_range)

  # Apply client-side data filters (app mode)
  usage_data_filtered <- reactive({
    print(input$app_mode_filter)
    if (length(input$app_mode_filter ) == 0) {
      usage_data_raw()
    } else {
      filter_guids <- content() |>
        filter(app_mode %in% input$app_mode_filter) |>
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
        last_viewed_at = max(timestamp, na.rm = TRUE),
        .groups = "drop"
      )

    # Prepare sparkline data as a list column of numeric vectors.
    all_dates <- seq.Date(input$date_range[1], input$date_range[2], by = "day")
    daily_usage <- usage_data_visits() |>
      count(content_guid, date = date(timestamp)) |>
      complete(date = all_dates, nesting(content_guid), fill = list(n = 0)) |>
      group_by(content_guid) |>
      summarize(sparkline = list(n), .groups = "drop")

    content() |>
      mutate(owner_username = map_chr(owner, "username")) |>
      select(title, content_guid = guid, owner_username) |>
      right_join(usage_summary, by = "content_guid") |>
      right_join(daily_usage, by = "content_guid") |>
      arrange(desc(total_views)) |>
      select(content_guid, title, owner_username, total_views, sparkline, unique_viewers, last_viewed_at)
  })

  output$summary_text <- renderText(
    glue::glue(
      "{nrow(usage_data_visits())} visits ",
      "across {nrow(content_usage_data())} content items."
    )
  )

  # Main content table ----
  output$content_usage_table <- renderReactable({
    data <- content_usage_data() |>
      select(-content_guid)
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

        title = colDef(name = "Content", defaultSortOrder = "asc"),

        owner_username = colDef(name = "Owner", defaultSortOrder = "asc", minWidth = 75),

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
          name = "",
          align = "center",
          width = 90,
          sortable = FALSE,
          cell = function(value) {
            # Use sparkline::spk_chr() to generate the sparkline HTML.
            sparkline::sparkline(value, type = "bar", barColor = "#7494b1", disableTooltips = TRUE, barWidth = 8, chartRangeMin = TRUE)
          }
        ),

        unique_viewers = colDef(
          name = "Unique Visitors",
          align = "left",
          minWidth = 70,
          maxWidth = 120,
          cell = function(value) {
            max_val <- max(data$total_views, na.rm = TRUE)
            format(value, width = nchar(max_val), justify = "right")
          },
          class = "number"
        ),

        last_viewed_at = colDef(
          name = "Last Viewed",
          align = "right",
          width = 150,
          cell = function(value) {
            format(as.POSIXct(value), "%Y-%m-%d %H:%M:%S")
          }
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