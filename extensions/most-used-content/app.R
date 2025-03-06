library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(dplyr)
library(purrr)
library(lubridate)

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
          "content_usage"
        )
      )
    )
  )
)

server <- function(input, output, session) {
  client <- connect()

  content <- get_content(client)

  # Default dates. "This week" is best "common sense" best represented by six
  # days ago thru the end of today. Without these, content takes too long to
  # display on some servers.
  from_date <- today() - ddays(6)
  to_date <- today()
  from_time <- format(from_date, "%Y-%m-%dT%H:%M:%SZ")
  to_time <- format(to_date + hours(23) + minutes(59) + seconds(59), "%Y-%m-%dT%H:%M:%SZ")

  usage <- get_usage(
    client,
    from = from_time,
    to = to_time
  )

  # Compute basic usage stats
  usage_stats <- usage |>
    group_by(content_guid) |>
    summarize(
      total_views = n(),
      unique_viewers = n_distinct(user_guid, na.rm = TRUE),
      last_viewed_at = format(max(timestamp, na.rm = TRUE), "%Y-%m-%d at %I:%M %p")
    )

  content_usage <- content |>
    mutate(owner_username = map_chr(owner, "username")) |>
    select(title, content_guid = guid, owner_username) |>
    right_join(usage_stats, by = "content_guid") |>
    arrange(desc(total_views))

  output$content_usage <- renderDT(
    content_usage,
    options = list(
      order = list(list(4, "desc")),
      paging = FALSE
    ),
    colnames = c(
      "Content Title" = "title",
      "Content GUID" = "content_guid",
      "Owner Isername" = "owner_username",
      "Total Views" = "total_views",
      "Unique Logged-in Viewers" = "unique_viewers",
      "Last Viewed At" = "last_viewed_at"
    )
  )
}

shinyApp(ui, server)
