library(shiny)
library(bslib)
library(DT)
library(connectapi)
library(dplyr)
library(purrr)
library(tidyr)
library(ggplot2)

# cache data to disk with a refresh every 8h
shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 12)
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
    all_failed_jobs <- map_dfr(seq_len(nrow(failed_jobs)), ~
                                 tibble(
                                   "content_title" = item$content$title,
                                   "content_guid" = item$content$guid,
                                   "content_owner" = item$content$owner[[1]]$username,
                                   "job_failed_at" = failed_jobs$end_time[.x],
                                   "failed_job_type" = failed_jobs$tag[.x],
                                   "failure_reason" = failed_jobs$exit_code[.x],
                                   "last_deployed_time" = item$content$last_deployed_time,
                                   "last_visited" = as.POSIXct(last_visit$timestamp)
                                 )
    )
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
    map_dfr(content_list(), ~ get_failed_job_data(.x, usage())) |>
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
           # treat any unmapped exit_code integers as characters 
           TRUE ~ as.character(failure_reason))) |>
    mutate(content_title = replace_na(content_title, ""))
  }) |> bindCache("static_key")
 
  # output plot of failed jobs per content item
  output$jobs <- renderPlot({
    failed_job_counts <- bad_content_df() %>%
      group_by(content_guid) %>%
      summarise(total_failed_jobs = n(), .groups = "drop")
    ggplot(failed_job_counts, aes(x = content_guid, y = total_failed_jobs)) +
      geom_bar(stat = "identity", fill = "limegreen") +
      labs(title = "Total Failed Jobs per Content Item",
           x = "Content Item",
           y = "Total Failed Jobs") +
      theme_minimal()
  })
  
  # output plot of failed jobs over time 
  output$jobs_timeline <- renderPlot({
    failed_jobs_timeline <- bad_content_df() %>%
      mutate(date = as.Date(job_failed_at)) %>%
      group_by(date) %>%
      summarise(total_failed_jobs = n(), .groups = "drop")
    ggplot(failed_jobs_timeline, aes(x = date, y = total_failed_jobs)) +
      geom_line(color = "limegreen", linewidth = 1) +
      geom_point(color = "purple", size = 3) +
      labs(title = "Total Failed Jobs Over Time",
           x = "Date",
           y = "Total Failed Jobs") +
      theme_minimal()
  })
  
  # output plot of failed jobs per content owner 
  output$jobs_by_owner <- renderPlot({
    failed_by_owner <- bad_content_df() %>%
      group_by(content_owner) %>%
      summarise(total_failed_jobs = n(), .groups = "drop")
    ggplot(failed_by_owner, aes(x = content_owner, y = total_failed_jobs)) +
      geom_bar(stat = "identity", fill = "limegreen") +
      labs(title = "Total Failed Jobs per Content Owner",
           x = "Owner",
           y = "Total Failed Jobs") +
      theme_minimal()
  })
}

ui <- fluidPage(
  fluidRow(
    column(12, 
           titlePanel("Content With Issues (plot edition)")
    )
  ),
  
  fluidRow(
    column(12,
           titlePanel(tags$h6("Total failed jobs per content item:")), 
           plotOutput("jobs"),
    )
  ),
  fluidRow(
    column(12,
           titlePanel(tags$h6("Total failed jobs per content owner:")), 
           plotOutput("jobs_by_owner"),
    )
  ),
  fluidRow(
    column(12,
           titlePanel(tags$h6("Total failed jobs over time:")), 
           plotOutput("jobs_timeline"),
    )
  )
)


shinyApp(ui, server)
