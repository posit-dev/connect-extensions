library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(dplyr)
library(purrr)
library(tidyr)

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

# checks to see if a content item has failed jobs, grabs usage data if it does,
# then compiles content, job, and usage data together, returning it.
get_failed_job_data <- function(item, usage) {
  failed_jobs <- tryCatch(
    {
      get_jobs(item) |> 
        # filter successful jobs
        filter(exit_code != 0) 
    },
    error = function(e) {
      # content item does not have any jobs 
      NULL
    }
  )
  
  if (is.null(failed_jobs) || nrow(failed_jobs) == 0) {
    return(NULL)
  } else {
    # handle content without usage data, such as unpublished content
    last_visit <- usage %>%
      filter(content_guid == item$content$guid) %>%
      slice_max(timestamp) %>%
      select(timestamp)
    # return required information from https://github.com/posit-dev/connect/issues/30288
    all_failed_jobs <- map_dfr(seq_len(nrow(failed_jobs)), function(i) {
      tibble(
        "content_title" = item$content$title,
        "content_guid" = item$content$guid,
        "content_owner" = item$content$owner[[1]]$username,
        "job_failed_at" = failed_jobs$end_time[i],
        "failed_job_type" = failed_jobs$tag[i],
        "failure_reason" = failed_jobs$exit_code[i],
        "last_deployed_time" = item$content$last_deployed_time,
        "last_visited" = as.POSIXct(last_visit$timestamp)
      )
    })
    all_failed_jobs
  }
}

server <- function(input, output, session) {
  # initialize Connect API client
  client <- connect()
  
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
    map_dfr(content_list(), ~ get_failed_job_data(.x, usage()))
  }) |> bindCache("static_key")
  
  # output the datatable of failed jobs
  output$jobs <- renderDT({
    datatable(bad_content_df() |>
                # map job type to something more readable
                mutate(failed_job_type = case_when(
                  failed_job_type %in% c("build_report", "build_site", "build_jupyter") ~ "Building",
                  failed_job_type %in% c("packrat_restore", "python_restore") ~ "Restoring environment",
                  failed_job_type == "configure_report" ~ "Configuring report",
                  failed_job_type %in% c("run_app", 
                             "run_api", 
                             "run_tensorflow", 
                             "run_python_api",
                             "run_dash_app",
                             "run_gradio_app",
                             "run_streamlit",
                             "run_bokeh_app",
                             "run_fastapi_app",
                             "run_voila_app",
                             "run_pyshiny_app") ~ "Running",
                  failed_job_type == "render_shiny" ~ "Rendering",
                  failed_job_type == "ctrl_extraction" ~ "Extracting parameters",
                  TRUE ~ failed_job_type)) |>
                # map exit codes to something more readable 
                mutate(failure_reason = case_when(
                  failure_reason %in% c(1, 2, 134) ~ "failed to run / error during running",
                  failure_reason == 137 ~ "out of memory",
                  failure_reason %in% c(255, 15, 130) ~ "process terminated by server",
                  failure_reason %in% c(13, 127) ~ "configuration / permissions error",
                  TRUE ~ as.character(failure_reason))) |>
                mutate(content_title = replace_na(content_title, "")),
              rownames = FALSE, 
              escape = FALSE,
              options = list( # non-interactive table for this prototype
                paging = FALSE,
                searching = FALSE,
                ordering = FALSE, 
                info = FALSE, 
                dom = "t" 
              )
            )
  })
}

ui <- fluidPage(
  fluidRow(
    column(12, 
      titlePanel("Content With Issues (table view)")
    )
  ),
    
  fluidRow(
    column(12,
           titlePanel(tags$h6("All failed content jobs:")), 
           DTOutput("jobs"),
    )
  )
)


shinyApp(ui, server)
