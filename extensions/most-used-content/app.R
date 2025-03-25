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
      summarize(sparkline_data = paste(n, collapse = ", "))

    # Combine ----

    content() |>
      mutate(owner_username = map_chr(owner, "username")) |>
      select(title, content_guid = guid, owner_username) |>
      right_join(usage_summary, by = "content_guid") |>
      right_join(daily_usage, by = "content_guid") |>
      arrange(desc(total_views)) |>
      select(-content_guid)
  }) |> bindCache(input$date_range)

  sparkline_options <- nanoplot_options(
    data_line_stroke_width = px(4),
    data_line_stroke_color = "gray",
    show_data_line = TRUE,
    show_data_points = FALSE,
    show_data_area = FALSE,
  )

  # Render table
  output$content_usage_table <- render_gt({
    content_usage_data() |>
      gt() |>
      cols_label(
        title = "Content",
        owner_username = "Owner",
        total_views = "Visits",
        unique_viewers = "Unique Visitors",
        last_viewed_at = "Last Viewed",
      ) |>
      fmt_datetime(
        columns = last_viewed_at,
        date_style = "iso"
      ) |>
      cols_nanoplot(
        columns = "sparkline_data",
        plot_type = "line",
        new_col_name = "sparkline",
        new_col_label = "Daily Visits",
        reference_line = 0
      ) |>
      cols_nanoplot(
        columns = "total_views",
        plot_type = "bar",
        new_col_name = "view_bar",
        new_col_label = "",
        before = "title",
        autohide = FALSE
      ) |>
      cols_width(view_bar ~ px(160)) |>
      tab_options(
        column_labels.font.weight = "bold"
      ) |>
      opt_interactive(
        use_pagination = FALSE,
        use_sorting = TRUE,
        use_text_wrapping = FALSE,
        use_highlight = TRUE
      )
  })
}

shinyApp(ui, server)
