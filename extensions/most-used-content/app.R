library(shiny)
library(bslib)
library(gt)
library(connectapi)
library(dplyr)
library(purrr)
library(lubridate)
library(ggplot2)
library(plotly)
library(tidyr)
library(svglite) # required by gtExtras

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

ui <- page_fillable(
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
          max = today(),
        ),

        actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
      ),

      card(
        gt_output("content_usage_table")
      )
    )
  )
)

server <- function(input, output, session) {
  # Cache invalidation button ----
  cache <- cachem::cache_disk("./app_cache/cache/")
  observeEvent(input$clear_cache, {
    print("Cache cleared!")
    cache$reset()  # Clears all cached data
    session$reload()  # Reload the app to ensure fresh data
  })

  # Loading and processing data ----
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

  # Compute basic usage stats ----
  content_usage_data <- reactive({
    usage_summary <- usage_data() |>
      group_by(content_guid) |>
      summarize(
        total_views = n(),
        unique_viewers = n_distinct(user_guid, na.rm = TRUE),
        last_viewed_at = max(timestamp, na.rm = TRUE)
      )


    # Add sparkline ----
    all_dates <- seq.Date(input$date_range[1], input$date_range[2], by = "day")

    daily_usage <- usage_data() |>
      count(content_guid, date = date(timestamp)) |>
      complete(date = all_dates, nesting(content_guid), fill = list(n = 0)) |>
      group_by(content_guid) |>
      summarize(sparkline = list(n))

    # Combine ----

    content() |>
      mutate(owner_username = map_chr(owner, "username")) |>
      select(title, content_guid = guid, owner_username) |>
      right_join(usage_summary, by = "content_guid") |>
      right_join(daily_usage, by = "content_guid") |>
      arrange(desc(total_views)) |>
      select(-content_guid)
  }) |> bindCache(input$date_range)



  # Render table
  output$content_usage_table <- render_gt({
    content_usage_data() |>
      mutate(view_bar = total_views) |>
      relocate(view_bar, .before = 1) |>
      gt() |>
      cols_label(
        view_bar = "",
        title = "Content",
        owner_username = "Owner",
        total_views = "Visits",
        unique_viewers = "Unique Visitors",
        last_viewed_at = "Last Viewed",
        sparkline = "Sparkline"
      ) |>
      fmt_datetime(
        columns = last_viewed_at,
        date_style = "iso"
      ) |>
      gtExtras::gt_plt_bar(
        view_bar,
        "grey",
        width = 30
      ) |>
      gtExtras::gt_plt_sparkline(
        sparkline,
        same_limit = TRUE,
        palette = c("black", rep("transparent", 4)),
        label = FALSE
      ) |>
      cols_align(
        align = "left", columns = c("sparkline")
      ) |>
      tab_options(
        column_labels.font.weight = "bold"
      )
  })
}

shinyApp(ui, server)
