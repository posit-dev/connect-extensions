library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(dplyr)
library(purrr)

# cache data to disk with a refresh every 8h
shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

source("get_usage.R")

# Hacky function to get a list of Content class objects without making a request
# for each item. These objects differ from the ones created by `content_item()`
# because they also include the full owner info as returned by `get_content()`.
as_content_list <- function(content_df, client) {
  cdf_split <- split(content_df, 1:nrow(content_df))
  map(cdf_split, function(x) {
    x <- x[, !(names(x) %in% c("tags"))]
    x <- as.list(x)
    Content$new(client, x)
  })
}

# grab the username associated with a provided user_guid
get_user_info <- function(client, user_guid, connectServer) {
  if (is.na(user_guid)) {
    # NA user_guid populates when ACL is no login required / public access
    as.character("Anonymous")
  } else {
    user_endpoint <- paste0("v1/users/", user_guid)
    user <- client$GET(user_endpoint)
    user$username
  }
}

# checks to see if a content item has failed jobs, grabs usage data if it does,
# then compiles content, job, and usage data together, returning it.
get_failed_job_data <- function(item, usage, client, connectServer) {
  failed_jobs <- tryCatch(
    {
      get_jobs(item) |> 
        # filter successful jobs
        filter(exit_code != 0) |> 
        # map job types to something more readable 
        mutate(tag = case_when(
               tag == "run_app" ~ "Run R Application",
               tag == "packrat_restore" ~ "Packrat Cache Restore",
               tag == "build_report" ~ "Build Report",
               tag == "build_site" ~ "Build Site",
               tag == "build_jupyter" ~ "Build Jupyter Notebook",
               tag == "python_restore" ~ "Python Envrionment Restore",
               tag == "run_fastapi_app" ~ "Run Python FastAPI",
               tag == "run_gradio_app" ~ "Run Python Gradio",
               tag == "run_pyshiny_app" ~ "Run PyShiny Application",
               TRUE ~ tag)) |>
        # map exit codes to something more readable 
        mutate(exit_code = as.character(exit_code)) |>
        mutate(exit_code = case_when(
               exit_code == "1" ~ "Ended with errors",
               exit_code == "127" ~ "Command could not be executed outside container",
               exit_code == "137" ~ "Application terminated due to low memory",
               exit_code == "2" ~ "Command encountered an error during execution",
               exit_code == "134" ~ "Terminated due to critical error, potential segfault",
               TRUE ~ exit_code))
    },
    error = function(e) {
      # content item does not have any jobs 
      NULL
    }
  )
  
  if (is.null(failed_jobs) || nrow(failed_jobs) == 0) {
    return(NULL)
  } else {
    print(item)
    print(failed_jobs)
    # handle content without usage data, such as unpublished content
    last_visit <- usage %>%
      filter(content_guid == item$content$guid) %>%
      slice_max(timestamp) %>%
      select(user_guid, timestamp)
    # some content with issues do not have visit data (ex: unpublished)
    if (nrow(last_visit) == 0){
      visit_timestamp <- as.POSIXct(0) 
      visitor_username <- "No visit data exists for this content"
    } else {
      visit_timestamp <- last_visit$timestamp
      visitor_username <- get_user_info(client, last_visit$user_guid, connectServer)
    }
    if (is.na(item$content$title)) {
      item$content$title <- "" # use empty strings when content is missing title
    }
    # return required information from https://github.com/posit-dev/connect/issues/30288 
    all_failed_jobs <- bind_rows(lapply(seq_len(nrow(failed_jobs)), function(i) {
      tibble(
        "content_title" = item$content$title,
        "content_guid" = item$content$guid,
        "content_owner" = item$content$owner[[1]]$username,
        "job_failed_at" = failed_jobs$end_time[i],
        "failed_job_type" = failed_jobs$tag[i],
        "failure_reason" = failed_jobs$exit_code[i],
        "last_deployed_time" = item$content$last_deployed_time,
        "last_viewed_by" = visitor_username,
        "last_viewed_time" = visit_timestamp
      )
    }))
    print(all_failed_jobs)
    all_failed_jobs
  }
}

server <- function(input, output, session) {
  # use API key environment variables for now
  # we can add local run and connect API integration functionality later
  api_key <- Sys.getenv("CONNECT_API_KEY")
  connect_server <- Sys.getenv("CONNECT_SERVER")
  # initialize Connect API client
  client <- connect(server = connect_server, api_key = api_key)
  # set dashboard URL, needed for call to v1/users for visitor user_guid replacement
  connectServer <- client$get_dashboard_url()
  # get content once up front and pass it around for additional filtering
  content <- get_content(client, limit = inf)
  
  # cache content list
  content_list <- reactive({
    as_content_list(content, client)
  }) |> bindCache("static_key")
  
  # cache usage (uses firehose if available, legacy otherwise)
  usage <- reactive({
    get_usage(client)
  }) |> bindCache("static_key")

  # cache content with failed jobs 
  bad_content_df <- reactive({
    req(content_list(), usage())
    map_dfr(content_list(), ~ get_failed_job_data(.x, usage(), client, connectServer))
  }) |> bindCache("static_key")
  
  # output the table on load, wrapping in render UI 
  output$jobs <- renderDT({
    datatable(bad_content_df(), 
              rownames = FALSE, 
              escape = FALSE,
            )
  })
}

ui <- fluidPage(
  tags$head(
    # icons for pretty display 
    tags$link(rel = "stylesheet", href = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css")
  ),
  
  fluidRow(
    column(12, 
      titlePanel("Content With Issues (interactive table)")
    )
  ),
    
  tags$h3(class = "header-title", tags$i(class = "fas fa-exclamation-triangle"), "Content with Failures"),
  fluidRow(
    column(12,
           titlePanel(tags$h6("All content with a failed job:")), 
           DTOutput("jobs"),
    )
  )
)


shinyApp(ui, server)
