library(shiny)
library(shinythemes)
library(ellmer)
library(mall)
library(connectcreds)
library(connectapi)

# Simple setup UI
setup_ui <- shiny::fluidPage(
  shiny::tags$head(
    shiny::tags$style(
      "body { padding: 30px; }
       .setup-box { max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; }
       .setup-title { margin-bottom: 20px; color: #2c3e50; }
       .setup-section { margin-top: 25px; }
       .setup-code { background: #f1f1f1; padding: 15px; border-radius: 5px; font-family: monospace; }"
    )
  ),
  
  shiny::div(
    class = "setup-box",
    
    # Title
    shiny::tags$h2("Setup Required", class = "setup-title"),
    
    # Vertex AI Integration section
    shiny::div(
      class = "setup-section",
      shiny::tags$h3("Vertex AI OAuth Integration"),
      shiny::p(
        shiny::HTML(
          "This application uses a <strong>Google Vertex AI OAuth</strong> ",
          "integration to authenticate with Google Cloud Platform. ",
          "For more information, visit the Vertex AI",
          "<a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/google' ",
          "target='_blank'>admin guide</a>."
        )
      )
    ),
    
    # Environment Variables section
    shiny::div(
      class = "setup-section",
      shiny::tags$h3("Environment Variables Required"),
      shiny::p(
        shiny::HTML(
          "This application requires the following environment variables to be properly configured: ",
          "<code>LOCATION</code>, <code>PROJECT_ID</code>, and <code>MODEL</code>."
        )
      ),
      
      shiny::p("For example:"),
      shiny::pre(
        class = "setup-code",
        "LOCATION = \"us-central1\"
PROJECT_ID = \"your-gcp-project-123\"
MODEL = \"gemini-2.5-flash\""
      )
    )
  )
)

app_ui <- shiny::fluidPage(
  theme = shinytheme("flatly"),
  
  shiny::tags$head(
    shiny::tags$style(
      "body { padding-top: 30px; }
      #text_input { height: 130px; resize: none; }
      .translation-area { min-height: 130px; border: 1px solid #ddd; border-radius: 4px; padding: 10px; background-color: #f9f9f9; }
      .translate-btn-container { text-align: center; margin: 15px 0; }
      .container-narrow { max-width: 800px; margin-left: auto; margin-right: auto; margin-top: 80px; }
      .header-flex { display: flex; justify-content: space-between; align-items: center; }
      .header-flex .shiny-input-container { margin-bottom: 0; }"
    )
  ),
  
  # wrapper div to constrain width
  shiny::div(
    class = "container-narrow",
    
  shiny::fluidRow(
    shiny::column(
      width = 12,
      shiny::wellPanel(
        shiny::p("English:"),
        shiny::textAreaInput(
          "text_input",
          label = NULL,
          placeholder = "Type or paste text here for translation...",
          width = "100%"
        )
      )
    )
  ),
  
  shiny::fluidRow(
    shiny::column(
      width = 12,
      shiny::div(
        class = "translate-btn-container",
        shiny::actionButton(
          "analyze_btn", 
          "Translate", 
          class = "btn-primary"
        )
      )
    )
  ),
  
  shiny::fluidRow(
    shiny::column(
      width = 12,
      shiny::wellPanel(
        # Language selector
        shiny::selectInput(
          "target_language",
          NULL,
          choices = c(
            "Spanish" = "spanish",
            "French" = "french",
            "Italian" = "italian",
            "German" = "german"
          ),
          width = "150px"
        ),
        shiny::div(
          class = "translation-area",
          shiny::uiOutput("results_container")
        )
      )
    )
  )
  )
)

screen_ui <- shiny::uiOutput("screen")

server <- function(input, output, session) {

  OAUTH_INTEGRATION_ENABLED <- TRUE
  user_session_token <- session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN

  if (!is.null(user_session_token)) {
    # Capture any messages that might contain the error code
    msg <- capture.output(
      try(connectapi::connect(token = user_session_token)),
      type = "message"
    )

    if (any(grepl("212", msg))) {
      OAUTH_INTEGRATION_ENABLED <- FALSE
    }
  }

  LOCATION <- Sys.getenv("LOCATION")
  PROJECT_ID <- Sys.getenv("PROJECT_ID")
  MODEL <- Sys.getenv("MODEL")

  output$screen <- shiny::renderUI({
    # Show the app UI if OAuth is enabled and all env vars are set
    if (OAUTH_INTEGRATION_ENABLED & !any(LOCATION == "", PROJECT_ID == "", MODEL == "")) {
      app_ui
    } else {
      setup_ui
    }
  })

  
  shiny::observeEvent(input$analyze_btn, {
    text <- input$text_input
    
    if (nchar(text) > 0) {
      # Using ellmer and mall for sentiment analysis
      chat <- ellmer::chat_google_vertex(
        location = LOCATION,
        project_id = PROJECT_ID,
        model = MODEL,
        system_prompt = "you are a translator and will do nothing else other than translate."
      )

      mall::llm_use(chat)

      text_df <- data.frame(text = text)
      selected_language <- input$target_language
      
      # translate text to selected language using mall
      translated_text <- text_df |>
        mall::llm_translate(text, language = selected_language)

      translated_text <- translated_text$.translation[1]

    } else {
      translated_text <- ""
    }

    output$results_container <- shiny::renderUI({
        shiny::p(
          translated_text,
          style = "font-size: 16px;"
        )
      })

  })
}

shiny::shinyApp(ui = screen_ui, server = server)
