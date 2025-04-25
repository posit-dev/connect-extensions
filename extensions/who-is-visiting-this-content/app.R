library(shiny)
library(bslib)
library(shinyjs)
library(connectapi)
library(purrr)
library(dplyr)
library(lubridate)
library(reactable)
library(ggplot2)
library(plotly)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

extract_guid <- function(raw) {
  guid_pattern <- "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
  match <- regmatches(raw, regexpr(guid_pattern, raw))
  if (length(match) == 1) {
    match
  } else {
    ""
  }
}

app_mode_groups <- list(
  "API" = c("api", "python-fastapi", "python-api", "tensorflow-saved-model"),
  "Application" = c("shiny", "python-shiny", "python-dash", "python-gradio", "python-streamlit", "python-bokeh"),
  "Jupyter" = c("jupyter-static", "jupyter-voila"),
  "Quarto" = c("quarto-shiny", "quarto-static"),
  "R Markdown" = c("rmd-shiny", "rmd-static"),
  "Pin" = c("pin"),
  "Other" = c("unknown")
)

bar_chart <- function(value, max_val, height = "1rem", fill = "#00bfc4", background = NULL) {
  width <- paste0(value * 100 / max_val, "%")
  value <- format(value, width = nchar(max_val), justify = "right")
  bar <- div(class = "bar", style = list(background = fill, width = width))
  chart <- div(class = "bar-chart", style = list(background = background), bar)
  label <- span(class = "number", value)
  div(class = "bar-cell", label, chart)
}

ui <- function(request) {
  page_sidebar(
    useShinyjs(),
    theme = bs_theme(version = 5),
    tags$head(
      tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
    ),

    title = uiOutput("page_title_bar"),

    sidebar = sidebar(
      open = TRUE,
      width = 275,

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

      sliderInput(
        "visit_merge_window",
        label = tagList(
          "Visit Merge Window (sec)",
          tooltip(
            bsicons::bs_icon("question-circle-fill", class = "ms-2"),
            "Filter out visits occurring within this many seconds of that user's last visit."
          )
        ),
        min = 0,
        max = 180,
        value = 0,
        step = 1
      ),

      textInput(
        "visit_merge_window_text",
        label = NULL,
        value = 0,
      ),

      tags$hr(),

      # Controls shown only when the outer table is displayed
      conditionalPanel(
        "input.content_guid == null",
        selectizeInput(
          "app_mode_filter",
          label = "Filter by Content Type",
          options = list(placeholder = "All Content Types"),
          choices = list(
            "API",
            "Application",
            "Jupyter",
            "Quarto",
            "R Markdown",
            "Pin",
            "Other"
          ),
          multiple = TRUE
        ),
        checkboxInput(
          "show_guid",
          label = "Show GUID"
        ),
        downloadButton(
          "export_visit_totals",
          class = "btn-sm",
          label = "Export Usage Table"
        ),
        downloadButton(
          "export_raw_visits",
          class = "btn-sm",
          label = "Export Raw Visit Data"
        )
      ),

      # Controls shown only when the inner detail view is displayed
      conditionalPanel(
        "input.content_guid != null",
        # div(class = "fs-5", "Filters"),
        selectizeInput(
          "selected_users",
          label = "Filter Visitors",
          options = list(placeholder = "All Visitors"),
          choices = NULL,
          multiple = TRUE
        ),
        uiOutput("email_selected_users_button")
      ),

      tags$hr(),

      # TODO: Possibly remove or hide in a "Troubleshooting" or Advanced
      # accordion section
      actionButton("clear_cache", "Clear Cache", icon = icon("refresh")),
    ),

    # The multi-content table is shown if no content item is selected. The
    # single-content detail view is displayed if an item is selected by clicking
    # on its table row.
    div(
      id = "multi_content_table",
      textOutput("summary_text"),
      reactableOutput("content_usage_table")
    ),


    div(
      id = "single_content_detail",
      style = "display:none;",
      div(
        class = "d-flex justify-content-between align-items-center gap-2 mb-3",
        span(
          uiOutput("filter_message")
        ),
        div(
          class = "d-flex align-items-center gap-2",
          textOutput("owner_info", inline = TRUE),
          uiOutput("email_owner_link")
        )
      ),
      layout_column_wrap(
        width = "400px",
        heights_equal = "row",
        navset_card_tab(
          # Plot panel
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
          # Table panel
          tabPanel(
            title = tagList(
              "Top Visitors",
              tooltip(
                bsicons::bs_icon("info-circle-fill", class = "ms-2"),
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
    ),
    tags$script("
      Shiny.addCustomMessageHandler('set_input_value', function(args) {
        Shiny.setInputValue(args[0], args[1]);
      });
    ")
  )
}

server <- function(input, output, session) {

  client <- NULL

  tryCatch(
    client <- connect(token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN),
    error = function(e) {
      showModal(modalDialog(
        title = "Additional Setup Required",
        footer = NULL,
        HTML(paste(
          "In the Access panel to the right, click <strong>\"Add integration\"</strong>,",
          "then select a <strong>Visitor API Key</strong> integration.",
          "If you don't see one in the list, an administrator must enable this feature on your Connect server.",
          "See the <a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/' target='_blank'>Admin Guide</a> for setup instructions.",
          "<br><br>",
          "For guidance on using visitor-scoped permissions in your own Connect apps, see the",
          "<a href='https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key' target='_blank'>User Guide</a>.",
          sep = " "
        ))
      ))
    }
  )
  print(client)
  if (is.null(client)) {
    return()
  }

  # Bookmarking ----

  observe({
    setBookmarkExclude(setdiff(names(input), "content_guid"))
  })
  onBookmarked(function(url) {
    message("Bookmark complete. URL: ", url)
    updateQueryString(url)
  })
  onRestore(function(state) {
    guid <- state$input$content_guid
    print(guid)
    if (length(guid) == 1 && guid %in% content()$guid) {
      print("found a guid")
      session$sendCustomMessage("set_input_value", list('content_guid', guid))
    }
  })

  # Handle GUID input ----


  # Update the bookmark when a valid GUID is input
  observeEvent(input$content_guid, {
    req(input$content_guid %in% content()$guid)
    session$doBookmark()

  }, ignoreInit = TRUE)

  observe({
    shinyjs::toggle(id = "multi_content_table", condition = is.null(selected_guid()))
    shinyjs::toggle(id = "single_content_detail", condition = !is.null(selected_guid()))
    shinyjs::toggle("clear_content_selection", condition = !is.null(selected_guid()))
  })

  # Back button logic ----

  observeEvent(input$clear_content_selection, {
    session$sendCustomMessage("set_input_value", list('content_guid', NULL))
    updateReactable("aggregated_visits", selected = NA)

    full_url <- paste0(
      session$clientData$url_protocol, "//",
      session$clientData$url_hostname,
      if (nzchar(session$clientData$url_port)) paste0(":", session$clientData$url_port),
      session$clientData$url_pathname,
      "?"
    )
    updateQueryString(full_url)
  })

  # Cache invalidation button ----

  cache <- cachem::cache_disk("./app_cache/cache/")
  observeEvent(input$clear_cache, {
    print("Cache cleared!")
    cache$reset()  # Clears all cached data
    session$reload()  # Reload the app to ensure fresh data
  })

  # Visit Merge Window: sync slider and text input ----

  observeEvent(input$visit_merge_window, {
    if (input$visit_merge_window != input$visit_merge_window_text) {
      freezeReactiveValue(input, "visit_merge_window_text")
      updateTextInput(session, "visit_merge_window_text", value = input$visit_merge_window)
    }
  })

  observeEvent(input$visit_merge_window_text, {
    new_value <- suppressWarnings(as.numeric(input$visit_merge_window_text))

    if (!is.na(new_value) && new_value >= 0 && new_value <= 180) {
      if (new_value != input$visit_merge_window) {
        freezeReactiveValue(input, "visit_merge_window")
        updateSliderInput(session, "visit_merge_window", value = new_value)
      }
    } else {
      if (input$visit_merge_window_text != input$visit_merge_window) {
        freezeReactiveValue(input, "visit_merge_window_text")
        updateTextInput(session, "visit_merge_window_text", value = input$visit_merge_window)
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

  # Load and processing data ----

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

  usage_data_raw <- reactive({
    get_usage(
      client,
      from = date_range()$from,
      to = date_range()$to
    )
  }) |> bindCache(authed_user_guid, date_range())

  # Multi-content view data ----

  # Apply client-side data filters (app mode)
  usage_data_visits <- reactive({
    filtered_data <- if (length(input$app_mode_filter ) == 0) {
      usage_data_raw()
    } else {
      app_modes <- unlist(app_mode_groups[input$app_mode_filter])
      filter_guids <- content() |>
        filter(app_mode %in% app_modes) |>
        pull(guid)
      usage_data_raw() |>
        filter(content_guid %in% filter_guids)
    }

    req(input$visit_merge_window)
    if (input$visit_merge_window == 0) {
      filtered_data
    } else {
      filtered_data |>
        group_by(content_guid, user_guid) |>

        # Compute time diffs and filter out hits within the session
        mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
        replace_na(list(time_diff = seconds(Inf))) |>
        filter(time_diff > input$visit_merge_window) |>
        ungroup() |>
        select(-time_diff)
    }
  })

    # Create data for the main table and summary export.
    content_usage_data <- reactive({
      usage_summary <- usage_data_visits() |>
        group_by(content_guid) |>
        summarize(
          total_views = n(),
          unique_viewers = n_distinct(user_guid, na.rm = TRUE),
          .groups = "drop"
        )

      # Prepare sparkline data as a list column of numeric vectors.
      all_dates <- seq.Date(date_range()$from, date_range()$to, by = "day")
      daily_usage <- usage_data_visits() |>
        count(content_guid, date = date(timestamp)) |>
        complete(date = all_dates, nesting(content_guid), fill = list(n = 0)) |>
        group_by(content_guid) |>
        summarize(sparkline = list(n), .groups = "drop")

      content() |>
        mutate(owner_username = map_chr(owner, "username")) |>
        select(title, content_guid = guid, owner_username, dashboard_url) |>
        replace_na(list(title = "[Untitled]")) |>
        right_join(usage_summary, by = "content_guid") |>
        right_join(daily_usage, by = "content_guid") |>
        replace_na(list(title = "[Deleted]")) |>
        arrange(desc(total_views)) |>
        select(title, dashboard_url, content_guid, owner_username, total_views, sparkline, unique_viewers)
    })

    output$page_title_bar <- renderUI({
      if (is.null(selected_guid())) {
        "Usage"
      } else {
        div(
          style = "display: flex; justify-content: space-between; gap: 1rem; align-items: center;",
          actionButton("clear_content_selection", "Back", icon("arrow-left"), class = "btn btn-sm", style = "white-space: nowrap;"),
          span(
              "Usage / ",
              textOutput("content_title", inline = TRUE)
          ),
          uiOutput("dashboard_link")
        )
      }
    })

    output$summary_text <- renderText(
      glue::glue(
        "{nrow(usage_data_visits())} visits ",
        "across {nrow(content_usage_data())} content items."
      )
    )

    output$content_usage_table <- renderReactable({
      data <- content_usage_data()

      reactable(
        data,
        defaultSortOrder = "desc",
        onClick = JS("function(rowInfo, colInfo) {
          if (rowInfo && rowInfo.row && rowInfo.row.content_guid) {
            Shiny.setInputValue('content_guid', rowInfo.row.content_guid, {priority: 'event'});
          }
        }"),
        pagination = TRUE,
        defaultPageSize = 25,
        sortable = TRUE,
        highlight = TRUE,
        defaultSorted = "total_views",
        style = list(cursor = "pointer"),
        wrap = FALSE,
        class = "metrics-tbl",

        columns = list(
          title = colDef(
            name = "Content",
            defaultSortOrder = "asc",
            filterable = TRUE,
            style = function(value) {
              switch(value,
                "[Untitled]" = list(fontStyle = "italic"),
                "[Deleted]" = list(fontStyle = "italic", color = "#808080"),
                NULL
              )
            }
          ),

          dashboard_url = colDef(
            name = "",
            width = 32,
            sortable = FALSE,
            cell = function(url) {
              if (is.na(url) || url == "") return("")
              HTML(as.character(tags$div(
                onclick = "event.stopPropagation()",
                tags$a(
                  href = url,
                  target = "_blank",
                  bsicons::bs_icon("arrow-up-right-square")
                )
              )))
            },
            html = TRUE
          ),

          content_guid = colDef(
            name = "GUID",
            show = input$show_guid,
            class = "number",
            cell = function(value) {
              div(style = list(whiteSpace = "normal", wordBreak = "break-all"), value)
            }
          ),

          owner_username = colDef(name = "Owner", defaultSortOrder = "asc", minWidth = 75, filterable = TRUE),

          total_views = colDef(
            name = "Visits",
            align = "left",
            minWidth = 75,
            maxWidth = 150,
            cell = function(value) {
              max_val <- max(data$total_views, na.rm = TRUE)
              bar_chart(value, max_val, fill = "#7494b1", background = "#e1e1e1")
            }
          ),

          sparkline = colDef(
            name = "By Day",
            align = "left",
            width = 90,
            sortable = FALSE,
            cell = function(value) {
              sparkline::sparkline(
                value,
                type = "bar",
                barColor = "#7494b1",
                disableTooltips = TRUE,
                barWidth = 8,
                chartRangeMin = TRUE
              )
            }
          ),

          unique_viewers = colDef(
            name = "Unique Visitors",
            align = "left",
            minWidth = 70,
            maxWidth = 135,
            cell = function(value) {
              max_val <- max(data$total_views, na.rm = TRUE)
              format(value, width = nchar(max_val), justify = "right")
            },
            class = "number"
          )
        )
      )
    })

    selected_guid <- reactiveVal(NULL)

    observeEvent(input$content_guid, {
      selected_guid(input$content_guid)
    }, ignoreNULL = FALSE)

    # Download handlers ---

    output$export_raw_visits <- downloadHandler(
      filename = function() {
        paste0("content_raw_visits_", Sys.Date(), ".csv")
      },
      content = function(file) {
        write.csv(usage_data_raw(), file, row.names = FALSE)
      }
    )

    output$export_visit_totals <- downloadHandler(
      filename = function() {
        paste0("content_visit_totals_", Sys.Date(), ".csv")
      },
      content = function(file) {
        to_export <- content_usage_data() |>
          select(-sparkline)
        write.csv(to_export, file, row.names = FALSE)
      }
    )



  # Single-content view data ----

  selected_content_usage <- reactive({
    req(selected_guid())
    usage_data_raw() |>
      filter(content_guid == selected_guid())
  })

  all_visits_data <- reactive({
    all_visits <- selected_content_usage() |>

      # Compute time diffs and filter out hits within the session
      group_by(user_guid) |>
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > input$visit_merge_window) |>
      ungroup() |>

      # Join to usernames
      left_join(users(), by = "user_guid") |>
      replace_na(list(
        user_guid = "ANONYMOUS",
        display_name = "[Anonymous]"
      )) |>
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
      filter(time_diff > input$visit_merge_window) |>

      summarize(n_visits = n())

    filtered_visits |>
      left_join(unfiltered_hits, by = "user_guid") |>
      left_join(users(), by = "user_guid") |>
      replace_na(list(
        user_guid = "ANONYMOUS",
        display_name = "[Anonymous]"
      )) |>
      arrange(desc(n_visits), display_name) |>
      select(user_guid, display_name, email, n_visits)
  })

  selected_content_info <- reactive({
    req(selected_guid())
    filter(content(), guid == selected_guid())
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
      class = "metrics-tbl",
      style = list(cursor = "pointer"),
      wrap = FALSE,
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
                icon("envelope")
              )
            )))
          },
          html = TRUE
        ),
        n_visits = colDef(
          name = "Visits",
          defaultSortOrder = "desc",
          maxWidth = 75,
          class = "number"
        )
      )
    )
  })

  output$all_visits <- renderReactable({
    reactable(
      all_visits_data(),
      defaultSorted = "timestamp",
      class = "metrics-tbl",
      wrap = FALSE,
      columns = list(
        user_guid = colDef(show = FALSE),
        timestamp = colDef(
          name = "Time",
          format = colFormat(datetime = TRUE, time = TRUE),
          defaultSortOrder = "desc",
          class = "number"
        ),
        display_name = colDef(name = "Visitor")
      )
    )
  })

  # Render content metadata and other text ----

  output$filter_message <- renderUI({
    hits <- all_visits_data()
    glue::glue(
      "{nrow(hits)} visits between ",
      "{date_range()$from} and {date_range()$to}."
    )
    if (length(input$selected_users) > 0) {
      users <- aggregated_visits_data() |>
        filter(user_guid %in% input$selected_users) |>
        pull(display_name)
      user_string <- if (length(users) == 1) users else "selected users"
      tagList(
        glue::glue(
          "{nrow(hits)} visits from {user_string} between ",
          "{date_range()$from} and {date_range()$to}."
        ),
        actionLink("clear_selection", glue::glue("Clear filter"), icon = icon("times"))
      )
    } else {

        glue::glue(
          "{nrow(hits)} total visits between ",
          "{date_range()$from} and {date_range()$to}."
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
        icon("arrow-up-right-from-square"),
        "Open in Connect"
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
        icon("envelope"),
        "Email"
      )
    )
  })

  output$email_selected_users_button <- renderUI({
    req(selected_content_info())
    emails <- users() |>
      filter(user_guid %in% input$selected_users) |>
      pull(email) |>
      na.omit()

    disabled <- if (length(emails) == 0) "disabled" else NULL

    subject <- glue::glue("\"{selected_content_info()$title}\" on Posit Connect")
    mailto <- glue::glue(
      "mailto:{paste(emails, collapse = ',')}",
      "?subject={URLencode(subject, reserved = TRUE)}"
    )

    tags$button(
      type = "button",
      class = "btn btn-sm btn-outline-secondary",
      disabled = disabled,
      onclick = if (is.null(disabled)) sprintf("window.location.href='%s'", mailto) else NULL,
      tagList(icon("envelope"), "Email Selected Visitors")
    )
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
