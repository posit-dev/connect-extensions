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
library(bslib)
library(ggplot2)
library(plotly)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

extract_guid <- function(raw) {
  guid_pattern <- "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
  match <- regmatches(raw, regexpr(guid_pattern, raw))
  if (length(match) == 1) {
    match
  } else {
    raw
  }
}

source("get_usage.R")

ui <- function(request) {
  page_fluid(
    useShinyjs(),
    theme = bs_theme(version = 5),

    div(
      id = "guid_input_panel",
      textInput("guid_field", "Paste in a content GUID or URL"),
      actionButton("submit_guid", "Go", icon("arrow-right"))
    ),

    div(
      id = "dashboard_panel",
      style = "display:none;",
      card(
        card_header(
          tags$div(
            style = "display: flex; align-items: center; gap: 0.5rem;",
            actionButton("clear_guid", "Back", icon("arrow-left"), class = "btn btn-sm"),
            span("Content Detail")
          )
        ),
        layout_sidebar(
          sidebar = sidebar(
            title = "Controls",
            open = TRUE,

            selectInput(
              "date_range_choice",
              label = "Date Range",
              choices = c("1 Week", "30 Days", "90 Days", "Custom"),
              selected = "1 Week"
            ),

            conditionalPanel(
              condition = "input.date_range_choice === 'Custom'",
              dateRangeInput(
                "date_range",
                label = NULL,
                start = today() - days(6),
                end = today(),
                max = today()
              )
            ),

            sliderInput(
              "visit_lag_cutoff_slider",
              label = "Visit Merge Window (sec)",
              min = 0,
              max = 180,
              value = 1,
              step = 0.5
            ),

            textInput(
              "visit_lag_cutoff_text",
              label = NULL,
              value = 1
            ),

            actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
          ),

          layout_columns(
            uiOutput("content_title"),
            div(style = "margin-left: auto;", uiOutput("owner_info"))
          ),

          uiOutput("filter_message"),

          layout_column_wrap(
            width = "400px",
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
                title = tagList(
                  "Top Visitors",
                  tooltip(
                    bs_icon("question-circle-fill", class = "ms-2"),
                    "Click a row to show only that user's visits."
                  )
                ),
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
    ),
    tags$script(HTML("
      document.addEventListener('DOMContentLoaded', function() {
        const input = document.getElementById('guid_field');
        if (input) {
          input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
              e.preventDefault();
              document.getElementById('submit_guid').click();
            }
          });
        }
      });
    "))
  )
}

server <- function(input, output, session) {
  observe({
    setBookmarkExclude(setdiff(names(input), "guid_field"))
  })
  onBookmarked(function(url) {
    message("Bookmark complete. URL: ", url)
    updateQueryString(url)
  })
  onRestore(function(state) {
    guid <- extract_guid(input$guid_field)
    if (guid %in% content()$guid) {
      resolved_guid(guid)
    } else {
      resolved_guid(NULL)
    }
  })

  # Handle GUID input ----

  resolved_guid <- reactiveVal()


  observeEvent(input$submit_guid, {
    raw_guid <- input$guid_field
    guid <- extract_guid(raw_guid)

    if (guid %in% content()$guid) {
      freezeReactiveValue(input, "guid_field")
      updateTextInput(session, "guid_field", value = guid)
      resolved_guid(guid)
    } else {
      resolved_guid(NULL)
    }
  })

  # Update the bookmark when a valid GUID is input
  observeEvent(input$guid_field, {
    req(!is.null(input$guid_field), input$guid_field %in% content()$guid)
    session$doBookmark()
  }, ignoreInit = TRUE)

  observe({
    shinyjs::toggle(id = "guid_input_panel", condition = is.null(resolved_guid()))
    shinyjs::toggle(id = "dashboard_panel", condition = !is.null(resolved_guid()))
  })

  # Back button logic ----

  observeEvent(input$clear_guid, {
    resolved_guid(NULL)    # Hide dashboard
    updateTextInput(session, "guid_field", value = "")

    updateSliderInput(session, "visit_lag_cutoff_slider", value = 1)
    updateTextInput(session, "visit_lag_cutoff_text", value = "1")
    updateReactable("aggregated_visits", selected = NA)

    updateQueryString("?", mode = "replace")
  })

  # Cache invalidation button ----
  cache <- cachem::cache_disk("./app_cache/cache/")
  observeEvent(input$clear_cache, {
    print("Cache cleared!")
    cache$reset()  # Clears all cached data
    session$reload()  # Reload the app to ensure fresh data
  })

  # Sync slider and text input ----

  observeEvent(input$visit_lag_cutoff_slider, {
    if (input$visit_lag_cutoff_slider != input$visit_lag_cutoff_text) {
      updateTextInput(session, "visit_lag_cutoff_text", value = input$visit_lag_cutoff_slider)
    }
  })

  observeEvent(input$visit_lag_cutoff_text, {
    new_value <- suppressWarnings(as.numeric(input$visit_lag_cutoff_text))

    if (!is.na(new_value) && new_value >= 0 && new_value <= 600) {
      if (new_value != input$visit_lag_cutoff_slider) {
        updateSliderInput(session, "visit_lag_cutoff_slider", value = new_value)
      }
    } else {
      if (input$visit_lag_cutoff_text != input$visit_lag_cutoff_slider) {
        updateTextInput(session, "visit_lag_cutoff_text", value = input$visit_lag_cutoff_slider)
      }
    }
  })

  # Loading and processing data ----
  print(paste("Session token:", session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN))
  client <- connect(token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN)
  authed_user_guid <- client$me()$guid

  date_range <- reactive({
    switch(input$date_range_choice,
            "1 Week" = c(today() - days(6), today()),
            "30 Days" = c(today() - days(29), today()),
            "90 Days" = c(today() - days(89), today()),
            "Custom" = input$date_range)
  })

  content <- reactive({
    # Grab the entire content data frame here and filter it using the pasted-in
    # GUID to obtain content title and other metadata, rather than making a
    # request to `v1/content/{GUID}`. If this were a prod, standalone dashboard,
    # might be better to call that endpoint.
    get_content(client)
  }) |> bindCache(authed_user_guid, "static_key")

  users <- reactive({
    get_users(client) |>
      mutate(
        full_name = paste(first_name, last_name),
        display_name = paste0(full_name, " (", username, ")")
      ) |>
      select(user_guid = guid, full_name, username, display_name, email)
  }) |> bindCache(authed_user_guid, "static_key")

  firehose_usage_data <- reactive({
    get_usage(
      client,
      from = date_range()[1],
      to = date_range()[2]
    )
  }) |> bindCache(authed_user_guid, date_range())

  selected_content_usage <- reactive({
    firehose_usage_data() |>
      filter(content_guid == input$guid_field)
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
    print(filter_selection)
    if (isTruthy(filter_selection)) {
      filter_guids <- aggregated_visits_data()[filter_selection, ] |>
        pull(user_guid)
      print(filter_guids)
      all_visits |>
        filter(if (length(filter_guids) == 0) TRUE else user_guid %in% filter_guids)
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
      select(user_guid, display_name, email, n_visits)
  })

  selected_content_info <- reactive({
    filter(content(), guid == input$guid_field)
  })

  # Create day by day hit data for plot
  daily_hit_data <- reactive({
    all_dates <- seq.Date(date_range()[1], date_range()[2], by = "day")

    all_visits_data() |>
      mutate(date = date(timestamp)) |>
      group_by(date) |>
      summarize(daily_visits = n(), .groups = "drop") |>
      tidyr::complete(date = all_dates, fill = list(daily_visits = 0))
  })

  # Render tabular output ----

  output$aggregated_visits <- renderReactable({
    reactable(
      aggregated_visits_data(),
      selection = "multiple",
      onClick = "select",
      defaultSorted = "n_visits",
      columns = list(
        user_guid = colDef(show = FALSE),
        display_name = colDef(name = "Visitor"),
        email = colDef(
          name = "",
          width = 32,
          sortable = FALSE,
          cell = function(url) {
            if (is.na(url) || url == "") return("")
            HTML(as.character(tags$div(
              onclick = "event.stopPropagation()",
              tags$a(
                href = glue("mailto:{url}"),
                bs_icon("envelope")
              )
            )))
          },
          html = TRUE
        ),
        n_visits = colDef(
          name = "Visits",
          defaultSortOrder = "desc",
          maxWidth = 75
        )
      )
    )
  })

  output$all_visits <- renderReactable({
    reactable(
      all_visits_data(),
      defaultSorted = "timestamp",
      columns = list(
        user_guid = colDef(show = FALSE),
        timestamp = colDef(
          name = "Time",
          format = colFormat(datetime = TRUE, time = TRUE),
          defaultSortOrder = "desc"
        ),
        display_name = colDef(name = "Visitor")
      )
    )
  })

  # Render content metadata and other text ----

  output$filter_message <- renderUI({
    # req(getReactableState("aggregated_visits", "selected"))
    hits <- all_visits_data()
    glue(
      "{nrow(hits)} visits between ",
      "{date_range()[1]} and {date_range()[2]}."
    )
    if (isTruthy(getReactableState("aggregated_visits", "selected"))) {
      users <- aggregated_visits_data()[getReactableState("aggregated_visits", "selected"), "display_name", drop = TRUE]
      user_string <- if (length(users) == 1) users else "selected users"
      div(
        glue(
          "{nrow(hits)} visits from {user_string} between ",
          "{date_range()[1]} and {date_range()[2]}."
        ),
        actionLink("clear_selection", glue::glue("Clear filter"), icon = icon("times"))
      )
    } else {
      div(
        glue(
          "{nrow(hits)} total visits between ",
          "{date_range()[1]} and {date_range()[2]}."
        )
      )
    }
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


  # Output plots ----

  output$daily_visits_plot <- renderPlotly({
    p <- ggplot(
      daily_hit_data(),
      aes(x = date, y = daily_visits, text = paste("Date:", date, "<br>Visits:", daily_visits))) +
      geom_bar(stat = "identity") +
      labs(title = "Visits per Day", y = "Visits", x = "Date")
    ggplotly(p, tooltip = "text")
  })
}

enableBookmarking("url")
shinyApp(ui, server)
