library(shiny)
library(bslib)
library(shinyjs)
library(connectapi)
library(purrr)
library(dplyr)
library(tidyr)
library(lubridate)
library(reactable)
library(ggplot2)
library(plotly)
library(shinycssloaders)

shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60)
)

options(
  spinner.type = 1,
  spinner.color = "#7494b1"
)

files.sources = list.files("R", full.names = TRUE)
sapply(files.sources, source)

app_mode_groups <- list(
  "API" = c("api", "python-fastapi", "python-api", "tensorflow-saved-model"),
  "Application" = c(
    "shiny",
    "python-shiny",
    "python-dash",
    "python-gradio",
    "python-streamlit",
    "python-bokeh"
  ),
  "Jupyter" = c("jupyter-static", "jupyter-voila"),
  "Quarto" = c("quarto-shiny", "quarto-static"),
  "R Markdown" = c("rmd-shiny", "rmd-static"),
  "Pin" = c("pin"),
  "Other" = c("unknown")
)


content_usage_table_search_method = JS(
  "
  function(rows, columnIds, searchValue) {
    const searchLower = searchValue.toLowerCase();
    const searchColumns = ['title', 'dashboard_url', 'content_guid', 'owner_username'];

    return rows.filter(function(row) {
      return searchColumns.some(function(columnId) {
        const value = String(row.values[columnId] || '').toLowerCase();
        if (columnId === 'dashboard_url') {
          return searchLower.includes(value);
        }
        return value.includes(searchLower);
      });
    });
  }
"
)

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
        "session_window",
        label = tagList(
          "Session Window (sec)",
          tooltip(
            bsicons::bs_icon("question-circle-fill", class = "ms-2"),
            paste0(
              "Visits within this number of seconds are counted only once, ",
              "representing a unique session where a user is interacting with an app."
            )
          )
        ),
        min = 0,
        max = 180,
        value = 0,
        step = 1
      ),

      textInput(
        "session_window_text",
        label = NULL,
        value = 0,
      ),

      tags$hr(),

      # Controls shown only when the outer table is displayed
      conditionalPanel(
        "input.content_guid == null",
        selectizeInput(
          "content_scope",
          "Included Content",
          choices = NULL
        ),
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
        uiOutput("email_selected_visitors_button")
      ),

      tags$hr(),

      div(
        actionLink("clear_cache", "Refresh Data", icon = icon("refresh")),
        div(
          textOutput("last_updated"),
          style = "
            font-size:0.75rem;
            color:#6c757d;
            margin:2px 0 0 0;
          "
        )
      )
    ),

    # Main content views ----

    # The multi-content table is shown by default, when no content item is
    # selected.
    div(
      id = "multi_content_table",
      textOutput("summary_text"),
      withSpinner(reactableOutput("content_usage_table")),
      uiOutput("table_footnote")
    ),

    # The single-content detail view is displayed when an item is selected,
    # either by clicking on a table row or upon restoring from a bookmark URL.
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
          uiOutput("email_owner_button")
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
              withSpinner(plotlyOutput(
                "daily_visits_plot",
                height = "100%",
                width = "100%"
              ))
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
            withSpinner(reactableOutput("aggregated_visits"))
          ),
          tabPanel(
            "List of Visits",
            withSpinner(reactableOutput("all_visits"))
          )
        )
      )
    ),

    # Used to update the selected content GUID in locations other than the table
    # row click.
    tags$script(
      "
      Shiny.addCustomMessageHandler('set_input_value', function(args) {
        Shiny.setInputValue(args[0], args[1], {priority: 'event'});
      });
    "
    )
  )
}

server <- function(input, output, session) {
  # Set up Connect client; handle error if Visitor API Key integration isn't
  # present.

  publisher_client <- connect()

  selected_integration_guid <- reactiveVal(NULL)
  observeEvent(input$auto_add_integration, {
    auto_add_integration(publisher_client, selected_integration_guid())
    # Hard refresh so that the sidebar gets the up to date info
    runjs("window.top.location.reload(true);")
  })

  client <- NULL
  tryCatch(
    client <- connect(
      token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
    ),
    error = function(e) {
      eligible_integrations <- get_eligible_integrations(publisher_client)
      selected_integration <- eligible_integrations |>
        # Sort "max_role: Admin" before "max_role: Publisher"
        arrange(config) |>
        slice_head(n = 1)
      selected_integration_guid(selected_integration$guid)

      if (nrow(selected_integration) == 1) {
        message <- paste0(
          "This content uses a <strong>Visitor API Key</strong> ",
          "integration to show users the content they have access to. ",
          "A compatible integration is already available; use it below.",
          "<br><br>",
          "For more information, see ",
          "<a href='https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key' ",
          "target='_blank'>documentation on Visitor API Key integrations</a>."
        )
      } else if (nrow(selected_integration) == 0) {
        integration_settings_url <- publisher_client$server_url(connectapi:::unversioned_url(
          "connect",
          "#",
          "system",
          "integrations"
        ))
        message <- paste0(
          "This content needs permission to ",
          " show users the content they have access to.",
          "<br><br>",
          "To allow this, an Administrator must configure a ",
          "<strong>Connect API</strong> integration on the ",
          "<strong><a href='",
          integration_settings_url,
          "' target='_blank'>Integration Settings</a></strong> page. ",
          "<br><br>",
          "On that page, select <strong>'+ Add Integration'</strong>. ",
          "In the 'Select Integration' dropdown, choose <strong>'Connect API'</strong>. ",
          "The 'Max Role' field must be set to <strong>'Administrator'</strong> ",
          "or <strong>'Publisher'</strong>; 'Viewer' will not work. ",
          "<br><br>",
          "See the <a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/' ",
          "target='_blank'>Connect API section of the Admin Guide</a> for more detailed setup instructions."
        )
      }

      footer <- if (nrow(selected_integration) == 1) {
        button_label <- HTML(paste0(
          "Use the ",
          "<strong>'",
          selected_integration$name,
          "'</strong> ",
          "Integration"
        ))
        actionButton(
          "auto_add_integration",
          button_label,
          icon = icon("plus"),
          class = "btn btn-primary"
        )
      } else if (nrow(selected_integration) == 0) {
        NULL
      }

      showModal(modalDialog(
        # title = "Additional Setup Required",
        footer = footer,
        HTML(message)
      ))
    }
  )
  if (is.null(client)) {
    return()
  }

  # Tracking the selected content GUID GUID input ----

  # selected_guid is a reactive value that tracks the input GUID. They are each
  # used to trigger different behaviors in different parts of the app so that it
  # reacts appropriately to the selection state.
  selected_guid <- reactiveVal(NULL)

  observeEvent(
    input$content_guid,
    {
      selected_guid(input$content_guid)
    },
    ignoreNULL = FALSE
  )

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
    # Need to use content_unscoped() here because the input value that content()
    # depends on is not available yet. And we *can* use it, because the app
    # always starts up with the widest-selected scope level for a given user,
    # which corresponds to all the content they can view metrics data for.
    if (length(guid) == 1 && guid %in% content_unscoped()$guid) {
      session$sendCustomMessage("set_input_value", list('content_guid', guid))
    }
  })
  observeEvent(
    input$content_guid,
    {
      req(input$content_guid %in% content()$guid)
      session$doBookmark()
    },
    ignoreInit = TRUE
  )

  # Use selection state to toggle visibility of main views.
  observe({
    shinyjs::toggle(
      id = "multi_content_table",
      condition = is.null(selected_guid())
    )
    shinyjs::toggle(
      id = "single_content_detail",
      condition = !is.null(selected_guid())
    )
  })

  # Clicking the back button clears the selected GUID.
  observeEvent(input$clear_content_selection, {
    session$sendCustomMessage("set_input_value", list('content_guid', NULL))
    updateReactable("aggregated_visits", selected = NA)
    updateQueryString(paste0(full_url(session), "?"))

    updateSelectizeInput(
      session,
      "selected_users",
      selected = NA
    )
  })

  # "Clear filter x" link ----

  observeEvent(input$clear_selection, {
    updateSelectizeInput(
      session,
      "selected_users",
      selected = NA
    )
  })

  # Cache invalidation button ----

  cache <- cachem::cache_disk("./app_cache/cache/")
  observeEvent(input$clear_cache, {
    print("Cache cleared!")
    cache$reset()
    session$reload()
  })

  # Session Window controls: sync slider and text input ----

  observeEvent(input$session_window, {
    if (input$session_window != input$session_window_text) {
      freezeReactiveValue(input, "session_window_text")
      updateTextInput(
        session,
        "session_window_text",
        value = input$session_window
      )
    }
  })

  observeEvent(input$session_window_text, {
    new_value <- suppressWarnings(as.numeric(input$session_window_text))
    if (!is.na(new_value) && new_value >= 0 && new_value <= 180) {
      if (new_value != input$session_window) {
        freezeReactiveValue(input, "session_window")
        updateSliderInput(session, "session_window", value = new_value)
      }
    } else {
      if (input$session_window_text != input$session_window) {
        freezeReactiveValue(input, "session_window_text")
        updateTextInput(
          session,
          "session_window_text",
          value = input$session_window
        )
      }
    }
  })

  # Filter Visitors input behavior ----

  # Set choices when aggregated visits data is present
  observe({
    req(aggregated_visits_data())
    data <- aggregated_visits_data()
    updateSelectizeInput(
      session,
      "selected_users",
      choices = setNames(data$user_guid, data$display_name),
      server = TRUE
    )
  })

  # Selection syncing behavior is made more complex because the reactable data needs
  # to be sorted differently from data for the sidebar and plots for them to appear
  # in the same order.

  aggregated_visits_reactable_data <- reactive({
    aggregated_visits_data() |>
      arrange(desc(n_visits), desc(display_name))
  })

  # Sync table to sidebar
  observe({
    selected_guids_reactable <- aggregated_visits_reactable_data()[
      getReactableState("aggregated_visits", "selected"),
      "user_guid",
      drop = TRUE
    ]
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
  observeEvent(
    input$selected_users,
    {
      all_guids_reactable <- aggregated_visits_reactable_data()$user_guid
      selected_indices <- which(all_guids_reactable %in% input$selected_users)
      updateReactable("aggregated_visits", selected = selected_indices)
    },
    ignoreNULL = FALSE
  )

  # Load and processing data ----

  active_user_info <- client$me()

  active_user_guid <- active_user_info$guid

  # Allow the user to control the content they can see.
  active_user_role <- active_user_info$user_role

  scope_choices <- switch(
    active_user_role,
    "administrator" = list(
      "All Content" = "all",
      "Owned + Collaborating" = "edit",
      "Owned" = "own"
    ),
    list(
      "Owned + Collaborating" = "edit",
      "Owned" = "own"
    )
  )

  observe({
    req(scope_choices)
    updateSelectizeInput(
      session,
      "content_scope",
      choices = scope_choices,
      selected = scope_choices[1]
    )
  })

  content_unscoped <- reactive({
    get_content(client)
  }) |>
    bindCache(active_user_guid)

  content <- reactive({
    req(input$content_scope)

    switch(
      input$content_scope,
      "all" = content_unscoped(),
      "view" = content_unscoped() |> filter(app_role != "none"),
      "edit" = content_unscoped() |> filter(app_role %in% c("owner", "editor")),
      "own" = content_unscoped() |> filter(owner_guid == active_user_guid)
    )
  })

  date_range <- reactive({
    switch(
      input$date_range_choice,
      "1 Week" = list(from = today() - days(6), to = today()),
      "30 Days" = list(from = today() - days(29), to = today()),
      "90 Days" = list(from = today() - days(89), to = today()),
      "Custom" = list(
        from = input$date_range_custom[1],
        to = input$date_range_custom[2]
      )
    )
  })

  users <- reactive({
    get_users(client) |>
      mutate(
        full_name = paste(first_name, last_name),
        display_name = paste0(full_name, " (", username, ")")
      ) |>
      select(user_guid = guid, full_name, username, display_name, email)
  }) |>
    bindCache(active_user_guid)

  usage_data_meta <- reactive({
    req(active_user_role %in% c("administrator", "publisher"))
    from <- as.POSIXct(paste(date_range()$from, "00:00:00"), tz = "")
    to <- as.POSIXct(paste(date_range()$to, "23:59:59"), tz = "")

    usage_list <- get_usage(
      client,
      from = from,
      to = to
    )
    usage_tbl <- as_tibble(usage_list) |>
      filter(!grepl("^ContentHealthMonitor/", user_agent)) |>
      select(user_guid, content_guid, timestamp)
    list(
      data = usage_tbl,
      last_updated = Sys.time()
    )
  }) |>
    bindCache(active_user_guid, date_range())

  usage_data_raw <- reactive({
    usage_data_meta()$data
  })

  usage_last_updated <- reactive({
    usage_data_meta()$last_updated
  })

  # Multi-content table data ----

  # Filter the raw data based on selected scope, app mode and session window
  usage_data_visits <- reactive({
    req(content())
    scope_filtered_usage <- usage_data_raw() |>
      filter(content_guid %in% content()$guid)

    app_mode_filtered_usage <- if (length(input$app_mode_filter) == 0) {
      scope_filtered_usage
    } else {
      app_modes <- unlist(app_mode_groups[input$app_mode_filter])
      filter_guids <- content() |>
        filter(app_mode %in% app_modes) |>
        pull(guid)
      scope_filtered_usage |>
        filter(content_guid %in% filter_guids)
    }

    req(input$session_window)
    filter_visits_by_time_window(app_mode_filtered_usage, input$session_window)
  })

  # Create data for the main table and summary export.
  multi_content_table_data <- reactive({
    req(nrow(usage_data_visits()) > 0)
    usage_summary <- usage_data_visits() |>
      group_by(content_guid) |>
      summarize(
        total_views = n(),
        unique_viewers = n_distinct(user_guid, na.rm = TRUE),
        has_anonymous = any(is.na(user_guid)),
        .groups = "drop"
      )

    # Prepare sparkline data.
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
      select(
        title,
        dashboard_url,
        content_guid,
        owner_username,
        total_views,
        sparkline,
        unique_viewers,
        has_anonymous
      )
  })

  # Multi-content table UI and outputs ----

  output$summary_text <- renderText(
    if (active_user_role == "viewer") {
      "Viewer accounts do not have permission to view usage data."
    } else if (nrow(usage_data_visits()) == 0) {
      paste(
        "No usage data available.",
        "Try adjusting your content filters or date range."
      )
    } else {
      glue::glue(
        "{nrow(usage_data_visits())} visits ",
        "across {nrow(multi_content_table_data())} content items."
      )
    }
  )

  output$last_updated <- renderText({
    fmt <- "%Y-%m-%d %l:%M:%S %p %Z"
    paste0("Updated ", format(usage_last_updated(), fmt))
  })

  output$table_footnote <- renderUI({
    # Only execute if anonymous visits are present
    req(any(multi_content_table_data()$has_anonymous))
    div(
      style = "text-align: right; font-size: 0.875rem;",
      "* Anonymous visitors do not contribute to the unique visitor count."
    )
  })

  # JavaScript for persisting search terms across table rerenders
  table_js <- "
  function(el, x) {
    const tableId = el.id;
    const storageKey = 'search_' + tableId;

    // Clear search value when the page is refreshed
    window.addEventListener('beforeunload', function() {
      sessionStorage.removeItem(storageKey);
    });

    const searchInput = el.querySelector('input.rt-search');
    if (!searchInput) return;

    // Restore previous search if available
    const savedSearch = sessionStorage.getItem(storageKey);

    if (savedSearch) {
      searchInput.value = savedSearch;
      if (window.Reactable && typeof window.Reactable.setSearch === 'function') {
        window.Reactable.setSearch(tableId, savedSearch);
      }
    }

    // Save search terms as they're entered
    searchInput.addEventListener('input', function() {
      sessionStorage.setItem(storageKey, this.value);
    });
  }
  "

  output$content_usage_table <- renderReactable({
    data <- multi_content_table_data()

    table <- reactable(
      data,
      defaultSortOrder = "desc",
      onClick = JS(
        "function(rowInfo, colInfo) {
        if (rowInfo && rowInfo.row && rowInfo.row.content_guid) {
          Shiny.setInputValue('content_guid', rowInfo.row.content_guid, {priority: 'event'});
        }
      }"
      ),
      pagination = TRUE,
      defaultPageSize = 25,
      sortable = TRUE,
      searchable = TRUE,
      searchMethod = content_usage_table_search_method,
      language = reactableLang(
        searchPlaceholder = "Search by title, URL, GUID, or owner",
      ),
      highlight = TRUE,
      defaultSorted = "total_views",
      style = list(cursor = "pointer"),
      wrap = FALSE,
      class = "metrics-tbl",

      columns = list(
        title = colDef(
          name = "Content",
          defaultSortOrder = "asc",
          style = function(value) {
            switch(
              value,
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
            if (is.na(url) || url == "") {
              return("")
            }
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
            div(
              style = list(whiteSpace = "normal", wordBreak = "break-all"),
              value
            )
          }
        ),

        owner_username = colDef(
          name = "Owner",
          defaultSortOrder = "asc",
          minWidth = 75
        ),

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
          align = "right",
          minWidth = 70,
          maxWidth = 135,
          cell = function(value, index) {
            if (data$has_anonymous[index]) {
              paste0(value, "*")
            } else {
              paste0(value, "\u00A0") # Non-breaking space for alignment
            }
          },
          class = "number"
        ),

        has_anonymous = colDef(
          show = FALSE
        )
      )
    )

    # Apply any onRender JS for capturing search value
    htmlwidgets::onRender(table, table_js)
  })

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
      to_export <- multi_content_table_data() |>
        select(-sparkline, -has_anonymous, -unique_viewers_display)
      write.csv(to_export, file, row.names = FALSE)
    }
  )

  # Single-content detail view data ----

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
      filter(time_diff > input$session_window) |>
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
    filtered_visits <- selected_content_usage() |>
      group_by(user_guid) |>

      # Compute time diffs and filter out hits within the session
      mutate(time_diff = seconds(timestamp - lag(timestamp, 1))) |>
      replace_na(list(time_diff = seconds(Inf))) |>
      filter(time_diff > input$session_window) |>

      summarize(n_visits = n())

    filtered_visits |>
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

  # Single-content detail view UI and outputs ----

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
            if (is.na(url) || url == "") {
              return("")
            }
            subject <- glue::glue(
              "\"{selected_content_info()$title}\" on Posit Connect"
            )
            mailto <- glue::glue(
              "mailto:{url}?subject={URLencode(subject, reserved = TRUE)}"
            )
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
      user_string <- if (length(users) == 1) {
        users
      } else {
        "multiple selected users"
      }
      tagList(
        HTML(glue::glue(
          "{nrow(hits)} visits from <b>{user_string}</b> between ",
          "{date_range()$from} and {date_range()$to}."
        )),
        actionLink(
          "clear_selection",
          glue::glue("Clear filter"),
          icon = icon("times")
        )
      )
    } else {
      glue::glue(
        "{nrow(hits)} total visits between ",
        "{date_range()$from} and {date_range()$to}."
      )
    }
  })

  output$content_title <- renderText({
    req(selected_content_info())
    selected_content_info()$title
  })

  output$content_guid <- renderText({
    req(selected_content_info())
    selected_content_info()$guid
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
        "Open"
      )
    )
  })

  output$owner_info <- renderText({
    req(selected_content_info())
    if (nrow(selected_content_info()) == 1) {
      owner <- filter(
        users(),
        user_guid == selected_content_info()$owner[[1]]$guid
      )
      glue::glue("Owner: {owner$display_name}")
    }
  })

  output$email_owner_button <- renderUI({
    owner_email <- users() |>
      filter(user_guid == selected_content_info()$owner[[1]]$guid) |>
      pull(email)
    subject <- glue::glue(
      "\"{selected_content_info()$title}\" on Posit Connect"
    )
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

  output$email_selected_visitors_button <- renderUI({
    req(selected_content_info())
    emails <- users() |>
      filter(user_guid %in% input$selected_users) |>
      pull(email) |>
      na.omit()

    disabled <- if (length(emails) == 0) "disabled" else NULL

    subject <- glue::glue(
      "\"{selected_content_info()$title}\" on Posit Connect"
    )
    mailto <- glue::glue(
      "mailto:{paste(emails, collapse = ',')}",
      "?subject={URLencode(subject, reserved = TRUE)}"
    )

    tags$button(
      type = "button",
      class = "btn btn-sm btn-outline-secondary",
      disabled = disabled,
      onclick = if (is.null(disabled)) {
        sprintf("window.location.href='%s'", mailto)
      } else {
        NULL
      },
      tagList(icon("envelope"), "Email Selected Visitors")
    )
  })

  # Plots for single-content view ----

  daily_hit_data <- reactive({
    all_dates <- seq.Date(date_range()$from, date_range()$to, by = "day")

    all_visits_data() |>
      mutate(date = date(timestamp)) |>
      group_by(date) |>
      summarize(daily_visits = n(), .groups = "drop") |>
      complete(date = all_dates, fill = list(daily_visits = 0))
  })

  output$daily_visits_plot <- renderPlotly({
    p <- ggplot(
      daily_hit_data(),
      aes(
        x = date,
        y = daily_visits,
        text = paste("Date:", date, "<br>Visits:", daily_visits)
      )
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
      aes(
        x = timestamp,
        y = display_name,
        text = paste("Timestamp:", timestamp)
      )
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
    row_height <- 20 # visual pitch per user
    label_buffer <- 50 # additional padding for y-axis labels
    toolbar_buffer <- 80 # plotly toolbar & margins

    height_px <- n_users * row_height + label_buffer + toolbar_buffer

    withSpinner(plotlyOutput(
      "visit_timeline_plot",
      height = paste0(height_px, "px")
    ))
  })

  # Global UI elements ----

  output$page_title_bar <- renderUI({
    if (is.null(selected_guid())) {
      "Usage"
    } else {
      div(
        style = "display: flex; justify-content: space-between; gap: 1rem; align-items: baseline;",
        actionButton(
          "clear_content_selection",
          "Back",
          icon("arrow-left"),
          class = "btn btn-sm",
          style = "white-space: nowrap;"
        ),
        span(
          "Usage / ",
          textOutput("content_title", inline = TRUE)
        ),
        code(
          class = "text-muted",
          style = "font-family: \"Fira Mono\", Consolas, Monaco, monospace; font-size: 0.875rem;",
          textOutput("content_guid", inline = TRUE)
        ),
        uiOutput("dashboard_link")
      )
    }
  })
}

enableBookmarking("url")
shinyApp(ui, server)
