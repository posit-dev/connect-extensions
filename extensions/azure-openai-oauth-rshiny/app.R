library(shiny)
library(shinychat) 
library(ellmer)
library(palmerpenguins)
library(connectapi)
library(bslib)
library(shinyjs)
library(dplyr)

source("integrations.R")
source("styles.R")

data(penguins)

setup_ui <- function(selected_integration = NULL, integration_button = NULL, enabled = FALSE) {
  bslib::page_fillable(
      app_styles,
      setup_container(
          tags$h1("Setup", class = "setup-title"),
          if (!is.null(selected_integration) && nrow(selected_integration) > 0) {
            # azure openai integration available 
            tags$div(
              class = ifelse(!enabled, "setup-integration-section", "setup-integration-section setup-success"),
              tags$h2("Azure OpenAI Integration", class = "setup-section-title"),
              
              if (!enabled) { 
                # azure openai ntegration available but not enabled yet
                tags$div(
                  class = "setup-description",
                  HTML(paste0(
                    "This content uses an <strong>Azure OpenAI OAuth</strong> ",
                    "integration to authenticate with Azure OpenAI services. ",
                    "A compatible integration is available; use it below.",
                    "<br><br>",
                    "For more information, see ",
                    "<a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/azure-openai/' ",
                    "target='_blank' class='setup-link'>documentation on Azure OpenAI OAuth integrations</a>."
                  ))
                )
                
              } else {
                # azure openai ntegration available and is already enabled
                tags$div(
                  class = "setup-description",
                  HTML(paste0(
                    "<strong>✓ Integration Added</strong>: The Azure OpenAI OAuth integration '",
                    selected_integration$name,
                    "' has been successfully added to this content.",
                    "<br><br>",
                    "You still need to set the environment variables below to complete the setup."
                  ))
                )
              },
              if(!is.null(integration_button)) {
                tags$div(
                  class = "setup-button-container",
                  integration_button
                )
              }
            )
          } else {
             # azure openai integration not available
            tags$div(
              class = "setup-description",
              HTML(paste0(
                "This content requires an <strong>Azure OpenAI OAuth</strong> integration, ",
                "but no compatible integration was found. ",
                "<br><br>",
                "Please see the ",
                "<a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/azure-openai/' ",
                "target='_blank' class='setup-link'>documentation </a> ",
                "on Azure OpenAI OAuth integrations to set one up."
              ))
            )
          },
          
          
          # Regular Setup Info to always show when setup_ui is surfaced
          tags$h2("Azure OpenAI API", class = "setup-section-title"),
          tags$div(
            class = "setup-description",
            HTML(
              "This application requires the following environment variables to be properly configured: <code>DEPLOYMENT_ID</code>, <code>API_VERSION</code>, and <code>ENDPOINT</code>. ",
              "Please set them in your environment before running the app. "
            )
          ),
          tags$h4("Example Environment Variables", class = "setup-section-title"),
          tags$pre(
            "DEPLOYMENT_ID = \"gpt-4o-mini\"
API_VERSION = \"2023-05-15\"
ENDPOINT = \"https://your-resource-name.openai.azure.com\"",
            class = "setup-code-block"
          )
        ),
        fillable = TRUE
      )
}

app_ui <- bslib::page_fillable(
    app_styles,
    setup_container(
        tags$h1("Palmer Penguins Chat Assistant", class = "setup-title"),
        tags$div(
          class = "setup-description",
          HTML(
            "Ask questions about the Palmer Penguins dataset, which contains measurements for Adelie, Chinstrap, and Gentoo penguins observed on islands in the Palmer Archipelago."
          )
        ),
        shinychat::chat_ui("chat", height = "400px")
      )
)

screen_ui <- shiny::uiOutput("screen")


server <- function(input, output, session) {

  cl <- connectapi::connect()

  selected_integration_guid <- shiny::reactiveVal(NULL)
  shiny::observeEvent(input$auto_add_integration, {
    auto_add_integration(cl, selected_integration_guid())
    shinyjs::runjs("window.top.location.reload(true);")
  })

  # Get available integrations
  selected_integration <- get_eligible_integrations(cl) |>
      dplyr::slice_head(n = 1)
  
  if (nrow(selected_integration) > 0) {
    selected_integration_guid(selected_integration$guid)
  }
    

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

  DEPLOYMENT_ID <- Sys.getenv("DEPLOYMENT_ID")
  API_VERSION <- Sys.getenv("API_VERSION")
  ENDPOINT <- Sys.getenv("ENDPOINT")
  

  output$screen <- shiny::renderUI({
    # Show the app UI if OAuth is enabled and all env vars are set
    if (OAUTH_INTEGRATION_ENABLED & !any(DEPLOYMENT_ID == "", API_VERSION == "", ENDPOINT == "")) {
      app_ui
    } else {

      integration_button <- NULL
      
      if (!OAUTH_INTEGRATION_ENABLED && nrow(selected_integration) > 0) {
        button_label <- shiny::HTML(paste0(
          "Use the ",
          "<strong>'",
          selected_integration$name,
          "'</strong> ",
          "Integration"
        ))
        integration_button <- shiny::actionButton(
          "auto_add_integration",
          button_label,
          icon = icon("plus"),
          class = "btn btn-primary"
        )
      }
      
      setup_ui(selected_integration, integration_button, enabled = OAUTH_INTEGRATION_ENABLED)
    }
  })

  # Create Azure OpenAI chat function
  penguin_chat <- function() {
  
    credentials <- get_oauth_credentials()

    # Create a custom chat function for Azure OpenAI
    azure_chat <- ellmer::chat_azure_openai(
      deployment_id = DEPLOYMENT_ID,
      api_version =  API_VERSION, 
      endpoint = ENDPOINT,
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