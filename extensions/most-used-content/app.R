library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(dplyr)
library(purrr)
library(lubridate)

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
        title = "No Filters Yet",
        open = FALSE
      ),
      card(
        DTOutput(
          "content_usage_table"
        )
      )
    )
  )
)

server <- function(input, output, session) {
  client <- connect()


  # Default dates. "This week" is best "common sense" best represented by six
  # days ago thru the end of today. Without these, content takes too long to
  # display on some servers.
  date_range <- reactive({
    list(
      from_date = today() - ddays(6),
      to_date = today()
    )
  })

  content <- reactive({
    get_content(client)
  }) |> bindCache("static_key")

  usage_data <- reactive({
    get_usage(
      client,
      from = format(date_range()$from_date, "%Y-%m-%dT%H:%M:%SZ"),
      to = format(date_range()$to_date + hours(23) + minutes(59) + seconds(59), "%Y-%m-%dT%H:%M:%SZ")
    )
  }) |> bindCache(date_range()$from_date, date_range()$to_date)

  # Compute basic usage stats
  content_usage_data <- reactive({
    usage_summary <- usage_data() |>
      group_by(content_guid) |>
      summarize(
        total_views = n(),
        unique_viewers = n_distinct(user_guid, na.rm = TRUE),
        last_viewed_at = max(timestamp, na.rm = TRUE)
      )

    content() |>
      mutate(owner_username = map_chr(owner, "username")) |>
      select(title, content_guid = guid, owner_username) |>
      right_join(usage_summary, by = "content_guid") |>
      arrange(desc(total_views))
  }) |> bindCache(date_range()$from_date, date_range()$to_date)

    output$content_usage_table <- renderDT({
      datatable(
        content_usage_data(),
        options = list(
          order = list(list(4, "desc")),
          paging = FALSE
        ),
        colnames = c(
          "Content Title" = "title",
          "Content GUID" = "content_guid",
          "Owner Username" = "owner_username",
          "Total Views" = "total_views",
          "Unique Logged-in Viewers" = "unique_viewers",
          "Last Viewed At" = "last_viewed_at"
        )
      ) |>
        formatDate(columns = "Last Viewed At", method = "toLocaleString")

    })
}

shinyApp(ui, server)
