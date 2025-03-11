library(shiny)
library(bslib)
library(shinyjs)
library(DT)
library(dplyr)
library(purrr)
library(connectapi)
library(pins)
library(tidyr)

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
      card_body(textOutput("data_note"), fill = FALSE),
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
    get_content(client)
  }) |> bindCache("static_key")

  users <- reactive({
    get_users(client) |>
      mutate(full_name = paste(first_name, last_name)) |>
      select(user_guid = guid, username, full_name)
  }) |> bindCache("static_key")

  # No need to cache, as it is only loaded when audit_log_summary is refreshed
  # (and is already cached in a pin).
  audit_logs <- reactive({
    board <- board_connect()
    PIN_NAME <- paste0(board$account, "/", "connect_metrics_cache_audit_logs")
    pin_read(board, PIN_NAME)
  })

  audit_log_summary <- reactive({
    audit_logs() |>
      filter(action %in% c("deploy_application", "add_application")) |>
      group_by(user_guid, action) |>
      summarize(
        n = n(),
        latest = max(time),
        .groups = "drop"
      ) |>
      pivot_wider(names_from = action, values_from = c(n, latest), values_fill = list(n = 0)) |>
      inner_join(users()) |>
      select(
        username,
        full_name,
        n_add_app = n_add_application,
        n_deploy = n_deploy_application,
        latest_deploy = latest_deploy_application
      )
  }) |> bindCache("static_key")

  # Cached on the same cadence as audit_log_summary to avoid loading audit logs
  # when not required.
  earliest_record <- reactive({
    min(audit_logs()$time)
  }) |> bindCache("static_key")

  output$data_note <- renderText(
    paste(
      "Earliest data loaded:",
      earliest_record()
    )
  )

  output$user_table <- renderDT({
    print(names(audit_log_summary()))
    datatable(
      audit_log_summary(),
      options = list(
        order = list(list(3, "desc")),
        paging = FALSE,
        searching = FALSE
      ),
      filter = "top",
      colnames = c(
        "Username" = "username",
        "User" = "full_name",
        "Number of New Content Items" = "n_add_app",
        "Number of Deploys" = "n_deploy",
        "Time of Latest Deploy" = "latest_deploy"
      )
    ) |>
      formatDate(columns = "Time of Latest Deploy", method = "toLocaleString")
  })
}

shinyApp(ui, server)
