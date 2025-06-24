library(shiny)
library(shinychat) 
library(ellmer)
library(palmerpenguins)
library(connectapi)
library(ggplot2)
library(bslib)

data(penguins)

ui <- bslib::page_fluid(
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

shiny::shinyApp(ui, server)