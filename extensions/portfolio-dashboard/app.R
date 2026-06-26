library(dplyr)
library(ggplot2)
library(plotly)
library(PerformanceAnalytics)
library(shiny)
library(shinydashboard)
library(xts)
library(zoo)

# Sample monthly returns for three risk profiles. Swap in your own returns.csv
# (columns: date, portfolio, returns) to use this dashboard with real data.
returns_data <- read.csv("returns.csv")
returns_data$date <- as.Date(returns_data$date)

# Build the selector from whatever portfolios are in the data, so swapping in
# your own returns.csv populates it automatically.
portfolio_choices <- unique(returns_data$portfolio)
names(portfolio_choices) <- tools::toTitleCase(portfolio_choices)

ui <- dashboardPage(
  dashboardHeader(title = "Portfolio Dashboard"),
  dashboardSidebar(
    selectInput(
      "portfolio",
      "Choose a portfolio",
      choices = portfolio_choices,
      selected = "balanced"
    ),
    dateInput(
      inputId = "date",
      label = "Starting Date",
      value = min(returns_data$date),
      min = min(returns_data$date),
      max = max(returns_data$date),
      format = "yyyy-mm-dd"
    ),
    sliderInput("mar", "Min Acceptable Rate", min = 0, max = 0.1, value = 0.008, step = 0.001),
    numericInput("window", "Rolling Window", min = 6, max = 36, value = 12)
  ),
  dashboardBody(
    fluidRow(
      box(title = "Rolling Sortino", width = 12,
        plotlyOutput("time_series")
      )
    ),
    fluidRow(
      box(title = "Scatterplot", width = 4,
        plotlyOutput("scatterplot", height = 250)
      ),
      box(title = "Histogram", width = 4,
        plotlyOutput("histogram", height = 250)
      ),
      box(title = "Density", width = 4,
        plotlyOutput("density", height = 250)
      )
    )
  )
)

server <- function(input, output, session) {

  # The Minimum Acceptable Rate (MAR) is the return threshold below which a month
  # counts as "downside." The Sortino ratio measures return per unit of downside
  # (below-MAR) volatility, so unlike the Sharpe ratio it doesn't penalize upside
  # swings. All four plots below react to the chosen portfolio, start date, MAR,
  # and rolling-window length.

  rate_limit_sec <- 2

  # Throttle so dragging the MAR slider or window doesn't recompute on every
  # tick; recompute at most once per rate_limit_sec.
  portfolio_selected <- throttle(reactive({
    req(input$portfolio, input$date)

    returns_data |>
      filter(portfolio == input$portfolio, date >= input$date)

  }), rate_limit_sec * 1000)

  rolling_sortino <- reactive({
    req(input$mar)
    req(input$window)

    # Need at least `window` months of data to compute a rolling value; show a
    # message instead of a blank plot when the start date leaves too few.
    validate(need(
      nrow(portfolio_selected()) >= input$window,
      "Not enough data for this rolling window. Choose an earlier start date or a smaller window."
    ))

    portfolio_selected()$returns |>
      xts::xts(order.by = portfolio_selected()$date) |>
      rollapply(input$window, function(x) SortinoRatio(x, MAR = input$mar)) |>
      `colnames<-`(paste0(input$window, "-month rolling"))
  })

  returns_flagged <- reactive({
    portfolio_selected() |>
      # Flag each month as up/down vs the MAR, so the plots below can color and
      # shade the downside months.
      mutate(status = ifelse(returns < input$mar, "down", "up"))
  })

  output$time_series <- renderPlotly({
    plot_ly() |>
      add_lines(x = index(rolling_sortino()), y = as.numeric(rolling_sortino())) |>
      layout(
        hovermode = "x",
        xaxis = list(
          rangeslider = list(visible = TRUE),
          rangeselector = list(
            x = 0, y = 1, xanchor = 'left', yanchor = "top", font = list(size = 9),
            buttons = list(
              list(count = 1, label = 'RESET', step = 'all'),
              list(count = 1, label = '1 YR', step = 'year', stepmode = 'backward'),
              list(count = 3, label = '3 MO', step = 'month', stepmode = 'backward'),
              list(count = 1, label = '1 MO', step = 'month', stepmode = 'backward')
            )
          )
        )
      )
  })

  output$scatterplot <- renderPlotly({
    portfolio_scatter <- ggplot(returns_flagged(), aes(x = date, y = returns, color = status)) +
      geom_point() +
      geom_hline(yintercept = input$mar, color = "purple", linetype = "dotted") +
      scale_color_manual(values = c(down = "tomato", up = "chartreuse3")) +
      theme(legend.position = "none") + ylab("monthly returns")

    ggplotly(portfolio_scatter)
  })

  output$histogram <- renderPlotly({
    p <- ggplot(returns_flagged(), aes(x = returns)) +
      geom_histogram(alpha = 0.25, binwidth = .01, fill = "cornflowerblue") +
      geom_vline(xintercept = input$mar, color = "green")
    ggplotly(p) |>
      add_annotations(text = "MAR", x = input$mar, y = 10, xshift = 10, showarrow = FALSE, textangle = -90)
  })

  output$density <- renderPlotly({
    sortino_density_plot <- ggplot(returns_flagged(), aes(x = returns)) +
      stat_density(geom = "line", linewidth = 1, color = "cornflowerblue")

    shaded_area_data <- ggplot_build(sortino_density_plot)$data[[1]] |>
      filter(x < input$mar)

    sortino_density_plot <-
      sortino_density_plot +
      geom_area(data = shaded_area_data, aes(x = x, y = y), fill = "pink", alpha = 0.5) +
      geom_segment(
        data = shaded_area_data, aes(x = input$mar, y = 0, xend = input$mar, yend = y),
        color = "red", linetype = "dotted"
      )

    ggplotly(sortino_density_plot) |>
      add_annotations(
        x = input$mar, y = 5, text = paste("MAR =", input$mar, sep = ""), textangle = -90
      ) |>
      add_annotations(
        x = (input$mar - .02), y = .1, text = "Downside",
        xshift = -20, yshift = 10, showarrow = FALSE
      )
  })
}

shinyApp(ui = ui, server = server)
