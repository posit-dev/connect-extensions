library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(lubridate)
library(dplyr)
library(ggplot2)
library(plotly)

fetch_data <- function(client, start_date = NULL, end_date = NULL, content_scope = NULL) {
  if (is.null(end_date)) {
    end_date <- today()
  }
  if (is.null(start_date)) {
    start_date <- end_date - ddays(7)
  }
  duration_days <- as.numeric(end_date - start_date)
  duration_weeks <- duration_days / 7

  usage <- get_usage_static(
    client,
    from = start_date,
    to = end_date,
    limit = Inf
  )


  content <- switch(
    content_scope,
    "all" = get_content(client),
    "view" = get_content(client) |> filter(app_role != "none"),
    get_content(client, owner_guid = client$me()$guid)
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
    right_join(total_stats, c("guid" = "content_guid")) |>
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

# content_detail_data <- function(usage, guid) {

# }


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
        "Unique Users",
        textOutput("modal_users"),
        showcase = bsicons::bs_icon("people")
      )
    ),

    card(
      "Usage Over Time"
      # Add a plot or more detailed statistics here
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
      )
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
  visitor_client <- connect(token = user_session_token)

  visitor_role <- visitor_client$me()$user_role

  # Define available content scope options based on user role
  observe({
    scope_choices <- switch(
      visitor_role,
      "publisher" = list("My content" = "own", "Content I can see" = "view", "All content" = "all"),
      "administrator" = list("My content" = "own", "Content I can see" = "view", "All content" = "all"),
      list("My content" = "own")
    )

    updateSelectizeInput(session, "content_scope", choices = scope_choices, selected = "own")
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

  # Show modal when table row is selected
  observeEvent(input$content_table_rows_selected, {
    req(input$content_table_rows_selected)
    showModal(contentDetailsModal())

    req(nrow(selected_row) > 0)

    # Update modal content
    selected_row <- usage_stats()$content_usage[input$content_table_rows_selected, ]
    output$modal_title <- renderText(selected_row$title)
    output$modal_views <- renderText(selected_row$total_hits)  # Changed from views to total_hits
    output$modal_users <- renderText(selected_row$mean_daily_visitors)  # Changed from users to mean_daily_visitors
  })

  observeEvent(input$close_modal, {
    removeModal()
    # Deselect the table row
    proxy <- dataTableProxy("content_table")
    selectRows(proxy, NULL)
  })
}

shinyApp(ui, server)
