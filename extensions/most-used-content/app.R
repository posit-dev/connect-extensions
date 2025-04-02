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

bar_chart <- function(value, width = "100%", height = "1rem", fill = "#00bfc4", background = NULL) {
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
        title = "Controls",
        open = TRUE,
        width = 275,
        dateRangeInput(
          "date_range",
          label = "Select Date Range",
          start = today() - ddays(6),
          end = today(),
          max = today()
        ),
        actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
      ),
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

  usage_data <- reactive({
    get_usage(
      client,
      from = as.POSIXct(input$date_range[1]),
      to = as.POSIXct(input$date_range[2]) + hours(23) + minutes(59) + seconds(59)
    )
  }) |> bindCache(input$date_range)

  content_usage_data <- reactive({
    usage_summary <- usage_data() |>
      group_by(content_guid) |>
      summarize(
        total_views = n(),
        unique_viewers = n_distinct(user_guid, na.rm = TRUE),
        last_viewed_at = max(timestamp, na.rm = TRUE),
        .groups = "drop"
      )

    # Prepare sparkline data as a list column of numeric vectors.
    all_dates <- seq.Date(input$date_range[1], input$date_range[2], by = "day")
    daily_usage <- usage_data() |>
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
      # mutate(views_bar = total_views) |>
      # select(title, owner_username, total_views, views_bar, sparkline, unique_viewers, last_viewed_at)
      select(title, owner_username, total_views, sparkline, unique_viewers, last_viewed_at)
  }) |> bindCache(input$date_range)

  output$content_usage_table <- renderReactable({
    data <- content_usage_data()
    reactable(
      data,
      defaultSortOrder = "desc",
      pagination = FALSE,
      sortable = TRUE,
      highlight = TRUE,
      filterable = TRUE,
      columns = list(

        # views_bar = colDef(
        #   name = "",
        #   cell = function(value) {
        #     max_val <- max(data$total_views, na.rm = TRUE)
        #     pct <- round(100 * value / max_val)
        #     sprintf("
        #       <div style='background: #e0e0e0; width: 100%%; height: 1em;'>
        #         <div style='background: #1f77b4; width: %d%%; height: 100%%;'></div>
        #       </div>", pct
        #     )
        #   },
        #   align = "center",
        #   html = TRUE,
        #   width = 80
        # ),

        title = colDef(name = "Content", defaultSortOrder = "asc"),

        owner_username = colDef(name = "Owner", defaultSortOrder = "asc", minWidth = 80),

        total_views = colDef(
          name = "Visits",
          align = "left",
          minWidth = 75,
          cell = function(value) {
            width <- paste0(value * 100 / max(data$total_views, na.rm = TRUE), "%")
            bar_chart(value, width = width, fill = "#3fc1c9", background = "#e1e1e1")
          }
        ),

        unique_viewers = colDef(name = "Unique Visitors", align = "right", minWidth = 50),

        last_viewed_at = colDef(
          name = "Last Viewed",
          align = "right",
          cell = function(value) {
            format(as.POSIXct(value), "%Y-%m-%d %H:%M:%S")
          }
        ),

        sparkline = colDef(
          name = "",
          align = "center",
          width = 90,
          cell = function(value) {
            # Use sparkline::spk_chr() to generate the sparkline HTML.
            sparkline::sparkline(value, type = "bar", barColor = "gray", disableTooltips = TRUE, barWidth = 8)
          }
        )

      )
    )
  })
}

shinyApp(ui, server)