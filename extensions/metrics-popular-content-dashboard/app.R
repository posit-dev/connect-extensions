library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(lubridate)
library(dplyr)
library(ggplot2)
library(plotly)
library(tidyr)
library(pins)
library(vctrs)

METRICS_PIN_NAME = "static_usage_cache"
NA_datetime_ <- # nolint: object_name_linter
  vctrs::new_datetime(NA_real_, tzone = "UTC")
NA_list_ <- # nolint: object_name_linter
  list(list())

# Get the usage data pinned from the cache. If `from` and `to` filters are
# provided, filter the output (to mirror `connectapi`'s usage function). If no
# filters are provided, just return everything.
get_usage_pin <- function(from = NULL, to = NULL) {
  board <- board_connect(auth = "envvar")

  usage_pin <- tryCatch(
    pin_read(board, METRICS_PIN_NAME),
    error = function(e) {
      if (inherits(e, "pins_pin_missing")) {
        return(
            tibble::tibble(
            "content_guid" = NA_character_,
            "user_guid" = NA_character_,
            "variant_key" = NA_character_,
            "time" = NA_datetime_,
            "rendering_id" = NA_character_,
            "bundle_id" = NA_character_,
            "data_version" = NA_integer_
          )
        )
      } else {
        stop(e)
      }
    }
  )

  if (!is.null(from) && !is.null(to)) {
    filter(
      usage_pin,
      date(time) >= from,
      date(time) <= to
    )
  } else {
    usage_pin
  }
}

write_usage_pin <- function(usage) {
  board <- board_connect(auth = "envvar")
  pin_write(board, usage, name = METRICS_PIN_NAME)
}

# Returns a vector of missing dates
missing_dates <- function(from, to, dates) {
  dates <- unique(dates)
  date_range <- seq.Date(from, to, by = "day")
  result <- setdiff(date_range, dates)
  class(result) <- class(date_range)
  result
}

# Get pin usage. Remove duplicated dates from new usage data. Bind rows.
# > dput(pinned_dates)
# structure(c(20138, 20139, 20140, 20141, 20143, 20144), class = "Date")
# > dput(new_dates)
# structure(c(20141, 20142), class = "Date")
# > pinned_dates
# [1] "2025-02-19" "2025-02-20" "2025-02-21" "2025-02-22" "2025-02-24" "2025-02-25"
# > new_dates
# [1] "2025-02-22" "2025-02-23"
update_usage_pin <- function(usage) {
  # Get all the pinned usage data.
  usage_pin <- get_usage_pin()

  # Filter the new usage data to only include dates not present in the pinned usage data.
  pinned_dates <- unique(date(usage_pin$time))
  new_dates <- unique(date(usage$time))

  date_diff <- setdiff(new_dates, pinned_dates)
  class(date_diff) <- class(new_dates)

  additional_usage <- filter(usage, date(time) %in% date_diff)

  combined_usage <- bind_rows(usage_pin, additional_usage) |>
    arrange(time)

  # FIXME We don't cache today's data. This is kinda hacky, but we must assume
  # that today's data will never be complete.
  combined_usage <- filter(combined_usage, date(time) != today())

  cat(paste0("Updating pinned usage data with data from the following days:"))
  cat(as.character(unique(date(additional_usage$time))))

  write_usage_pin(combined_usage)
}

get_usage <- function(client, from, to) {
  # Always fetch today from the API.
  if (to == today()) {
    pin_to <- to - 1
  } else {
    pin_to <- to
  }

  # FIXME The API treats "to" as the *start* of the day so all this needs to be updated.

  # FIXME We only want up to yesterday's data from the pin.
  usage_pin <- get_usage_pin(from, pin_to)
  # FIXME The pin is only invalid based on yesterday, we never get today from it.
  if (length(missing_dates(from, pin_to, date(usage_pin$time))) == 0) {
    # FIXME What if one of the days is incomplete
    if (to == today()) {
      usage_today <- get_usage_static(
        client,
        from = to - 1,
        to = to,
        limit = Inf
      ) |>
        filter(time > max(usage_pin$time))
      usage_pin <- bind_rows(usage_pin, usage_today)
    }
    return(usage_pin)
  } else {
    usage_api <- get_usage_static(
      client,
      from = from,
      to = to,
      limit = Inf
    )
    update_usage_pin(usage_api)
    return(usage_api)
  }
}

fetch_data <- function(client, start_date = NULL, end_date = NULL, content_scope = NULL, force_api = FALSE) {
  if (is.null(end_date)) {
    end_date <- today()
  }
  if (is.null(start_date)) {
    start_date <- end_date - ddays(7)
  }
  duration_days <- as.numeric(end_date - start_date)
  duration_weeks <- duration_days / 7

  if (force_api) {
    usage <- get_usage_static(
      client,
      from = start_date,
      to = end_date,
      limit = Inf
    )
  } else {
    usage <- get_usage(
      client,
      from = start_date,
      to = end_date
    )
  }

  content <- switch(
    content_scope,
    "all" = get_content(client),
    "view" = get_content(client) |> filter(app_role != "none"),
    "own" = get_content(client, owner_guid = client$me()$guid),
    get_content(client)
  )

  list(
    usage = usage,
    content = content
  )
}

compute_stats <- function(usage, content, app_mode_mask = c(), start_date, end_date) {
  if (length(app_mode_mask) > 0) {
    content <- filter(content, app_mode %in% app_mode_mask)
    usage <- filter(usage, content_guid %in% content$guid)
  }

  duration_days <- as.numeric(end_date - start_date)
  duration_weeks <- duration_days / 7

  daily_stats <- usage |>
    mutate(date = date(time)) |>
    group_by(content_guid, date) |>
    summarize(
      daily_visitors = n_distinct(user_guid, na.rm = TRUE),
      daily_hits = n(),
      .groups = "drop_last"
    ) |>
    summarize(
      mean_daily_visitors = sum(daily_visitors) / duration_days,
      mean_daily_hits = sum(daily_hits) / duration_days
    )

  weekly_stats <- usage |>
    mutate(week = week(time)) |>
    group_by(content_guid, week) |>
    summarize(
      weekly_visitors = n_distinct(user_guid, na.rm = TRUE),
      weekly_hits = n(),
      .groups = "drop_last"
    ) |>
    summarize(
      mean_weekly_visitors = sum(weekly_visitors) / duration_weeks,
      mean_weekly_hits = sum(weekly_hits) / duration_weeks
    )

  total_stats <- usage |>
    group_by(content_guid) |>
    summarize(
      total_hits = n(),
      anonymous_hits = sum(is.na(user_guid)),
      unique_visitors = n_distinct(user_guid, na.rm = TRUE),
      hits_per_visitor = (total_hits - anonymous_hits) / unique_visitors
    )

  content_usage <- content |>
    select(guid, title, app_mode) |>
    inner_join(total_stats, c("guid" = "content_guid")) |>
    left_join(weekly_stats, c("guid" = "content_guid")) |>
    left_join(daily_stats, c("guid" = "content_guid"))


  daily_usage <- usage |>
    mutate(date = date(time)) |>
    group_by(date) |>
    summarize(
      daily_visitors = n_distinct(user_guid, na.rm = TRUE),
      total_hits = n()
    )

  return(list(
    content_usage = content_usage,
    daily_usage = daily_usage
  ))
}

compute_content_plot <- function(usage, target_guid) {
  date_range <- seq.Date(min(date(usage$time), na.rm = TRUE), max(date(usage$time), na.rm = TRUE), by = "day")

  # Summarize usage data
  usage_summary <- usage |>
    filter(content_guid == target_guid) |>
    mutate(date = date(time)) |>
    group_by(date) |>
    summarize(
      daily_visitors = n_distinct(user_guid, na.rm = TRUE),
      total_hits = n(),
      .groups = "drop"
    )

  # Ensure all dates are represented
  full_data <- tibble(date = date_range) |>
    full_join(usage_summary, by = "date") |>
    mutate(across(c(daily_visitors, total_hits), ~ replace_na(.x, 0)))

  full_data
}

# Define the modal UI separately
contentDetailsModal <- function() {
  modalDialog(
    size = "l",
    title = textOutput("modal_title"),

    layout_columns(
      value_box(
        "Total Views",
        textOutput("modal_views"),
        showcase = bsicons::bs_icon("eye")
      ),
      value_box(
        "Unique Visitors",
        textOutput("modal_users"),
        showcase = bsicons::bs_icon("people")
      )
    ),

    card(
      "Hits Per Day",
      plotlyOutput("modal_plot")
    ),

    footer = actionButton("close_modal", "Close")
  )
}

ui <- page_sidebar(
  title = "Posit Connect Usage Metrics",
  sidebar = sidebar(
    dateRangeInput(
      "date_range",
      "Date Range",
      start = today() - ddays(7),
      end = today()
    ),
    selectizeInput(
      "app_mode_mask",
      "Content Type Filter",
      choices = c("static", "unknown", "shiny", "rmd-shiny", "quarto-static",
        "python-shiny", "rmd-static", "python-streamlit", "python-fastapi",
        "python-dash", "jupyter-static", "api", "jupyter-voila", "python-gradio",
        "python-api", "python-bokeh", "quarto-shiny", "tensorflow-saved-model"),
      multiple = TRUE
    ),
    selectizeInput(
      "content_scope",
      "Content Scope",
      choices = list(
        "My content" = "own",
        "Content I can see" = "view",
        "All content" = "all"
      ),
      selected = "all"
    )
    # Add more filters as needed
  ),

  card(
    layout_columns(
      value_box(
        "Total Views",
        textOutput("total_views"),
        showcase = bsicons::bs_icon("eye")
      ),
      value_box(
        "Active Users",
        textOutput("total_users"),
        showcase = bsicons::bs_icon("people")
      ),
      value_box(
        "Active Content",
        textOutput("total_content"),
        showcase = bsicons::bs_icon("file-earmark")
      ),
      max_height = "150px"
    ),
    card(
      card_header("Daily Usage"),
      plotlyOutput("aggregate_plot")
    ),
    card(
      card_header("Most Popular Content"),
      DTOutput("content_table")
    )
  )
)

server <- function(input, output, session) {
  publisher_client <- connect()
  user_session_token <- session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN

  if (connectapi:::compare_connect_version(publisher_client$version, "2025.01.0") >= 0) {
    visitor_client <- connect(token = user_session_token)
    scope_choices_active <- TRUE
  } else {
    visitor_client <- publisher_client
    scope_choices_active <- FALSE
  }

  visitor_role <- visitor_client$me()$user_role

  # Define available content scope options based on user role
  observe({
    if (scope_choices_active) {
      scope_choices <- switch(
        visitor_role,
        "publisher" = list("My content" = "own", "Content I can see" = "view", "All content" = "all"),
        "administrator" = list("My content" = "own", "Content I can see" = "view", "All content" = "all"),
        list("My content" = "own")
      )
      updateSelectizeInput(session, "content_scope", choices = scope_choices, selected = "all")
    } else {
      updateSelectizeInput(session, "content_scope", label = "Content Scope [requires Connect 2025.01.0]", choices = list(), selected = "all")
    }
  })

  usage_data <- reactive({
    withProgress(
      {
        fetch_data(visitor_client, input$date_range[1], input$date_range[2], input$content_scope)
      },
      message = "Fetching data...",
      value = NULL
    )
  })

  # Reactive data source
  usage_stats <- reactive({
    withProgress(
      {
        compute_stats(
          usage_data()$usage,
          usage_data()$content,
          input$app_mode_mask,
          input$date_range[1],
          input$date_range[2]
        )
      },
      message = "Computing stats...",
      value = NULL
    )
  })

  # Reactive value to store selected content ID
  selected_content <- reactiveVal(NULL)

    # Add these back in
    output$total_views <- renderText({
      sum(usage_stats()$content_usage$total_hits)
    })

    output$total_users <- renderText({
      sum(usage_stats()$daily_usage$daily_visitors)
    })

    output$total_content <- renderText({
      nrow(usage_stats()$content_usage)
    })

  # Render the main content table
  output$content_table <- renderDT({
    print(usage_stats()$content_usage)
    datatable(
      usage_stats()$content_usage,
      selection = "single",
      options = list(
        order = list(list(4, "desc"))
      ),
      colnames = c(
        "GUID" = "guid",
        "Title" = "title",
        "Content Type" = "app_mode",
        "Total Hits" = "total_hits",
        "Anonymous Hits" = "anonymous_hits",
        "Unique Visitors" = "unique_visitors",
        "Hits per Visitor" = "hits_per_visitor",
        "Mean Weekly Visitors" = "mean_weekly_visitors",
        "Mean Weekly Hits" = "mean_weekly_hits",
        "Mean Daily Visitors" = "mean_daily_visitors",
        "Mean Daily Hits" = "mean_daily_hits"
      )
    ) |>
      formatRound(columns = c(
        "Mean Weekly Visitors",
        "Mean Weekly Hits",
        "Mean Daily Visitors",
        "Mean Daily Hits"
      ), digits = 2)
  })

  output$aggregate_plot <- renderPlotly(
    {
      ggplotly(
        ggplot(usage_stats()$daily_usage) +
          geom_line(aes(x = date, y = total_hits)) +
            labs(x = "Date", y = "Hits")
      )
    }
  )

  observe(print(input$content_table_rows_selected))

  # Show modal when table row is selected
  observeEvent(input$content_table_rows_selected, {
    req(input$content_table_rows_selected)
    showModal(contentDetailsModal())

    selected_row <- usage_stats()$content_usage[input$content_table_rows_selected, ]

    req(nrow(selected_row) > 0)

    # Update modal content
    output$modal_title <- renderText(selected_row$title)
    output$modal_views <- renderText(selected_row$total_hits)  # Changed from views to total_hits
    output$modal_users <- renderText(selected_row$unique_visitors)  # Changed from users to mean_daily_visitors
    output$modal_plot <- renderPlotly(
      ggplotly(
        ggplot(compute_content_plot(usage_data()$usage, selected_row$guid)) +
          geom_col(aes(x = date, y = total_hits)) +
            labs(x = "Date", y = "Hits")
      )
    )
  })

  observeEvent(input$close_modal, {
    removeModal()
    # Deselect the table row
    proxy <- dataTableProxy("content_table")
    selectRows(proxy, NULL)
  })
}

shinyApp(ui, server)
