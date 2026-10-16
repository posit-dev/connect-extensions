library(shiny)
library(bslib)
library(connectapi)
library(reactable)

# Shiny sources R/content_hub.R automatically: card_grid(), content_table(),
# hub_items(), and the other helpers come from there.

# Building and sending a card per item gets slow past a few dozen (seconds
# for a server with thousands of items), so the card view shows at most this
# many. The table view has no limit; it pages through rows in the browser.
max_cards <- 30

ui <- page_sidebar(
  title = "Content Hub",
  # The same Bootswatch theme as the Quarto: Content Hub extension, with the
  # header in the theme's primary color rather than Flatly's default grey.
  theme = bs_theme(version = 5, preset = "flatly", "navbar-bg" = "#2c3e50"),
  # The page scrolls as one long list instead of fitting the window.
  fillable = FALSE,
  tags$head(tags$link(rel = "stylesheet", href = "styles.css")),
  sidebar = sidebar(
    textInput("search", "Search", placeholder = "Title, description, owner, or tag"),
    selectizeInput(
      "types",
      "Type",
      choices = NULL,
      multiple = TRUE,
      options = list(placeholder = "All types", plugins = list("remove_button"))
    ),
    selectizeInput(
      "tags",
      "Tag",
      choices = NULL,
      multiple = TRUE,
      options = list(placeholder = "All tags", plugins = list("remove_button"))
    ),
    radioButtons("view", "View", c("Cards", "Table"))
  ),
  # Replace this introduction with a note for your own audience: who the hub
  # is for, and where to go for help.
  p(class = "lead mb-4", "Browse the reports, apps, and APIs on Posit Connect that you have access to."),
  uiOutput("status"),
  uiOutput("featured"),
  uiOutput("all_content")
)

server <- function(input, output, session) {
  # Fetch the content list once per session, as the viewer.
  #
  # Connect passes each viewer's session token in a request header. With a
  # Connect API integration associated with this app, connect() exchanges the
  # token for a short-lived API key carrying that viewer's permissions, so
  # get_content() returns exactly the content this viewer may access. That is
  # what makes the hub personal; no shared publisher key is involved.
  #
  # The fetch runs inside a reactive rather than directly in the server
  # function, so the page appears right away and the outputs show Shiny's busy
  # indicator while the list loads, instead of a blank page.
  token <- session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
  result <- reactive({
    if (is.null(token) && identical(Sys.getenv("RSTUDIO_PRODUCT"), "CONNECT")) {
      # On Connect, the header is missing only when nobody is logged in.
      list(error = "anonymous")
    } else {
      tryCatch(
        list(items = hub_items(get_content(connect(token = token)))),
        error = function(e) list(error = "integration", message = conditionMessage(e))
      )
    }
  })
  items <- reactive(result()$items)

  observeEvent(items(), once = TRUE, {
    updateSelectizeInput(session, "types", choices = sort(unique(items()$type)))
    updateSelectizeInput(session, "tags", choices = sort(unique(unlist(items()$tags))))
  })

  output$status <- renderUI({
    result <- result()
    items <- items()
    if (identical(result$error, "anonymous")) {
      div(class = "alert alert-info", "Log in to Posit Connect to see the content available to you.")
    } else if (identical(result$error, "integration")) {
      div(
        class = "alert alert-warning",
        p(
          paste(
            "This hub needs a Connect API integration to list the content available to you.",
            "The hub's publisher can add one on the Runtime tab of its settings",
            "(Access before Connect 2026.08.0). If no Connect API integration exists,",
            "a Connect administrator must create one first. See the "
          ),
          # .noWS keeps the link flush against the surrounding text, so no
          # stray space appears before the closing period.
          tags$a(
            href = "https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/",
            target = "_blank",
            .noWS = "outside",
            "Connect API integration guide"
          ),
          "."
        ),
        p(class = "small mb-0", "Details: ", result$message)
      )
    } else if (nrow(items) == 0) {
      div(class = "alert alert-info", "You don't have access to any content on this server yet.")
    }
  })

  # Featured content stays put while the viewer filters the list below it.
  output$featured <- renderUI({
    req(items(), nrow(items()) > 0)
    featured <- featured_items(items(), parse_tags(Sys.getenv("FEATURED_TAGS")))
    # A plain block wrapper carries the spacing: uiOutput()'s own container is
    # display: contents, which ignores margins.
    tags$section(class = "hub-section", h2(featured$heading), card_grid(featured$items))
  })

  # Re-filter only once the viewer pauses typing, not on every keystroke.
  search <- debounce(reactive(input$search), 250)

  matches <- reactive({
    req(items())
    filter_items(items(), search(), input$types, input$tags)
  })

  output$all_content <- renderUI({
    req(items(), nrow(items()) > 0)
    matches <- matches()
    tags$section(
      class = "hub-section",
      h2("All content"),
      if (nrow(matches) == 0) {
        p(class = "text-muted", "No content matches these filters.")
      } else if (input$view == "Table") {
        content_table(matches)
      } else {
        tagList(
          card_grid(utils::head(matches, max_cards)),
          if (nrow(matches) > max_cards) {
            p(
              class = "text-muted",
              sprintf(
                "Showing the %d most recently updated of %d items. Search or filter to narrow the list, or switch to the table to see them all.",
                max_cards,
                nrow(matches)
              )
            )
          }
        )
      }
    )
  })
}

shinyApp(ui, server)
