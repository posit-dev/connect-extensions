library(shiny)
library(bslib)
library(bsicons)
library(connectapi)
library(dplyr)
library(shinyjs)

ui <- page_sidebar(
  useShinyjs(),
  title = "Swap Vanity URLs",
  sidebar = sidebar(
    div("Select two content items to swap their vanity URLs."),
    checkboxInput("only_vanities", "Show only content with vanity URLs", value = FALSE)
  ),

  card(
    card_header(
      div(
        class = "d-flex justify-content-between align-items-center",
        span("Content Items"),
        actionButton("swapButton", "Swap Vanity URLs", class = "btn-primary")
      )
    ),
    div(
      style = "padding: 15px;",
      uiOutput("content_list")
    )
  )
)

server <- function(input, output, session) {
  data_version <- reactiveVal(0)

  # Connect client as a reactive value
  reactive_client <- reactive(suppressMessages(connect()))

  # Reactive to get content data
  content_data <- reactive({
    data_version()

    client <- reactive_client()

    # FIXDME: Filter for a single user's content, hard-coded
    content <- get_content(client, owner_guid = Sys.getenv("OWNER_GUID"))
    vanities <- get_vanity_urls(client)

    if (input$only_vanities) {
      joined_content <- inner_join(content, vanities, join_by("guid" == "content_guid"))
    } else {
      joined_content <- left_join(content, vanities, join_by("guid" == "content_guid"))
    }
    select(joined_content, guid, title, path, dashboard_url)
  })

  # Reactive to track the number of selected items
  selected_count <- reactive({
    sum(unlist(reactiveValuesToList(input)[grep("^select_", names(input))]))
  })

  # Update button state based on count
  observe({
    toggleState("swapButton", selected_count() == 2)
  })

  # Generate the list UI
  output$content_list <- renderUI({
    data <- content_data()

    client <- reactive_client()

    items <- lapply(seq_len(nrow(data)), function(i) {
      div(
        class = "d-flex border-bottom py-3",
        # Checkbox column
        div(
          class = "me-3",
          checkboxInput(paste0("select_", data$guid[i]), "", width = "auto")
        ),
        # Content column
        div(
          class = "flex-grow-1 d-flex flex-column", # Flex column layout
          style = "min-width: 0;",
          # Title row
          div(
            h5(data$title[i], class = "mb-1")
          ),
          # URLs
          div(
            class = "d-flex flex-column gap-1",
            # Vanity Path Row
            div(
              class = "small text-truncate",
              tags$span("Vanity Path: "),
              if (is.na(data$path[i])) {
                "None"
              } else {
                a(data$path[i], href = (client$server_url(data$path[i])), target = "_blank",
                  class = "text-decoration-none")
              }
            ),
            # Open Dashboard Row
            div(
              class = "small",
              a(
                div("Open Dashboard ", bs_icon("arrow-up-right-square")),
                href = data$dashboard_url[i],
                target = "_blank", class = "text-decoration-none"
              )
            )
          )
        )
      )
    })

    div(class = "list-group", items)
  })

  # When the button is pressed, swap the vanity URLs.
  observeEvent(input$swapButton, {
    input_list <- reactiveValuesToList(input)
    checkboxes <- input_list[grep("^select_", names(input_list))]
    selected <- names(checkboxes[checkboxes == TRUE])
    selected_guids <- sub("^select_", "", selected)

    client <- reactive_client()

    item_1 <- content_item(client, selected_guids[1])
    item_2 <- content_item(client, selected_guids[2])

    swap_vanity_url(item_1, item_2)

    data_version(data_version() + 1)
  })
}

shinyApp(ui, server)
