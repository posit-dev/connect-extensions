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
                "date_range_custom",
                label = NULL,
                start = today() - days(6),
                end = today(),
                max = today()
              )
            ),

            selectizeInput(
              "selected_users",
              label = "Filter Users",
              choices = NULL,  # set dynamically in server
              multiple = TRUE
            ),

            sliderInput(
              "visit_lag_cutoff_slider",
              label = "Visit Merge Window (sec)",
              min = 0,
              max = 180,
              value = 0,
              step = 0.5
            ),

            textInput(
              "visit_lag_cutoff_text",
              label = NULL,
              value = 0
            ),

            actionButton("clear_cache", "Clear Cache", icon = icon("refresh"))
          ),

          div(
            style = "display: flex; justify-content: space-between; gap: 1rem; align-items: center;",
            div(
              style = "display: inline-flex; gap: 0.5rem; align-items: center;",
              h3(textOutput("content_title")),
              uiOutput("dashboard_link")
            ),
            div(
              style = "display: flex; gap: 0.5rem; align-items: center;",
              textOutput("owner_info"),
              uiOutput("email_owner_link")
            )
          ),

          div(
            style = "display: flex; justify-content: space-between; align-items: center;",
            uiOutput("filter_message"),
            actionButton(
              "email_selected",
              label = div(
                style = "white-space: nowrap;",
                bs_icon("envelope"),
                "Email Selected Users"
              ),
              class = "btn btn-sm", disabled = TRUE,
            )
          ),

          layout_column_wrap(
            width = "400px",
            heights_equal = "row",
            navset_card_tab(
              tabPanel(
                "Daily Visits",
                div(
                  style = "height: 300px",
                  plotlyOutput("daily_visits_plot", height = "100%", width = "100%")
                )
              ),
              tabPanel(
                "Visit Timeline",
                div(
                  style = "height: 400px;",
                  uiOutput("visit_timeline_ui")
                )
              )
            ),

            navset_card_tab(
              tabPanel(
                title = tagList(
                  "Top Visitors",
                  tooltip(
                    bs_icon("info-circle-fill", class = "ms-2"),
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
    ")),
    tags$style(HTML("
      #selected_users + .selectize-control .selectize-input {
        max-height: 150px;
        overflow-y: auto;
      }
    "))
  )
}

server <- function(input, output, session) {
  # Bookmarking ----

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

    # TODO: Investigate why this does not work correctly on Connect.
    updateQueryString("?", mode = "replace")
  })

  # Cache invalidation button ----

  cache <- cachem::cache_disk("./app_cache/cache/")
  observeEvent(input$clear_cache, {
    print("Cache cleared!")
    cache$reset()  # Clears all cached data
    session$reload()  # Reload the app to ensure fresh data
  })

  # Visit Merge Window: sync slider and text input ----

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

  # User filter behaviors ----

  # Set choices initially
  observe({
    data <- aggregated_visits_data()
    updateSelectizeInput(
      session,
      "selected_users",
      choices = setNames(data$user_guid, data$display_name),
      server = TRUE
    )
  })

  # Selection syncing behavior is made more complex because the reactable data needs
  # to be sorted differently from data for the sidebar and plots for them to be
  # in the same order.

  # Sync table to sidebar
  observe({
    selected_guids_reactable <- aggregated_visits_reactable_data()[getReactableState("aggregated_visits", "selected"), "user_guid", drop = TRUE]
    # Get indices of selected reactable GUIDs from the main table
    all_guids <- aggregated_visits_data()$"user_guid"
    selected_guids <- all_guids[which(all_guids %in% selected_guids_reactable)]
    updateSelectizeInput(
      session,
      "selected_users",
      selected = selected_guids
    )
  })

  # Sync sidebar to table
  observeEvent(input$selected_users, {
    all_guids_reactable <- aggregated_visits_reactable_data()$user_guid
    selected_indices <- which(all_guids_reactable %in% input$selected_users)
    updateReactable("aggregated_visits", selected = selected_indices)
  }, ignoreNULL = FALSE)

  # Update action button depending on selection
  observe({
    sel <- input$selected_users
    updateActionButton(
      session, "email_selected",
      disabled = is.null(sel) || length(sel) == 0
    )
  })

  # Load and processing data ----

  client <- connect(token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN)
  authed_user_guid <- client$me()$guid

  date_range <- reactive({
    switch(input$date_range_choice,
            "1 Week" = list(from = today() - days(6), to = today()),
            "30 Days" = list(from = today() - days(29), to = today()),
            "90 Days" = list(from = today() - days(89), to = today()),
            "Custom" = list(from = input$date_range_custom[1], to = input$date_range_custom[2])
    )
  })

  content <- reactive({
    # Grab the entire content data frame here and filter it using the pasted-in
    # GUID to obtain content title and other metadata, rather than making a
    # request to `v1/content/{GUID}`.
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
      from = date_range()$from,
      to = date_range()$to
    )
  }) |> bindCache(authed_user_guid, date_range())

  selected_content_usage <- reactive({
    firehose_usage_data() |>
      filter(content_guid == input$guid_field)
  })

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

    # If any users are selected for filtering, filter by their GUIDs
    if (length(input$selected_users) > 0) {
      all_visits <- filter(all_visits, user_guid %in% input$selected_users)
    }
    all_visits
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
      arrange(desc(n_visits), display_name) |>
      select(user_guid, display_name, email, n_visits)
  })

  selected_content_info <- reactive({
    filter(content(), guid == input$guid_field)
  })

  # Render output tables ----

  # FIXME: This is required because the sort order handling of the reactable and
  # other elements (the timeline plot, selection in the sidebar) differs.
  aggregated_visits_reactable_data <- reactive({
    aggregated_visits_data() |>
      arrange(desc(n_visits), desc(display_name))
  })

  output$aggregated_visits <- renderReactable({
    reactable(
      aggregated_visits_reactable_data(),
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
            subject <- glue::glue("\"{selected_content_info()$title}\" on Posit Connect")
            mailto <- glue::glue("mailto:{url}?subject={URLencode(subject, reserved = TRUE)}")
            HTML(as.character(tags$div(
              onclick = "event.stopPropagation()",
              tags$a(
                href = mailto,
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
    hits <- all_visits_data()
    glue(
      "{nrow(hits)} visits between ",
      "{date_range()$from} and {date_range()$to}."
    )
    if (length(input$selected_users) > 0) {
      users <- aggregated_visits_data() |>
        filter(user_guid %in% input$selected_users) |>
        pull(display_name)
      user_string <- if (length(users) == 1) users else "selected users"
      div(
        glue(
          "{nrow(hits)} visits from {user_string} between ",
          "{date_range()$from} and {date_range()$to}."
        ),
        actionLink("clear_selection", glue::glue("Clear filter"), icon = icon("times"))
      )
    } else {
      div(
        glue(
          "{nrow(hits)} total visits between ",
          "{date_range()$from} and {date_range()$to}."
        )
      )
    }
  })

  observeEvent(input$clear_selection, {
    updateSelectizeInput(
      session,
      "selected_users",
      selected = NA
    )
  })

  output$content_title <- renderText({
    req(selected_content_info())
    selected_content_info()$title
  })

  output$dashboard_link <- renderUI({
    req(selected_content_info())
    url <- selected_content_info()$dashboard_url
    tags$a(
      href = url,
      class = "btn btn-sm btn-outline-secondary",
      target = "_blank",
      div(
        style = "white-space: nowrap;",
        bs_icon("arrow-up-right-square"),
        "Open"
      )
    )
  })

  output$owner_info <- renderText({
    req(selected_content_info())
    if (nrow(selected_content_info()) == 1) {
      owner <- filter(users(), user_guid == selected_content_info()$owner[[1]]$guid)
      glue::glue("Owner: {owner$display_name}")
    }
  })

  output$email_owner_link <- renderUI({
    owner_email <- users() |>
      filter(user_guid == selected_content_info()$owner[[1]]$guid) |>
      pull(email)
    subject <- glue::glue("\"{selected_content_info()$title}\" on Posit Connect")
    mailto <- glue::glue(
      "mailto:{owner_email}",
      "?subject={URLencode(subject, reserved = TRUE)}"
    )
    tags$a(
      href = mailto,
      class = "btn btn-sm btn-outline-secondary",
      target = "_blank",
      div(
        style = "white-space: nowrap;",
        bs_icon("envelope"),
        "Email"
      )
    )
  })

  # Email button
  observeEvent(input$email_selected, {
    selected_guids <- input$selected_users
    emails <- users() |>
      filter(user_guid %in% selected_guids) |>
      pull(email) |>
      na.omit()

    if (length(emails) > 0) {
      subject <- glue::glue("\"{selected_content_info()$title}\" on Posit Connect")
      mailto <- glue::glue(
        "mailto:{paste(emails, collapse = ',')}",
        "?subject={URLencode(subject, reserved = TRUE)}"
      )
      browseURL(mailto)
    }
  })

  # Output plots ----

  # Create day by day hit data for plot
  daily_hit_data <- reactive({
    all_dates <- seq.Date(date_range()$from, date_range()$to, by = "day")

    all_visits_data() |>
      mutate(date = date(timestamp)) |>
      group_by(date) |>
      summarize(daily_visits = n(), .groups = "drop") |>
      tidyr::complete(date = all_dates, fill = list(daily_visits = 0))
  })

  output$daily_visits_plot <- renderPlotly({
    p <- ggplot(
      daily_hit_data(),
      aes(x = date, y = daily_visits, text = paste("Date:", date, "<br>Visits:", daily_visits))
    ) +
      geom_bar(stat = "identity", fill = "#447099") +
      labs(y = "Visits", x = "Date") +
      theme_minimal()
    ggplotly(p, tooltip = "text")
  })

  output$visit_timeline_plot <- renderPlotly({

    visit_order <- aggregated_visits_data()$display_name
    data <- all_visits_data() |>
      mutate(display_name = factor(display_name, levels = rev(visit_order)))

    from <- as.POSIXct(paste(date_range()$from, "00:00:00"), tz = "")
    to <- as.POSIXct(paste(date_range()$to, "23:59:59"), tz = "")
    p <- ggplot(
      data,
      aes(x = timestamp, y = display_name, text = paste("Timestamp:", timestamp))
    ) +
      geom_point(color = "#447099") +
      # Plotly output does not yet support `position = "top"`, but it should be
      # supported in the next release.
      # https://github.com/plotly/plotly.R/issues/808
      scale_x_datetime(position = "top", limits = c(from, to)) +
      theme_minimal() +
      theme(axis.title.y = element_blank(), axis.ticks.y = element_blank())
    ggplotly(p, tooltip = "text")
  })

  output$visit_timeline_ui <- renderUI({
    n_users <- length(unique(all_visits_data()$display_name))
    row_height <- 20  # visual pitch per user
    label_buffer <- 50  # additional padding for y-axis labels
    toolbar_buffer <- 80  # plotly toolbar & margins

    height_px <- n_users * row_height +
                label_buffer + toolbar_buffer

    plotlyOutput("visit_timeline_plot", height = paste0(height_px, "px"))
  })
}

enableBookmarking("url")
shinyApp(ui, server)
