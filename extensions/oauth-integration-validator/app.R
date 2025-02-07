library(shiny)
library(httr2)
library(bslib)
library(connectapi)

ui <- page_sidebar(
  title = "OAuth Integration Validation in R",
  sidebar = sidebar(
    title = "Request an endpoint",
    textInput("endpoint", "GET endpoint to request:", placeholder = "https://example.com/api/list"),
    actionButton("request", "Request")
  ),
  layout_columns(
    card(
      card_header("Results"),
      htmlOutput("results")
    )
  )
)

server <- function(input, output, session) {
  
  # check if running on Posit Connect
  if (Sys.getenv("RSTUDIO_PRODUCT") == "CONNECT") {
    # initialize Connect API client
    client <- connect()
    
    # read the user-session-token header
    user_session_token <- session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
    
    # wrap client credentials exchange request for error handling
    # and so the app does not fail to start on first deploy
    credentials <- reactive({
      tryCatch({
        # exchange user session token for an access token using connectapi client
        # checking for a client error in
        credentials <- get_oauth_credentials(client, user_session_token)
      }, error = function(e) {
          return(list(error = "Unable to obtain access token: ", message = e$message))
        })
      })
   
    # set token to null
    token <- reactiveVal(NULL)
    
    # react to the credentials request
    observeEvent(credentials(), {
      creds <- credentials()
      
      # check if the credentials exchange was successful
      if (is.null(creds$error)) {
        token(creds$access_token)
      } else {
        # show notification to user
        showNotification(creds$error, creds$message)
      }
    }) 
  } else {
    # grab the access token from the OAUTH_TOKEN environment variable if running
    # locally
    token <- Sys.getenv("OAUTH_TOKEN")
  }
  
  # react to request button being pressed 
  observeEvent(input$request, {
    # do not allow empty value for endpoint
    req(input$endpoint)
    endpoint <- input$endpoint
    
    # do not allow request without an access token
    if (is.null(token())) {
      # remind the user that they don't have a token 
      output$results <- renderUI({
        HTML('<span style="color:red; font-size:larger;">No access token found.',
        '<br/>Try logging out and logging back in to the integration if you haven not ',
        'visited this content recently.<br/>If an integration is not associated with ',
        'the content then ask your publisher to add one.</span><br/>')
      })
    } else {
      # make the request 
      resp <- httr2::request(endpoint) |>
        httr2::req_headers("Accept" = "application/json") |>
        httr2::req_auth_bearer_token(token()) |>
        # to avoid HTTP response error codes being surfaced as R errors
        httr2::req_error(is_error = ~FALSE) |>
        httr2::req_perform()
    
      # check the HTTP response code
      http_code <- httr2::resp_status(resp)
      if (http_code == 200) {
        # format response body now that we have the HTTP status code
        resp <- httr2::resp_body_json(resp)
      
        # save the results
        results <- paste0("Endpoint ", input$endpoint, " returned: ", resp)
      
        # display success message and expandable results section 
        output$results <- renderUI({
          HTML('<span style="color:green; font-size:larger;">Success!</span><br/>', 
            '<details><summary>Show results</summary><p>',
            results,
            '</p></details>'
          )
        })
      }
      
      # output the unexpected HTTP code
      if (http_code != 200) {
        output$results <- renderUI({
          # only display the HTTP error code to the user
          error <- paste0("Received non-200 HTTP response code: ", http_code)
          HTML('<span style="color:red; front-size:larger;">', error, '</span>')
        })
        # log the results for debugging
        print(httr2::resp_body_json(resp))
      }
    }
  })
}

shinyApp(ui, server)

