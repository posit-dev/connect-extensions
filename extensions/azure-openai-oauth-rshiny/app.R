library(shiny)
library(shinychat) 
library(ellmer)
library(palmerpenguins)
library(connectapi)
library(ggplot2)
library(bslib)

data(penguins)

setup_ui <- bslib::page_fluid(
      theme = bslib::bs_theme(bootswatch = "flatly"),
      bslib::layout_columns(
        col_widths = c(2, 8, 2),
        NULL,
        bslib::card(
          bslib::card_header("Azure OpenAI OAuth Setup Instructions"),
          bslib::card_body(
            tags$h4("Configuration Required"),
            tags$p("This application requires Azure OpenAI OAuth integration to be properly configured."),
            tags$p("For more detailed instructions, please refer to the ",
                   tags$a(href="https://docs.posit.co/connect/admin/integration-azure-openai/",
                          "Posit Connect Azure OpenAI integration documentation",
                          target="_blank"))
          ),
          width = "100%",
          class = "shadow"
        ),
        NULL
      )
    )

app_ui <- bslib::page_fluid(
    theme = bslib::bs_theme(bootswatch = "flatly"),
    bslib::layout_columns(
      col_widths = c(2, 8, 2),
      NULL,  
      bslib::card(
        bslib::card_header("Palmer Penguins Chat Assistant"),
        shinychat::chat_ui("chat", height = "300px"),
        width = "100%",
        class = "shadow"
      ),
      NULL   
    )
  )

screen_ui <- uiOutput("screen")


server <- function(input, output, session) {

  # Get Connect OAuth credentials using connectapi
  get_oauth_credentials <- function() {

    if (Sys.getenv("POSIT_PRODUCT") == "CONNECT") {

      client <- connectapi::connect()
      
      user_session_token <- session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
      oauth_response <- connectapi::get_oauth_credentials(client, user_session_token)
      credentials <- list(Authorization = paste("Bearer", oauth_response$access_token))
         
    } else {

      # Local development mode
      api_key <- Sys.getenv("AZURE_OPENAI_API_KEY")
      if (api_key != "") {
        credentials <- list("api-key" = api_key)
      } else {
        credentials <- NULL 
      }

    }

    credentials

  }

  OAUTH_INTEGRATION_ENABLED <- TRUE

  # Capture any messages that might contain the error code
  msg <- capture.output(
    try(connectapi::connect(token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN)),
    type = "message"
  )
  
  if (any(grepl("212", msg))) {
    OAUTH_INTEGRATION_ENABLED <- FALSE
  }

  output$screen <- shiny::renderUI({
    if (OAUTH_INTEGRATION_ENABLED) {
      app_ui
    } else {
      setup_ui
    }
  })

  # Create Azure OpenAI chat function
  penguin_chat <- function() {
  
    credentials <- get_oauth_credentials()

    # Create a custom chat function for Azure OpenAI
    azure_chat <- ellmer::chat_azure_openai(
      deployment_id = "gpt-4o-mini",
      api_version =  "2024-12-01-preview", 
      endpoint = "https://8ul4l3wq0g.openai.azure.com",
      credentials = credentials,
      system_prompt = paste0(
        "You are a data assistant helping with the Palmer Penguins dataset. ",
        "The dataset contains measurements for Adelie, Chinstrap, and Gentoo penguins observed on islands in the Palmer Archipelago. ",
        "Answer questions about the dataset concisely and accurately. ",
        "The dataset structure is: \n", paste(capture.output(str(penguins)), collapse = "\n")
      )
    )
  }

  shiny::observeEvent(input$chat_user_input, {

    current_chat <- penguin_chat()

    stream <- current_chat$stream_async(input$chat_user_input)
    shinychat::chat_append("chat", stream)


  })

}

shiny::shinyApp(screen_ui, server)