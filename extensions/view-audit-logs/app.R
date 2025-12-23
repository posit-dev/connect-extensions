library(shiny)
library(bslib)
library(dplyr)
library(ggplot2)
library(lubridate)
library(connectapi)
library(pins)
library(plotly)

# UI definition
ui <- page_fillable(
  theme = bs_theme(version = 5),

  # Title bar
  card(
    full_screen = TRUE,
    card_header("Posit Connect Audit Logs"),

    layout_sidebar(
      # Sidebar with filter controls
      sidebar = sidebar(
        title = "Filters",

        dateRangeInput(
          "date_filter",
          "Filter by Date",
          start = today() - ddays(6)
        ),

        accordion(
          accordion_panel(
            "Actions",
            selectInput(
              "actions_exclude",
              "Exclude",
              choices = NULL,
              multiple = TRUE
            ),
            selectInput(
              "actions_include",
              "Include",
              choices = NULL,
              multiple = TRUE
            )
          ),
          accordion_panel(
            "Users",
            selectInput(
              "users_exclude",
              "Exclude",
              choices = "Git repository checker",
              selected = "Git repository checker",
              multiple = TRUE
            ),
            selectInput(
              "users_include",
              "Include",
              choices = NULL,
              multiple = TRUE
            )
          ),
          open = TRUE
        )

      ),

      # Main panel with visualizations and list
      card(
        # card_header("Activity Overview"),
        card_body(
          height = "500px",  # Set explicit height
          tabsetPanel(
            tabPanel(
              "Summary",
              layout_column_wrap(
                width = 1/2,
                height = "100%",  # Use full height
                gap = "1rem",
                card(
                  height = "100%",  # Make card fill space
                  card_header("Events by Type"),
                  card_body(
                    plotlyOutput("event_plot")
                  )
                ),
                card(
                  height = "100%",  # Make card fill space
                  card_header("Activity Timeline"),
                  card_body(
                    plotlyOutput("timeline_plot")
                  )
                )
              )
            ),
            tabPanel(
              "Activity By User",
              plotlyOutput("user_timeline")
            ),
            tabPanel(
              "Activity By Event Type",
              plotlyOutput("action_timeline")
            ),
            tabPanel(
              "Event List",
              card(
                card_header("Event List"),
                div(
                  style = "overflow-y: auto;",
                  reactable::reactableOutput("audit_list")
                )
              )
            )
          )
        )
      )

    )
  )
)

# Server logic
server <- function(input, output, session) {
  # Reactive expression to fetch audit logs
  audit_data <- reactive({
    board <- board_connect()
    PIN_NAME <- paste0(board$account, "/", "connect_metrics_cache_audit_logs")
    pin_read(board, PIN_NAME)
  })

    # Update date range input
    observe({
      req(audit_data())
      updateDateRangeInput(
        session,
        "date_filter",
        min = min(audit_data()$time, na.rm = TRUE)
      )
    })

  date_filtered_audits <- reactive(
    audit_data() |>
      filter(
        time >= input$date_filter[1],
        time <= input$date_filter[2] + 86399  # Add 23h 59m 59s
      )
  )

  # Handle action filters updates
  observe({
    data <- date_filtered_audits()
    actions <- data |>
      count(action) |>
      arrange(desc(n))

    all_actions <- actions$action

    updateSelectInput(session, "actions_exclude",
      choices = all_actions,
      selected = input$actions_exclude
    )

    remaining_actions <- setdiff(all_actions, input$actions_exclude)

    updateSelectInput(session, "actions_include",
      choices = remaining_actions,
      selected = input$actions_include
    )
  })


  # Handle user filter updates
  observe({
    data <- date_filtered_audits()
    users <- data %>%
      count(user_description) %>%
      arrange(desc(n))

    all_users <- users$user_description

    updateSelectInput(session, "users_exclude",
      choices = all_users,
      selected = input$users_exclude
    )

    remaining_actions <- setdiff(all_users, input$users_exclude)

    updateSelectInput(session, "users_include",
      choices = remaining_actions,
      selected = input$users_include
    )
  })

  # Filter data based on user inputs
  user_and_action_filtered_audits <- reactive({
    req(date_filtered_audits())
    data <- date_filtered_audits()

    if (!is.null(input$actions_exclude) && length(input$actions_exclude) > 0) {
      data <- data %>% filter(!(action %in% input$actions_exclude))
    }

    if (!is.null(input$actions_include) && length(input$actions_include) > 0) {
      data <- data %>% filter(action %in% input$actions_include)
    }

    if (!is.null(input$users_exclude) && length(input$users_exclude) > 0) {
      data <- data %>% filter(!(user_description %in% input$users_exclude))
    }

    if (!is.null(input$users_include) && length(input$users_include) > 0) {
      data <- data %>% filter(user_description %in% input$users_include)
    }

    data
  })

  # Action type plot
  output$event_plot <- renderPlotly({

    data <- user_and_action_filtered_audits()

    # Explicitly check for data
    validate(need(nrow(data) > 0, "No data available for plotting"))

    tryCatch({
      # Create summary data
      plot_data <- data %>%
        count(action)

      # Create plot
      p <- ggplot(plot_data, aes(x = reorder(action, n), y = n)) +
        geom_col(fill = "#0055AA") +
        coord_flip() +
        labs(x = "Action Type", y = "Count") +
        theme_minimal()
      ggplotly(p)

    }, error = function(e) {

      NULL
    })
  })

  # Timeline plot
  output$timeline_plot <- renderPlotly({

    audit_data <- user_and_action_filtered_audits()

    binwidth <- 3600

    bins <- seq(from = min(audit_data$time),
                    to = max(audit_data$time),
                    by = binwidth)

    # Per user time plot
    plot_data <- audit_data %>%
      mutate(bin_time = cut(time, breaks = bins)) %>%
      group_by(bin_time) %>%
      summarize(count = n(), .groups = "drop") %>%
      mutate(bin_time = as.POSIXct(bin_time, format = "%Y-%m-%d %H:%M:%S")) %>%
      tidyr::complete(bin_time = bins, fill = list(count = 0))

    p <- ggplot(plot_data, aes(x = bin_time, y = count)) +
      geom_line() +
      labs(x = "Time", y = "Event Count") +
      theme_minimal() +
      guides(color = "none")
    ggplotly(p)
  })

  output$user_timeline <- renderPlotly({
    audit_data <- user_and_action_filtered_audits()

    binwidth <- 3600

    bins <- seq(from = min(audit_data$time),
                    to = max(audit_data$time) + 3600,
                    by = binwidth)

    # Per user time plot
    plot_data <- audit_data %>%
      mutate(bin_time = cut(time, breaks = bins)) %>%
      group_by(bin_time, user_description) %>%
      summarize(count = n(), .groups = "drop") %>%
      mutate(bin_time = as.POSIXct(bin_time, format = "%Y-%m-%d %H:%M:%S")) %>%
      tidyr::complete(bin_time = bins, user_description, fill = list(count = 0))

    # Identify top n users
    top_n_users <- plot_data %>%
      group_by(user_description) %>%
      summarize(total_count = sum(count)) %>%
      arrange(desc(total_count)) %>%
      slice_head(n = 3) %>%  # Top 3 users
      pull(user_description)

    label_data <- plot_data %>%
      filter(user_description %in% top_n_users) %>%
      group_by(user_description) %>%
      slice_max(count, with_ties = FALSE)
      # mutate(label = ifelse(user_description %in% top_n_users, user_description, NA))

    p <- ggplot(plot_data, aes(x = bin_time, y = count, color = user_description)) +
      geom_line() +
      geom_label(data = label_data,
                aes(label = user_description),
                vjust = -0.5) +
      labs(x = "Time", y = "Event Count") +
      theme_minimal() +
      guides(color = "none")
    ggplotly(p)
  })

  output$action_timeline <- renderPlotly({
    audit_data <- user_and_action_filtered_audits()

    binwidth <- 3600

    bins <- seq(from = min(audit_data$time),
                    to = max(audit_data$time) + 3600,
                    by = binwidth)

    # Per user time plot
    plot_data <- audit_data %>%
      mutate(bin_time = cut(time, breaks = bins)) %>%
      group_by(bin_time, action) %>%
      summarize(count = n(), .groups = "drop") %>%
      mutate(bin_time = as.POSIXct(bin_time, format = "%Y-%m-%d %H:%M:%S")) %>%
      tidyr::complete(bin_time = bins, action, fill = list(count = 0))

    # Identify top n users
    top_n_users <- plot_data %>%
      group_by(action) %>%
      summarize(total_count = sum(count)) %>%
      arrange(desc(total_count)) %>%
      slice_head(n = 3) %>%  # Top 3 users
      pull(action)

    label_data <- plot_data %>%
      filter(action %in% top_n_users) %>%
      group_by(action) %>%
      slice_max(count, with_ties = FALSE)
      # mutate(label = ifelse(action %in% top_n_users, action, NA))

    p <- ggplot(plot_data, aes(x = bin_time, y = count, color = action)) +
      geom_line() +
      geom_label(data = label_data,
                aes(label = action),
                vjust = -0.5) +
      labs(x = "Time", y = "Event Count") +
      theme_minimal() +
      guides(color = "none")
    ggplotly(p)
  })

  # Audit list
  output$audit_list <- reactable::renderReactable({
    user_and_action_filtered_audits() %>%
      select(time, user_description, action, event_description) %>%
      arrange(desc(time)) %>%
      mutate(time = format(time, "%Y-%m-%dT%H:%M:%S%z")) %>%
      reactable::reactable(pageSizeOptions = 100)
  })
}

shinyApp(ui, server)
