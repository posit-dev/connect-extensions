library(shiny)
library(bslib)
library(shinyjs)
library(DT)
library(dplyr)
library(purrr)
library(connectapi)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 12)
)

ui <- page_fillable(
  useShinyjs(),

  theme = bs_theme(version = 5),

  card(
    card_header("Who Deploys Most Often"),
    layout_sidebar(
      sidebar = sidebar(
        title = "Filter Data",
        open = FALSE,
        checkboxInput("enable_date", "Filter Deploys", value = FALSE),

        dateRangeInput(
          "date_range",
          label = "Date Range",
          start = Sys.Date() - 7,
          end = Sys.Date(),
          min = "2020-01-01",
          max = Sys.Date()
        )

      ),
      card_body("Note: \"Number of Deploys\" is using synthetic data.", fill = FALSE),
      card(
        DTOutput("user_table")
      )
    )
  )
)

server <- function(input, output, session) {
  # Enable or disable the date range filter.
  observe({
    if (input$enable_date) {
      print("enableing date range")
      enable("date_range")
    } else {
      print("disabling date range")
      disable("date_range")
    }
  })


  client <- connect()

  # Load data
  content <- reactive({
    get_content(client) |>
      # Fake data, to be replaced with real data later.
      mutate(n_bundles = rpois(n(), 3))
  }) |> bindCache("static_key")

  content_by_user <- reactive({
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
        n_content_items = n(),
        n_bundles = sum(n_bundles),
        last_deploy = max(last_deployed_time)
      )
  }) |> bindCache("static_key")

  output$user_table <- renderDT({
    datatable(
      content_by_user(),
      options = list(
        order = list(list(3, "desc")),
        paging = FALSE
      ),
      colnames = c(
        "User" = "user_full_name",
        "Number of Content Items" = "n_content_items",
        "Number of Deploys" = "n_bundles",
        "Time of Last Deploy" = "last_deploy"
      )
    ) |>
      formatDate(columns = "Time of Last Deploy", method = "toLocaleString")
  })
}

shinyApp(ui, server)
