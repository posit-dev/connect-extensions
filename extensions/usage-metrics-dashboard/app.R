shiny::shinyOptions(
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


content_usage_table_search_method = htmlwidgets::JS(
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
  bslib::page_sidebar(
    shinyjs::useShinyjs(),
    theme = bslib::bs_theme(version = 5),
    shiny::tags$head(
      shiny::tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
    ),

    title = shiny::uiOutput("page_title_bar"),

    sidebar = bslib::sidebar(
      open = TRUE,
      width = 275,

      shiny::selectInput(
        "date_range_choice",
        label = "Date Range",
        choices = c("1 Week", "30 Days", "90 Days", "Custom"),
        selected = "1 Week"
      ),

      shiny::conditionalPanel(
        condition = "input.date_range_choice === 'Custom'",
        shiny::dateRangeInput(
          "date_range_custom",
          label = NULL,
          start = lubridate::today() - lubridate::days(6),
          end = lubridate::today(),
          max = lubridate::today()
        )
      ),

      shiny::sliderInput(
        "session_window",
        label = shiny::tagList(
          "Session Window (sec)",
          bslib::tooltip(
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

      shiny::textInput(
        "session_window_text",
        label = NULL,
        value = 0
      ),

      shiny::tags$hr(),

      # Controls shown only when the outer table is displayed
      shiny::conditionalPanel(
        "input.content_guid == null",
        shiny::selectizeInput(
          "content_scope",
          "Included Content",
          choices = NULL
        ),
        shiny::selectizeInput(
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
        shiny::checkboxInput(
          "show_guid",
          label = "Show GUID"
        ),
        shiny::downloadButton(
          "export_visit_totals",
          class = "btn-sm",
          label = "Export Usage Table"
        ),
        shiny::downloadButton(
          "export_raw_visits",
          class = "btn-sm",
          label = "Export Raw Visit Data"
        )
      ),

      # Controls shown only when the inner detail view is displayed
      shiny::conditionalPanel(
        "input.content_guid != null",
        # shiny::div(class = "fs-5", "Filters"),
        shiny::selectizeInput(
          "selected_users",
          label = "Filter Visitors",
          options = list(placeholder = "All Visitors"),
          choices = NULL,
          multiple = TRUE
        ),
        shiny::uiOutput("email_selected_visitors_button")
      ),

      shiny::tags$hr(),

      shiny::div(
        shiny::actionLink("clear_cache", "Refresh Data", icon = shiny::icon("refresh")),
        shiny::div(
          shiny::textOutput("last_updated"),
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
    shiny::div(
      id = "multi_content_table",
      shiny::textOutput("summary_text"),
      shinycssloaders::withSpinner(reactable::reactableOutput("content_usage_table"))
    ),

    # The single-content detail view is displayed when an item is selected,
    # either by clicking on a table row or upon restoring from a bookmark URL.
    shiny::div(
      id = "single_content_detail",
      style = "display:none;",
      shiny::div(
        class = "d-flex justify-content-between align-items-center gap-2 mb-3",
        shiny::span(
          shiny::uiOutput("filter_message")
        ),
        shiny::div(
          class = "d-flex align-items-center gap-2",
          shiny::textOutput("owner_info", inline = TRUE),
          shiny::uiOutput("email_owner_button")
        )
      ),
      bslib::layout_column_wrap(
        width = "400px",
        heights_equal = "row",
        bslib::navset_card_tab(
          # Plot panel
          shiny::tabPanel(
            "Daily Visits",
            shiny::div(
              style = "height: 300px",
              shinycssloaders::withSpinner(plotly::plotlyOutput(
                "daily_visits_plot",
                height = "100%",
                width = "100%"
              ))
            )
          ),
          shiny::tabPanel(
            "Visit Timeline",
            shiny::div(
              style = "height: 400px;",
              shiny::uiOutput("visit_timeline_ui")
            )
          )
        ),
        bslib::navset_card_tab(
          # Table panel
          shiny::tabPanel(
            title = shiny::tagList(
              "Top Visitors",
              bslib::tooltip(
                bsicons::bs_icon("info-circle-fill", class = "ms-2"),
                "Click a row to show only that user's visits."
              )
            ),
            shinycssloaders::withSpinner(reactable::reactableOutput("aggregated_visits"))
          ),
          shiny::tabPanel(
            "List of Visits",
            shinycssloaders::withSpinner(reactable::reactableOutput("all_visits"))
          )
        )
      )
    ),

    # Used to update the selected content GUID in locations other than the table
    # row click.
    shiny::tags$script(
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

  publisher_client <- connectapi::connect()

  selected_integration_guid <- shiny::reactiveVal(NULL)
  shiny::observeEvent(input$auto_add_integration, {
    auto_add_integration(publisher_client, selected_integration_guid())
    # Hard refresh so that the sidebar gets the up to date info
    shiny::runjs("window.top.location.reload(true);")
  })

  client <- NULL
  tryCatch(
    client <- connectapi::connect(
      token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
    ),
    error = function(e) {
      eligible_integrations <- get_eligible_integrations(publisher_client)
      selected_integration <- eligible_integrations |>
        # Sort "max_role: Admin" before "max_role: Publisher"
        dplyr::arrange(config) |>
        dplyr::slice_head(n = 1)
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
        button_label <- shiny::HTML(paste0(
          "Use the ",
          "<strong>'",
          selected_integration$name,
          "'</strong> ",
          "Integration"
        ))
        shiny::actionButton(
          "auto_add_integration",
          button_label,
          icon = shiny::icon("plus"),
          class = "btn btn-primary"
        )
      } else if (nrow(selected_integration) == 0) {
        NULL
      }

      shiny::showModal(shiny::modalDialog(
        # title = "Additional Setup Required",
        footer = footer,
        shiny::HTML(message)
      ))
    }
  )
  print(client)
  if (is.null(client)) {
    return()
  }

  # Tracking the selected content GUID GUID input ----

  # selected_guid is a reactive value that tracks the input GUID. They are each
  # used to trigger different behaviors in different parts of the app so that it
  # reacts appropriately to the selection state.
  selected_guid <- shiny::reactiveVal(NULL)

  shiny::observeEvent(
    input$content_guid,
    {
      selected_guid(input$content_guid)
    },
    ignoreNULL = FALSE
  )

  # Bookmarking ----

  shiny::observe({
    shiny::setBookmarkExclude(setdiff(names(input), "content_guid"))
  })
  shiny::onBookmarked(function(url) {
    message("Bookmark complete. URL: ", url)
    shiny::updateQueryString(url)
  })
  shiny::onRestore(function(state) {
    guid <- state$input$content_guid
    # Need to use content_unscoped() here because the input value that content()
    # depends on is not available yet. And we *can* use it, because the app
    # always starts up with the widest-selected scope level for a given user,
    # which corresponds to all the content they can view metrics data for.
    if (length(guid) == 1 && guid %in% content_unscoped()$guid) {
      session$sendCustomMessage("set_input_value", list('content_guid', guid))
    }
  })
  shiny::observeEvent(
    input$content_guid,
    {
      shiny::req(input$content_guid %in% content()$guid)
      session$doBookmark()
    },
    ignoreInit = TRUE
  )

  # Use selection state to toggle visibility of main views.
  shiny::observe({
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
  shiny::observeEvent(input$clear_content_selection, {
    session$sendCustomMessage("set_input_value", list('content_guid', NULL))
    updateReactable("aggregated_visits", selected = NA)
    shiny::updateQueryString(paste0(full_url(session), "?"))

    shiny::updateSelectizeInput(
      session,
      "selected_users",
      selected = NA
    )
  })

  # "Clear filter x" link ----

  shiny::observeEvent(input$clear_selection, {
    shiny::updateSelectizeInput(
      session,
      "selected_users",
      selected = NA
    )
  })

  # Cache invalidation button ----

  cache <- cachem::cache_disk("./app_cache/cache/")
  shiny::observeEvent(input$clear_cache, {
    print("Cache cleared!")
    cache$reset()
    session$reload()
  })

  # Session Window controls: sync slider and text input ----

  shiny::observeEvent(input$session_window, {
    if (input$session_window != input$session_window_text) {
      shiny::freezeReactiveValue(input, "session_window_text")
      shiny::updateTextInput(
        session,
        "session_window_text",
        value = input$session_window
      )
    }
  })

  shiny::observeEvent(input$session_window_text, {
    new_value <- suppressWarnings(as.numeric(input$session_window_text))
    if (!is.na(new_value) && new_value >= 0 && new_value <= 180) {
      if (new_value != input$session_window) {
        shiny::freezeReactiveValue(input, "session_window")
        shiny::updateSliderInput(session, "session_window", value = new_value)
      }
    } else {
      if (input$session_window_text != input$session_window) {
        shiny::freezeReactiveValue(input, "session_window_text")
        shiny::updateTextInput(
          session,
          "session_window_text",
          value = input$session_window
        )
      }
    }
  })

  # Filter Visitors input behavior ----

  # Set choices when aggregated visits data is present
  shiny::observe({
    shiny::req(aggregated_visits_data())
    data <- aggregated_visits_data()
    shiny::updateSelectizeInput(
      session,
      "selected_users",
      choices = stats::setNames(data$user_guid, data$display_name),
      server = TRUE
    )
  })

  # Selection syncing behavior is made more complex because the reactable data needs
  # to be sorted differently from data for the sidebar and plots for them to appear
  # in the same order.

  aggregated_visits_reactable_data <- shiny::reactive({
    aggregated_visits_data() |>
      dplyr::arrange(dplyr::desc(n_visits), dplyr::desc(display_name))
  })

  # Sync table to sidebar
  shiny::observe({
    selected_guids_reactable <- aggregated_visits_reactable_data()[
      getReactableState("aggregated_visits", "selected"),
      "user_guid",
      drop = TRUE
    ]
    # Get indices of selected reactable GUIDs from the main table
    all_guids <- aggregated_visits_data()$"user_guid"
    selected_guids <- all_guids[which(all_guids %in% selected_guids_reactable)]
    shiny::updateSelectizeInput(
      session,
      "selected_users",
      selected = selected_guids
    )
  })

  # Sync sidebar to table
  shiny::observeEvent(
    input$selected_users,
    {
      all_guids_reactable <- aggregated_visits_reactable_data()$user_guid
      selected_indices <- which(all_guids_reactable %in% input$selected_users)
      reactable::updateReactable("aggregated_visits", selected = selected_indices)
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

  shiny::observe({
    shiny::req(scope_choices)
    shiny::updateSelectizeInput(
      session,
      "content_scope",
      choices = scope_choices,
      selected = scope_choices[1]
    )
  })

  content_unscoped <- shiny::reactive({
    connectapi::get_content(client)
  }) |>
    shiny::bindCache(active_user_guid)

  content <- shiny::reactive({
    shiny::req(input$content_scope)

    switch(
      input$content_scope,
      "all" = content_unscoped(),
      "view" = content_unscoped() |> dplyr::filter(app_role != "none"),
      "edit" = content_unscoped() |> dplyr::filter(app_role %in% c("owner", "editor")),
      "own" = content_unscoped() |> dplyr::filter(owner_guid == active_user_guid)
    )
  })

  date_range <- shiny::reactive({
    switch(
      input$date_range_choice,
      "1 Week" = list(from = lubridate::today() - lubridate::days(6), to = lubridate::today()),
      "30 Days" = list(from = lubridate::today() - lubridate::days(29), to = lubridate::today()),
      "90 Days" = list(from = lubridate::today() - lubridate::days(89), to = lubridate::today()),
      "Custom" = list(
        from = input$date_range_custom[1],
        to = input$date_range_custom[2]
      )
    )
  })

  users <- shiny::reactive({
    get_users(client) |>
      dplyr::mutate(
        full_name = paste(first_name, last_name),
        display_name = paste0(full_name, " (", username, ")")
      ) |>
      dplyr::select(user_guid = guid, full_name, username, display_name, email)
  }) |>
    shiny::bindCache(active_user_guid)

  usage_data_meta <- shiny::reactive({
    shiny::req(active_user_role %in% c("administrator", "publisher"))
    dat <- get_usage(
      client,
      from = date_range()$from,
      to = date_range()$to
    )
    list(
      data = dat,
      last_updated = Sys.time()
    )
  }) |>
    shiny::bindCache(active_user_guid, date_range())

  usage_data_raw <- shiny::reactive({
    usage_data_meta()$data
  })

  usage_last_updated <- shiny::reactive({
    usage_data_meta()$last_updated
  })

  # Multi-content table data ----

  # Filter the raw data based on selected scope, app mode and session window
  usage_data_visits <- shiny::reactive({
    shiny::req(content())
    scope_filtered_usage <- usage_data_raw() |>
      dplyr::filter(content_guid %in% content()$guid)

    app_mode_filtered_usage <- if (length(input$app_mode_filter) == 0) {
      scope_filtered_usage
    } else {
      app_modes <- unlist(app_mode_groups[input$app_mode_filter])
      filter_guids <- content() |>
        dplyr::filter(app_mode %in% app_modes) |>
        dplyr::pull(guid)
      scope_filtered_usage |>
        dplyr::filter(content_guid %in% filter_guids)
    }

    shiny::req(input$session_window)
    filter_visits_by_time_window(app_mode_filtered_usage, input$session_window)
  })

  # Create data for the main table and summary export.
  multi_content_table_data <- shiny::reactive({
    shiny::req(nrow(usage_data_visits()) > 0)
    usage_summary <- usage_data_visits() |>
      dplyr::group_by(content_guid) |>
      dplyr::summarize(
        total_views = dplyr::n(),
        unique_viewers = dplyr::n_distinct(user_guid, na.rm = TRUE),
        .groups = "drop"
      )

    # Prepare sparkline data.
    all_dates <- seq.Date(date_range()$from, date_range()$to, by = "day")
    daily_usage <- usage_data_visits() |>
      dplyr::count(content_guid, date = lubridate::date(timestamp)) |>
      tidyr::complete(date = all_dates, tidyr::nesting(content_guid), fill = list(n = 0)) |>
      dplyr::group_by(content_guid) |>
      dplyr::summarize(sparkline = list(n), .groups = "drop")

    content() |>
      dplyr::mutate(owner_username = purrr::map_chr(owner, "username")) |>
      dplyr::select(title, content_guid = guid, owner_username, dashboard_url) |>
      tidyr::replace_na(list(title = "[Untitled]")) |>
      dplyr::right_join(usage_summary, by = "content_guid") |>
      dplyr::right_join(daily_usage, by = "content_guid") |>
      tidyr::replace_na(list(title = "[Deleted]")) |>
      dplyr::arrange(dplyr::desc(total_views)) |>
      dplyr::select(
        title,
        dashboard_url,
        content_guid,
        owner_username,
        total_views,
        sparkline,
        unique_viewers
      )
  })

  # Multi-content table UI and outputs ----

  output$summary_text <- shiny::renderText(
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

  output$last_updated <- shiny::renderText({
    fmt <- "%Y-%m-%d %l:%M:%S %p %Z"
    paste0("Updated ", format(usage_last_updated(), fmt))
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

  output$content_usage_table <- reactable::renderReactable({
    data <- multi_content_table_data()

    table <- reactable::reactable(
      data,
      defaultSortOrder = "desc",
      onClick = htmlwidgets::JS(
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
      language = reactable::reactableLang(
        searchPlaceholder = "Search by title, URL, GUID, or owner"
      ),
      highlight = TRUE,
      defaultSorted = "total_views",
      style = list(cursor = "pointer"),
      wrap = FALSE,
      class = "metrics-tbl",

      columns = list(
        title = reactable::colDef(
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

        dashboard_url = reactable::colDef(
          name = "",
          width = 32,
          sortable = FALSE,
          cell = function(url) {
            if (is.na(url) || url == "") {
              return("")
            }
            shiny::HTML(as.character(shiny::tags$div(
              onclick = "event.stopPropagation()",
              shiny::tags$a(
                href = url,
                target = "_blank",
                bsicons::bs_icon("arrow-up-right-square")
              )
            )))
          },
          html = TRUE
        ),

        content_guid = reactable::colDef(
          name = "GUID",
          show = input$show_guid,
          class = "number",
          cell = function(value) {
            shiny::div(
              style = list(whiteSpace = "normal", wordBreak = "break-all"),
              value
            )
          }
        ),

        owner_username = reactable::colDef(
          name = "Owner",
          defaultSortOrder = "asc",
          minWidth = 75
        ),

        total_views = reactable::colDef(
          name = "Visits",
          align = "left",
          minWidth = 75,
          maxWidth = 150,
          cell = function(value) {
            max_val <- max(data$total_views, na.rm = TRUE)
            bar_chart(value, max_val, fill = "#7494b1", background = "#e1e1e1")
          }
        ),

        sparkline = reactable::colDef(
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

        unique_viewers = reactable::colDef(
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

    # Apply any onRender JS for capturing search value
    htmlwidgets::onRender(table, table_js)
  })

  output$export_raw_visits <- shiny::downloadHandler(
    filename = function() {
      paste0("content_raw_visits_", Sys.Date(), ".csv")
    },
    content = function(file) {
      write.csv(usage_data_raw(), file, row.names = FALSE)
    }
  )

  output$export_visit_totals <- shiny::downloadHandler(
    filename = function() {
      paste0("content_visit_totals_", Sys.Date(), ".csv")
    },
    content = function(file) {
      to_export <- multi_content_table_data() |>
        dplyr::select(-sparkline)
      write.csv(to_export, file, row.names = FALSE)
    }
  )

  # Single-content detail view data ----

  selected_content_usage <- shiny::reactive({
    shiny::req(selected_guid())
    usage_data_raw() |>
      dplyr::filter(content_guid == selected_guid())
  })

  all_visits_data <- shiny::reactive({
    all_visits <- selected_content_usage() |>
      # Compute time diffs and filter out hits within the session
      dplyr::group_by(user_guid) |>
      dplyr::mutate(time_diff = lubridate::seconds(timestamp - dplyr::lag(timestamp, 1))) |>
      tidyr::replace_na(list(time_diff = lubridate::seconds(Inf))) |>
      dplyr::filter(time_diff > input$session_window) |>
      dplyr::ungroup() |>

      # Join to usernames
      dplyr::left_join(users(), by = "user_guid") |>
      tidyr::replace_na(list(
        user_guid = "ANONYMOUS",
        display_name = "[Anonymous]"
      )) |>
      dplyr::arrange(dplyr::desc(timestamp)) |>
      dplyr::select(user_guid, display_name, timestamp)

    # If any users are selected for filtering, filter by their GUIDs
    if (length(input$selected_users) > 0) {
      all_visits <- dplyr::filter(all_visits, user_guid %in% input$selected_users)
    }
    all_visits
  })

  aggregated_visits_data <- shiny::reactive({
    filtered_visits <- selected_content_usage() |>
      dplyr::group_by(user_guid) |>

      # Compute time diffs and filter out hits within the session
      dplyr::mutate(time_diff = lubridate::seconds(timestamp - dplyr::lag(timestamp, 1))) |>
      tidyr::replace_na(list(time_diff = lubridate::seconds(Inf))) |>
      dplyr::filter(time_diff > input$session_window) |>

      dplyr::summarize(n_visits = dplyr::n())

    filtered_visits |>
      dplyr::left_join(users(), by = "user_guid") |>
      tidyr::replace_na(list(
        user_guid = "ANONYMOUS",
        display_name = "[Anonymous]"
      )) |>
      dplyr::arrange(dplyr::desc(n_visits), display_name) |>
      dplyr::select(user_guid, display_name, email, n_visits)
  })

  selected_content_info <- shiny::reactive({
    shiny::req(selected_guid())
    dplyr::filter(content(), guid == selected_guid())
  })

  # Single-content detail view UI and outputs ----

  output$aggregated_visits <- reactable::renderReactable({
    reactable::reactable(
      aggregated_visits_reactable_data(),
      selection = "multiple",
      onClick = "select",
      defaultSorted = "n_visits",
      class = "metrics-tbl",
      style = list(cursor = "pointer"),
      wrap = FALSE,
      columns = list(
        user_guid = reactable::colDef(show = FALSE),
        display_name = reactable::colDef(name = "Visitor"),
        email = reactable::colDef(
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
              "mailto:{url}?subject={utils::URLencode(subject, reserved = TRUE)}"
            )
            shiny::HTML(as.character(shiny::tags$div(
              onclick = "event.stopPropagation()",
              shiny::tags$a(
                href = mailto,
                shiny::icon("envelope")
              )
            )))
          },
          html = TRUE
        ),
        n_visits = reactable::colDef(
          name = "Visits",
          defaultSortOrder = "desc",
          maxWidth = 75,
          class = "number"
        )
      )
    )
  })

  output$all_visits <- reactable::renderReactable({
    reactable::reactable(
      all_visits_data(),
      defaultSorted = "timestamp",
      class = "metrics-tbl",
      wrap = FALSE,
      columns = list(
        user_guid = reactable::colDef(show = FALSE),
        timestamp = reactable::colDef(
          name = "Time",
          format = reactable::colFormat(datetime = TRUE, time = TRUE),
          defaultSortOrder = "desc",
          class = "number"
        ),
        display_name = reactable::colDef(name = "Visitor")
      )
    )
  })

  output$filter_message <- shiny::renderUI({
    hits <- all_visits_data()
    glue::glue(
      "{nrow(hits)} visits between ",
      "{date_range()$from} and {date_range()$to}."
    )
    if (length(input$selected_users) > 0) {
      users <- aggregated_visits_data() |>
        dplyr::filter(user_guid %in% input$selected_users) |>
        dplyr::pull(display_name)
      user_string <- if (length(users) == 1) {
        users
      } else {
        "multiple selected users"
      }
      shiny::tagList(
        shiny::HTML(glue::glue(
          "{nrow(hits)} visits from <b>{user_string}</b> between ",
          "{date_range()$from} and {date_range()$to}."
        )),
        actionLink(
          "clear_selection",
          glue::glue("Clear filter"),
          icon = shiny::icon("times")
        )
      )
    } else {
      glue::glue(
        "{nrow(hits)} total visits between ",
        "{date_range()$from} and {date_range()$to}."
      )
    }
  })

  output$content_title <- shiny::renderText({
    shiny::req(selected_content_info())
    selected_content_info()$title
  })

  output$content_guid <- shiny::renderText({
    shiny::req(selected_content_info())
    selected_content_info()$guid
  })

  output$dashboard_link <- shiny::renderUI({
    shiny::req(selected_content_info())
    url <- selected_content_info()$dashboard_url
    shiny::tags$a(
      href = url,
      class = "btn btn-sm btn-outline-secondary",
      target = "_blank",
      shiny::div(
        style = "white-space: nowrap;",
        shiny::icon("arrow-up-right-from-square"),
        "Open"
      )
    )
  })

  output$owner_info <- shiny::renderText({
    shiny::req(selected_content_info())
    if (nrow(selected_content_info()) == 1) {
      owner <- dplyr::filter(
        users(),
        user_guid == selected_content_info()$owner[[1]]$guid
      )
      glue::glue("Owner: {owner$display_name}")
    }
  })

  output$email_owner_button <- shiny::renderUI({
    owner_email <- users() |>
      dplyr::filter(user_guid == selected_content_info()$owner[[1]]$guid) |>
      dplyr::pull(email)
    subject <- glue::glue(
      "\"{selected_content_info()$title}\" on Posit Connect"
    )
    mailto <- glue::glue(
      "mailto:{owner_email}",
      "?subject={utils::URLencode(subject, reserved = TRUE)}"
    )
    shiny::tags$a(
      href = mailto,
      class = "btn btn-sm btn-outline-secondary",
      target = "_blank",
      shiny::div(
        style = "white-space: nowrap;",
        shiny::icon("envelope"),
        "Email"
      )
    )
  })

  output$email_selected_visitors_button <- shiny::renderUI({
    shiny::req(selected_content_info())
    emails <- users() |>
      dplyr::filter(user_guid %in% input$selected_users) |>
      dplyr::pull(email) |>
      stats::na.omit()

    disabled <- if (length(emails) == 0) "disabled" else NULL

    subject <- glue::glue(
      "\"{selected_content_info()$title}\" on Posit Connect"
    )
    mailto <- glue::glue(
      "mailto:{paste(emails, collapse = ',')}",
      "?subject={utils::URLencode(subject, reserved = TRUE)}"
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
      shiny::tagList(shiny::icon("envelope"), "Email Selected Visitors")
    )
  })

  # Plots for single-content view ----

  daily_hit_data <- shiny::reactive({
    all_dates <- seq.Date(date_range()$from, date_range()$to, by = "day")

    all_visits_data() |>
      dplyr::mutate(date = lubridate::date(timestamp)) |>
      dplyr::group_by(date) |>
      dplyr::summarize(daily_visits = dplyr::n(), .groups = "drop") |>
      tidyr::complete(date = all_dates, fill = list(daily_visits = 0))
  })

  output$daily_visits_plot <- plotly::renderPlotly({
    p <- ggplot2::ggplot(
      daily_hit_data(),
      ggplot2::aes(
        x = date,
        y = daily_visits,
        text = paste("Date:", date, "<br>Visits:", daily_visits)
      )
    ) +
      ggplot2::geom_bar(stat = "identity", fill = "#447099") +
      ggplot2::labs(y = "Visits", x = "Date") +
      ggplot2::theme_minimal()
    plotly::ggplotly(p, tooltip = "text")
  })

  output$visit_timeline_plot <- plotly::renderPlotly({
    visit_order <- aggregated_visits_data()$display_name
    data <- all_visits_data() |>
      dplyr::mutate(display_name = factor(display_name, levels = rev(visit_order)))

    from <- as.POSIXct(paste(date_range()$from, "00:00:00"), tz = "")
    to <- as.POSIXct(paste(date_range()$to, "23:59:59"), tz = "")
    p <- ggplot2::ggplot(
      data,
      ggplot2::aes(
        x = timestamp,
        y = display_name,
        text = paste("Timestamp:", timestamp)
      )
    ) +
      ggplot2::geom_point(color = "#447099") +
      # Plotly output does not yet support `position = "top"`, but it should be
      # supported in the next release.
      # https://github.com/plotly/plotly.R/issues/808
      ggplot2::scale_x_datetime(position = "top", limits = c(from, to)) +
      ggplot2::theme_minimal() +
      ggplot2::theme(axis.title.y = ggplot2::element_blank(), axis.ticks.y = ggplot2::element_blank())
    plotly::ggplotly(p, tooltip = "text")
  })

  output$visit_timeline_ui <- shiny::renderUI({
    n_users <- length(unique(all_visits_data()$display_name))
    row_height <- 20 # visual pitch per user
    label_buffer <- 50 # additional padding for y-axis labels
    toolbar_buffer <- 80 # plotly toolbar & margins

    height_px <- n_users * row_height + label_buffer + toolbar_buffer

    shinycssloaders::withSpinner(plotly::plotlyOutput(
      "visit_timeline_plot",
      height = paste0(height_px, "px")
    ))
  })

  # Global UI elements ----

  output$page_title_bar <- shiny::renderUI({
    if (is.null(selected_guid())) {
      "Usage"
    } else {
      shiny::div(
        style = "display: flex; justify-content: space-between; gap: 1rem; align-items: baseline;",
        shiny::actionButton(
          "clear_content_selection",
          "Back",
          shiny::icon("arrow-left"),
          class = "btn btn-sm",
          style = "white-space: nowrap;"
        ),
        shiny::span(
          "Usage / ",
          textOutput("content_title", inline = TRUE)
        ),
        shiny::code(
          class = "text-muted",
          style = "font-family: \"Fira Mono\", Consolas, Monaco, monospace; font-size: 0.875rem;",
          shiny::textOutput("content_guid", inline = TRUE)
        ),
        shiny::uiOutput("dashboard_link")
      )
    }
  })
}

shiny::enableBookmarking("url")
shiny::shinyApp(ui, server)
