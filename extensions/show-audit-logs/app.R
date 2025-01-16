library(shiny)
library(bslib)
library(dplyr)
library(ggplot2)
library(lubridate)
library(connectapi)

# UI definition
ui <- page_fluid(
  theme = bs_theme(version = 5),

  # Title bar
  card(
    full_screen = TRUE,
    card_header("Posit Connect Audit Logs"),

    layout_sidebar(
      # Sidebar with filter controls
      sidebar = sidebar(
        title = "Filters",

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
        ),

        numericInput(
          "limit",
          "Number of Records",
          value = 5000,
          min = 1,
          max = 50000
        ),

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
                    plotOutput("event_plot")
                  )
                ),
                card(
                  height = "100%",  # Make card fill space
                  card_header("Activity Timeline"),
                  card_body(
                    plotOutput("timeline_plot")
                  )
                )
              )
            ),
            tabPanel(
              "Activity By User",
              plotOutput("user_timeline")
            ),
            tabPanel(
              "Activity By Event Type",
              plotOutput("action_timeline")
            ),
            tabPanel(
              "Event List",
              card(
                card_header("Event List"),
                div(
                  style = "height: 500px; overflow-y: auto;",
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
    req(input$limit)


    withProgress(
      {
        client <- connect()
        logs <- get_audit_logs(client, limit = input$limit, asc_order = FALSE)
      },
      message = "Loading audit logs...",
      value = NULL
    )
  })

  # Handle action filters updates
  observe({
    data <- audit_data()
    actions <- data %>%
      count(action) %>%
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
    data <- audit_data()
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
  filtered_data <- reactive({
    data <- audit_data()

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
  output$event_plot <- renderPlot({

    data <- filtered_data()

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


      p

    }, error = function(e) {

      NULL
    })
  })

  # Timeline plot
  output$timeline_plot <- renderPlot({

    audit_data <- filtered_data()

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

    ggplot(plot_data, aes(x = bin_time, y = count)) +
      geom_line() +
      labs(x = "Time", y = "Event Count") +
      theme_minimal() +
      guides(color = "none")

  })

  output$user_timeline <- renderPlot({
    audit_data <- filtered_data()

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

    ggplot(plot_data, aes(x = bin_time, y = count, color = user_description)) +
      geom_line() +
      geom_label(data = label_data,
                aes(label = user_description),
                vjust = -0.5) +
      labs(x = "Time", y = "Event Count") +
      theme_minimal() +
      guides(color = "none")
  })

  output$action_timeline <- renderPlot({
    audit_data <- filtered_data()

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

    ggplot(plot_data, aes(x = bin_time, y = count, color = action)) +
      geom_line() +
      geom_label(data = label_data,
                aes(label = action),
                vjust = -0.5) +
      labs(x = "Time", y = "Event Count") +
      theme_minimal() +
      guides(color = "none")
  })

  # Audit list
  output$audit_list <- reactable::renderReactable({
    filtered_data() %>%
      select(time, user_description, action, event_description) %>%
      arrange(desc(time)) %>%
      mutate(time = format(time, "%Y-%m-%dT%H:%M:%S%z")) %>%
      reactable::reactable(pageSizeOptions = 100)
  })
}

shinyApp(ui, server)
