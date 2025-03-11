library(shiny)
library(bslib)
library(shinyjs)
library(DT)
library(dplyr)
library(purrr)
library(connectapi)

source("functions.R")

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 24)
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
        actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
      ),
      card_body(textOutput("bundle_count_method"), fill = FALSE),
      card(
        DTOutput("user_table")
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

  # Data processing ----

  client <- connect()

  # Load data
  content <- reactive({
    content <- get_content(client)
    bundle_count_method <- NA
    tryCatch(
      {
        # Number of bundles is summed per content item.
        time_taken <- system.time({
          content$n_bundles <- content |>
            as_content_list(client) |>
            map_int(function(x) nrow(get_bundles(x)))
        })
        print(paste0("Fetched bundles for ", nrow(content), " content items."))
        print(paste("Time elapsed:", time_taken["elapsed"]))
        list(
          content = content,
          bundle_count_method = "per_content"
        )
      },
      error = function(e) {
        print("Unable to use bundle count method")
        print(e)
        # Fake data, to be replaced with real data later.
        # Note: The number of bundles will be aggregated from apps, won't include collaborators, because we don't have that info.
        content <- content|>
          mutate(n_bundles = rpois(n(), 3))
        list(
          content = content,
          bundle_count_method = "synthetic"
        )
      }
    )

  }) |> bindCache("static_key")

  output$bundle_count_method <- renderText({
      switch(
      content()$bundle_count_method,
      "per_content" = paste0(
        "Note: \"Number of Deploys\" was generated using total bundle counts from each ",
        "user's owned content. Bundles published by collaborators count towards ",
        "content owners' totals."
      ),
      "synthetic" = "Note: \"Number of Deploys\" uses synthetic data."
    )
  })

  content_by_user <- reactive({
    content()$content |>
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
        paging = FALSE,
        searching = FALSE
      ),
      filter = "top",
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
