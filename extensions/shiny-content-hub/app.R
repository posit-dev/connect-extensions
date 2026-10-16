library(shiny)
library(bslib)
library(connectapi)

# Shiny sources the files in R/ automatically: card_grid(), hub_items(), and
# filter_items() come from R/content_hub.R, and the tag helpers, such as
# tab_sections(), from R/portal.R.

# Building and sending a card per item gets slow past a few dozen, so each
# section shows at most this many, the most recently updated.
max_cards <- 30

ui <- page_navbar(
  title = "Content Hub",
  id = "tabs",
  # The same Bootswatch theme as the Quarto: Content Hub extension, with the
  # header in the theme's primary color rather than Flatly's default grey.
  theme = bs_theme(version = 5, preset = "flatly", "navbar-bg" = "#2c3e50"),
  # The page scrolls as one long list instead of fitting the window.
  fillable = FALSE,
  header = tagList(
    tags$head(tags$link(rel = "stylesheet", href = "styles.css")),
    div(
      class = "pt-4",
      # Replace this introduction with a note for your own audience: who the
      # hub is for, and where to go for help.
      p(class = "lead", "Browse the reports, apps, and APIs on Posit Connect that you have access to."),
      uiOutput("status")
    )
  )
  # The server adds a tab for each tag once it has the tag list.
)

# One tab: a search box above the tab's content, grouped into sections.
tab_ui <- function(id) {
  ns <- NS(id)
  tagList(
    div(
      class = "hub-search",
      textInput(ns("search"), NULL, placeholder = "Search by title, description, owner, type, or tag", width = "100%")
    ),
    uiOutput(ns("content"))
  )
}

tab_server <- function(id, client, all_tags, tab) {
  moduleServer(id, function(input, output, session) {
    # Shiny doesn't render outputs in hidden tabs, so this fetch runs the
    # first time the viewer opens the tab, and is kept for the rest of the
    # session. A tab the viewer never opens costs nothing.
    #
    # The search matches every tag with this tab's name, plus the tags below
    # them. Tag names needn't be unique, so keep only the content under this
    # tab's own tag.
    items <- reactive({
      tryCatch(
        {
          content <- as.data.frame(search_content(client, q = tag_query(tab$name), include = "owner,tags"))
          items <- hub_items(content)
          items[has_any_tag(items, c(tab$id, descendant_ids(all_tags, tab$id))), , drop = FALSE]
        },
        error = function(e) {
          structure(list(message = conditionMessage(e)), class = "hub_error")
        }
      )
    })

    # Re-filter only once the viewer pauses typing, not on every keystroke.
    search <- debounce(reactive(input$search), 250)

    output$content <- renderUI({
      items <- items()
      if (inherits(items, "hub_error")) {
        return(div(class = "alert alert-warning", "Couldn't load this tab's content: ", items$message))
      }
      if (nrow(items) == 0) {
        return(p(class = "text-muted", "There's no content here that you have access to."))
      }
      matches <- filter_items(items, search())
      if (nrow(matches) == 0) {
        return(p(class = "text-muted", "No content matches your search."))
      }
      lapply(tab_sections(matches, all_tags, tab$id), function(section) {
        tags$section(
          class = "hub-section",
          if (!is.null(section$heading)) h2(section$heading),
          card_grid(utils::head(section$items, max_cards)),
          if (nrow(section$items) > max_cards) {
            p(
              class = "text-muted",
              sprintf(
                "Showing the %d most recently updated of %d items. Search to narrow the list.",
                max_cards,
                nrow(section$items)
              )
            )
          }
        )
      })
    })
  })
}

server <- function(input, output, session) {
  # Connect to Connect as the viewer, and fetch the tag list.
  #
  # Connect passes each viewer's session token in a request header. With a
  # Connect API integration associated with this app, connect() exchanges the
  # token for a short-lived API key carrying that viewer's permissions, so
  # every content search returns only content this viewer may access. That is
  # what makes the hub personal; no shared publisher key is involved.
  #
  # This runs inside a reactive rather than directly in the server function,
  # so the page appears right away and shows Shiny's busy indicator while it
  # loads, instead of a blank page.
  token <- session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
  hub <- reactive({
    if (is.null(token) && identical(Sys.getenv("RSTUDIO_PRODUCT"), "CONNECT")) {
      # On Connect, the header is missing only when nobody is logged in.
      return(list(error = "anonymous"))
    }
    connected <- tryCatch(
      {
        client <- connect(token = token)
        list(client = client, tags = tag_table(client$tag()))
      },
      error = function(e) list(error = "integration", message = conditionMessage(e))
    )
    if (!is.null(connected$error)) {
      return(connected)
    }

    # The tabs are the tags directly under HUB_TAG, or the top-level tags if
    # it isn't set.
    tags <- connected$tags
    hub_tag <- trimws(Sys.getenv("HUB_TAG"))
    parent_id <- NA
    if (nzchar(hub_tag)) {
      parent_id <- find_tag(tags, hub_tag)
      if (is.na(parent_id)) {
        return(list(error = "hub_tag", hub_tag = hub_tag))
      }
    }
    c(connected, list(tabs = child_tags(tags, parent_id)))
  })

  observeEvent(hub(), once = TRUE, {
    tabs <- hub()$tabs
    req(tabs)
    # lapply() rather than a for loop, so that each tab's server keeps its
    # own `tab` instead of all of them seeing the loop's last one.
    lapply(seq_len(nrow(tabs)), function(i) {
      tab <- tabs[i, , drop = FALSE]
      id <- paste0("tab_", tab$id)
      nav_insert("tabs", nav_panel(tab$name, value = id, tab_ui(id)), select = i == 1)
      tab_server(id, hub()$client, hub()$tags, tab)
    })
  })

  output$status <- renderUI({
    hub <- hub()
    if (identical(hub$error, "anonymous")) {
      div(class = "alert alert-info", "Log in to Posit Connect to see the content available to you.")
    } else if (identical(hub$error, "integration")) {
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
        p(class = "small mb-0", "Details: ", hub$message)
      )
    } else if (identical(hub$error, "hub_tag")) {
      div(
        class = "alert alert-warning",
        sprintf(
          "There's no tag named \"%s\" on this server. Check the HUB_TAG environment variable in the hub's settings.",
          hub$hub_tag
        )
      )
    } else if (nrow(hub$tabs) == 0) {
      div(
        class = "alert alert-info",
        if (nzchar(Sys.getenv("HUB_TAG"))) {
          sprintf("The \"%s\" tag has no tags under it to show as tabs.", Sys.getenv("HUB_TAG"))
        } else {
          "This server has no tags yet. Ask a Connect administrator to create some, and tag your content with them."
        }
      )
    }
  })
}

shinyApp(ui, server)
