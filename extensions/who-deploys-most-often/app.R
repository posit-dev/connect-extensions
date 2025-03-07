library(shiny)
library(bslib)
library(dplyr)
library(purrr)
library(connectapi)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 12)
)

ui <- page_fluid(
  theme = bs_theme(version = 5),

  card(
    card_header("Who Deploys Most Often"),
    layout_sidebar(
      sidebar = sidebar(
        title = "No Filters Yet",
        open = FALSE
      ),
      card_body("Note: `n_bundles` currently uses synthetic data."),
      card(
        tableOutput("user_table")
      )
    )
  )
)

server <- function(input, output, session) {
  client <- connect()

  # Load data
  content <- reactive({
    get_content(client) |>
      # Fake data, to be replaced with real data later.
      mutate(n_bundles = rpois(n(), 3))
  }) |> bindCache("static_key")

  user_table <- reactive({
    content() |>
      # The `owner` column is a nested list-column.
      # We extract the requisite metadata up to be first-class atomic vector columns.
      mutate(
        username = map_chr(owner, "username"),
        user_full_name = paste(map_chr(owner, "first_name"), map_chr(owner, "last_name"))
      ) |>
      group_by(username) |>
      summarize(
        user_full_name = first(user_full_name),
        n_bundles = sum(n_bundles),
        n_content_items = n(),
        last_deploy = format(max(last_deployed_time, na.rm = TRUE), "%Y-%m-%d at %I:%M %p")
      ) |>
      arrange(desc(n_content_items))
  }) |> bindCache("static_key")

  output$user_table <- renderTable({user_table()})
}

shinyApp(ui, server)
