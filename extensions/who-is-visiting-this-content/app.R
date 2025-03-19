library(shiny)
library(bslib)
library(shinyjs)
library(connectapi)
library(dplyr)
library(glue)
library(lubridate)
library(tidyr)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

ui <- page_fillable(
  useShinyjs(),
  theme = bs_theme(version = 5),

  card(
    card_header("Who is Visiting This Content?"),
    layout_sidebar(
      sidebar = sidebar(
        title = "Filters",
        open = TRUE,

        sliderInput(
          "visit_lag_cutoff_slider",
          label = "Visit Merge Window (sec)",
          min = 0,
          max = 600,
          value = 1,
          step = 0.5
        ),

        textInput(
          "visit_lag_cutoff_text",
          label = "Visit Merge Window (sec)",
          value = 1
        ),

        actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
      ),

      textInput(
        "content_guid",
        "Content GUID"
      ),

      h4(
        id = "guid_input_msg",
        "Please enter a content GUID"
      ),

      textOutput("summary_message"),

      tabsetPanel(
        id = "content_visit_tables",
        tabPanel(
          "List of Visits",
          tableOutput("all_visits")
        ),
        tabPanel(
          "Aggregated Visits",
          tableOutput("aggregated_visits")
        )
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

  observe({
    if (nchar(input$content_guid) == 0) {
      show("guid_input_msg")
      hide("content_visit_tables")
    } else {
      hide("guid_input_msg")
      show("content_visit_tables")
    }
  })

  # Sync slider and text input ----

  observeEvent(input$visit_lag_cutoff_slider, {
    updateTextInput(session, "visit_lag_cutoff_text", value = input$visit_lag_cutoff_slider)
  })

  observeEvent(input$visit_lag_cutoff_text, {
    new_value <- suppressWarnings(as.numeric(input$visit_lag_cutoff_text))

    if (!is.na(new_value) && new_value >= 0 && new_value <= 600) {
      updateSliderInput(session, "visit_lag_cutoff_slider", value = new_value)
    } else {
      updateTextInput(session, "visit_lag_cutoff_text", value = input$visit_lag_cutoff_slider)
    }
  })


  # Loading and processing data ----
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
    # Grab the entire content data frame here and filter it using the pasted-in
    # GUID to obtain content title and other metadata, rather than making a
    # request to `v1/content/{GUID}`. If this were a prod, standalone dashboard,
    # might be better to call that endpoint.
    get_content(client)
  }) |> bindCache("static_key")

  user_names <- reactive({
    get_users(client) |>
      mutate(full_name = paste(first_name, last_name)) |>
      select(user_guid = guid, full_name, username)
  }) |> bindCache("static_key")

  usage_data <- reactive({
    get_usage(
      client,
      from = date_range()$from_date,
      to = date_range()$to_date + hours(23) + minutes(59) + seconds(59)
    )
  }) |> bindCache(date_range()$from_date, date_range()$to_date)

  # Compute data
  all_visits_data <- reactive({
    usage_data() |>
      filter(content_guid == input$content_guid) |>

      # Compute time diffs and filter out hits within the session
      group_by(user_guid) |>
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > input$visit_lag_cutoff_slider) |>
      ungroup() |>

      # Join to usernames
      left_join(user_names(), by = "user_guid") |>
      replace_na(list(full_name = "[Anonymous]")) |>
      arrange(desc(timestamp)) |>
      select(timestamp, full_name, username)
  })

  aggregated_visits_data <- reactive({
    unfiltered_hits <- usage_data() |>
      filter(content_guid == input$content_guid) |>
      group_by(user_guid) |>
      summarize(n_hits = n())

    filtered_visits <- usage_data() |>
      filter(content_guid == input$content_guid) |>
      group_by(user_guid) |>

      # Compute time diffs and filter out hits within the session
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > input$visit_lag_cutoff_slider) |>

      summarize(n_visits = n())

    filtered_visits |>
      left_join(unfiltered_hits, by = "user_guid") |>
      left_join(user_names(), by = "user_guid") |>
      replace_na(list(full_name = "[Anonymous]")) |>
      arrange(desc(n_visits)) |>
      select(n_visits, n_hits, full_name, username)


  })

  summary_message <- reactive({
    content_title <- content() |>
      filter(guid == input$content_guid) |>
      pull(title)
    hits <- all_visits_data()
    glue(
      "Content '{content_title}' had {nrow(hits)} visits between ",
      "{min(hits$timestamp)} and {max(hits$timestamp)}."
    )
  })


  output$summary_message <- renderText(summary_message())
  output$all_visits <- renderTable(
    all_visits_data() |>
      transmute(timestamp = format(timestamp, "%Y-%m-%d %H:%M:%S"), full_name, username) |>
      rename("Time" = timestamp, "Full Name" = full_name, "Username" = username)
  )
  output$aggregated_visits <- renderTable(
    aggregated_visits_data() |>
      rename(
        "Total Visits" = n_visits,
        "Number of Hits" = n_hits,
        "Full Name" = full_name,
        "Username" = username
      )
  )
}

shinyApp(ui, server)
