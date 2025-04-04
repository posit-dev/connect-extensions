library(shiny)
library(bslib)
library(shinyjs)
library(connectapi)
library(dplyr)
library(glue)
library(lubridate)
library(tidyr)
library(reactable)
library(bsicons)
library(ggplot2)
library(plotly)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

ui <- page_fluid(
  useShinyjs(),
  theme = bs_theme(version = 5),

  card(
    card_header("Content Detail"),
    layout_sidebar(
      sidebar = sidebar(
        title = "Dev Controls",
        open = TRUE,

        textInput(
          "content_guid",
          "Content GUID"
        ),

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

      uiOutput("content_title"),

      layout_columns(
        card(
          textOutput("summary_message"),
          fill = FALSE
        ),
        card(
          uiOutput("owner_info"),
          fill = FALSE
        ),
        fill = FALSE
      ),

      uiOutput("filter_message"),
      # conditionalPanel(
      #   condition = "input.selectedRow != null",
      #   textOutput("filter_message")
      # ),

      layout_column_wrap(
        width = "300px",
        card(
          plotlyOutput("daily_visits_plot"),
          # min_height = "300px",
          height = "350px",
          max_width = "500px",
          fill = FALSE
        ),

        navset_card_tab(
          id = "content_visit_tables",
          tabPanel(
            "Top Visitors",
            reactableOutput("aggregated_visits")
          ),
          tabPanel(
            "List of Visits",
            reactableOutput("all_visits")
          )
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

  users <- reactive({
    get_users(client) |>
      mutate(
        full_name = paste(first_name, last_name),
        display_name = paste0(full_name, " (", username, ")")
      ) |>
      select(user_guid = guid, full_name, username, display_name, email)
  }) |> bindCache("static_key")

  firehose_usage_data <- reactive({
    get_usage(
      client,
      from = date_range()$from_date,
      to = date_range()$to_date + hours(23) + minutes(59) + seconds(59)
    )
  }) |> bindCache(date_range()$from_date, date_range()$to_date)

  # For demo purposes, this content pre-populates itself with the most popular guid.
  observe({
    default_guid <- firehose_usage_data() |>
        count(content_guid) |>
        slice_max(n) |>
        pull(content_guid)
    if (length(default_guid) == 1 && nchar(input$content_guid) == 0) {
      updateTextInput(session, "content_guid", value = default_guid)
    }
  })

  selected_content_usage <- reactive({
    firehose_usage_data() |>
      filter(content_guid == input$content_guid)
  })

  # Compute data
  all_visits_data <- reactive({
    all_visits <- selected_content_usage() |>

      # Compute time diffs and filter out hits within the session
      group_by(user_guid) |>
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > input$visit_lag_cutoff_slider) |>
      ungroup() |>

      # Join to usernames
      left_join(users(), by = "user_guid") |>
      replace_na(list(display_name = "[Anonymous]")) |>
      arrange(desc(timestamp)) |>
      select(user_guid, display_name, timestamp)

    # Conditionally filter by selection from other table
    filter_selection <- getReactableState("aggregated_visits", "selected")
    if (isTruthy(filter_selection)) {
      filter_guid <- aggregated_visits_data()[filter_selection, ] |>
        pull(user_guid)
      all_visits |>
        filter(if (is.na(filter_guid)) is.na(user_guid) else user_guid == filter_guid)
    } else {
      all_visits
    }
  })

  aggregated_visits_data <- reactive({
    unfiltered_hits <- selected_content_usage() |>
      group_by(user_guid) |>
      summarize(n_hits = n())

    filtered_visits <- selected_content_usage() |>
      group_by(user_guid) |>

      # Compute time diffs and filter out hits within the session
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > input$visit_lag_cutoff_slider) |>

      summarize(n_visits = n())

    filtered_visits |>
      left_join(unfiltered_hits, by = "user_guid") |>
      left_join(users(), by = "user_guid") |>
      replace_na(list(display_name = "[Anonymous]")) |>
      arrange(desc(n_visits)) |>
      select(user_guid, display_name, n_visits)
  })

  selected_content_info <- reactive({
    filter(content(), guid == input$content_guid)
  })

  # Create day by day hit data for plot
  daily_hit_data <- reactive({
    all_dates <- seq.Date(date_range()$from_date, date_range()$to_date, by = "day")

    all_visits_data() |>
      mutate(date = date(timestamp)) |>
      group_by(date) |>
      summarize(daily_visits = n(), .groups = "drop") |>
      tidyr::complete(date = all_dates, fill = list(daily_visits = 0))
  })

  # Render tabular output ----

  output$summary_message <- renderText(summary_message())
  output$aggregated_visits <- renderReactable({
    reactable(
      aggregated_visits_data(),
      selection = "single",
      onClick = "select",
      columns = list(
        user_guid = colDef(show = FALSE),
        display_name = colDef(name = "Visitor"),
        n_visits = colDef(name = "Visits")
      )
    )
  })

  output$all_visits <- renderReactable({
    reactable(
      all_visits_data(),
      columns = list(
        user_guid = colDef(show = FALSE),
        timestamp = colDef(
          name = "Time",
          format = colFormat(datetime = TRUE, time = TRUE)
        ),
        display_name = colDef(name = "Visitor")
      )
    )
  })

  # Render content metadata and other text ----

  output$filter_message <- renderUI({
    req(getReactableState("aggregated_visits", "selected"))
    user <- aggregated_visits_data()[getReactableState("aggregated_visits", "selected"), "display_name", drop = TRUE]

    div(
      style = "margin-bottom: 1em;",
      actionLink("clear_selection", glue::glue("Only showing visits by {user}"), icon = icon("times"))
    )
  })

  observeEvent(input$clear_selection, {
    updateReactable("aggregated_visits", selected = NA)
  })

  output$content_title <- renderUI({
    req(selected_content_info())
    title_text <- selected_content_info()$title
    open_url <- selected_content_info()$dashboard_url
    icon_html <- bs_icon("arrow-up-right-square")
    HTML(glue::glue(
      "<h3>{title_text} <a href='{open_url}' target='_blank'>{icon_html}</a></h3>"
    ))
  })

  output$owner_info <- renderUI({
    req(selected_content_info())
    if (nrow(selected_content_info()) == 1) {
      owner <- filter(users(), user_guid == selected_content_info()$owner[[1]]$guid)
      icon_html <- bs_icon("envelope")  # Using bsicons

      HTML(glue::glue(
        "<p>Owner: {owner$display_name} <a href='mailto:{owner$email}'>{icon_html}</a></p>"
      ))
    }
  })

  summary_message <- reactive({
    content_title <- selected_content_info()$title
    hits <- all_visits_data()
    glue(
      "{nrow(hits)} visits between ",
      "{date_range()$from_date} and {date_range()$to_date}."
    )
  })


  # Output plot ----

  output$daily_visits_plot <- renderPlotly({
    p <- ggplot(
      daily_hit_data(),
      aes(x = date, y = daily_visits, text = paste("Date:", date, "<br>Visits:", daily_visits))) +
      geom_bar(stat = "identity") +
      labs(title = "Visits per Day", y = "Visits", x = "Date")
    ggplotly(p, tooltip = "text")
  })
}

shinyApp(ui, server)
