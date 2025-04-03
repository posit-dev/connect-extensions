library(shinyBS)
library(shiny)
library(bslib)
library(gt)
library(connectapi)
library(dplyr)
library(purrr)
library(lubridate)
library(tidyr)
library(shinyjs)
library(shinycssloaders)
library(shinybusy)

source("./ui.R")

# cache data to disk with a refresh every 8h, table renders in ~7m when cache
# is expired, deleted, or on initial deploy
shinyOptions(
  cache = cachem::cache_disk("./app_cache/cache/", max_age = 60 * 60 * 8)
)

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

# user email is not on the content item owner object so we request it
# TODO: store user_guid = user_email list so we don't lookup the same user's 
# email for each failing content item they own
get_user_email <- function(client, guid) {
  user_endpoint <- paste0("v1/users/", guid)
  user <- client$GET(user_endpoint)
  user$email
}

# filters content jobs down to failures and sets content_recovered depending on 
# whether or not the latest job ended in error
filter_to_failed_jobs <- function(jobs) {
  failed_jobs <- if (nrow(jobs) == 0) {
    data.frame() 
    } else {
    # grab the latest job and all failing jobs
    latest_job <- jobs %>%
      slice_max(start_time, with_ties = FALSE)
    failed_jobs <- jobs %>%
      # filter out successful and running jobs 
      filter(exit_code != 0 & !(is.na(exit_code)) & status != 0 & !(is.na(end_time))) |>
      # grab only the columns we use for cleaner dplyr pipeline
      select(end_time, exit_code, tag, key) 
    # set content_recovered depending on if latest_job was in failed_jobs 
    failed_jobs %>%
      mutate(
        content_recovered = ifelse(latest_job$key %in% failed_jobs$key, FALSE, TRUE)
      )
    } 
  failed_jobs
}

# checks to see if a content item has failed jobs within the last 30d, then 
# compiles content and job data into a tibble, returning it.
get_failed_job_data <- function(item, client) {
  jobs <- tryCatch(
    {
      get_jobs(item) 
    }, error = function(e) {
      print(paste("Error encountered with item: ", item, e$message))
      data.frame() 
    })
  failed_jobs <- filter_to_failed_jobs(jobs)
  all_failed_jobs <- if (nrow(failed_jobs) == 0) {
    # content item does not have failed jobs
    data.frame() 
  } else {
    owner_email <- get_user_email(client, item$content$owner_guid)
    failed_jobs %>% 
      mutate(
        content_title = item$content$title,
        content_guid = item$content$guid,
        content_owner = item$content$owner[[1]]$username,
        log_url = paste0(item$content$dashboard_url,
                        "/logs?logKey=",
                        failed_jobs$key),
        owner_email = owner_email, 
        content_url = item$content$dashboard_url
        )
  }
  all_failed_jobs
}

server <- function(input, output, session) {
  # initialize Connect API client
  client <- connect()
  
  # TODO: use `v1/content/failed` to get content items with failed last job 
  # filter to deployed within last year for now
  content_list <- reactive({
    content <- get_content(client, limit = inf)
    content <- content %>%
      filter(last_deployed_time >= (Sys.time() - years(1)))
    as_content_list(content, client)
  }) |> bindCache("static_key")
  
  # cache failed jobs data, takes ~5m to build with content filtered to items 
  # deployed within the last year
  bad_content_df <- reactive({
    req(content_list()) 
    bad_content <- map_dfr(content_list(), ~ get_failed_job_data(.x, client)) 
    bad_content %>%
      rename(job_failed_at = end_time,
            failed_job_type = tag,
            failure_reason = exit_code) %>%
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
                    TRUE ~ failed_job_type),
                    # map exit codes to something more readable 
                    failure_reason = case_when(
                    failure_reason %in% c(1, 2, 134) ~ "failed to run / error during running",
                    failure_reason == 137 ~ "out of memory",
                    failure_reason %in% c(255, 15, 130) ~ "process terminated by server",
                    failure_reason %in% c(13, 127) ~ "configuration / permissions error",
                    # treat any unmapped exit_code integers as characters 
                    TRUE ~ as.character(failure_reason))) %>%
              group_by(content_guid) %>%
              mutate(content_guid = paste0('<a href="', 
                                            first(content_url), 
                                            '" target="_blank">', 
                                            first(content_title), 
                                            '</a>')) %>%
              mutate(owner_email = paste0('<span style="font-size: 32px;">',
                                          "<a href='mailto:",
                                          owner_email,
                                          "?subject=Problem%20with%20",
                                          gsub("'", 
                                              "%27", 
                                              gsub('"',
                                                  "%22",
                                                  content_title)),
                                          "&body=Please%20investigate:%0A",
                                          log_url,
                                          "'>",
                                          "✉",
                                          "</a></span>")) %>%
              mutate(log_url = paste0('<a href="',
                                     log_url,
                                     '" target="_blank">',
                                     '<span style="font-size: 32px;">🗒',
                                     '</a></span>')) %>%
              mutate(content_guid = ifelse(!content_recovered,
                paste(content_guid, " <span style='color: red;'>⚠️</span>"),
                content_guid)) %>%
              select(-content_url, -content_title, -key)
  }) |> bindCache("static_key")
  
  # show helpful information about what is and is not in failed jobs data
  # along with definitions of terms and descriptions of filter behavior
  observeEvent(input$show_help, {
    showModal(modalDialog(
      title = "Helpful info about this app",
      easyClose = TRUE,
      size = "m",
      help_information)
    )
  })
 
  # populate owners filter with username from compiled failed jobs data 
  observe({
    updateSelectInput(session, 
                      "owner_filter", 
                      choices = unique(bad_content_df()$content_owner))
  })
  
  # output the great table of failed jobs
  # TODO: better reflect current applied filters
  output$jobs <- render_gt({
      bad_content_df() %>%
        filter(if (input$currently_failing) content_recovered == FALSE else TRUE) %>%
        filter(if (input$not_notified) failed_job_type %in% c("Running",
                                                              "Configuring report",
                                                              "Restoring environment",
                                                              "Extracting parameters") else TRUE) %>%
        filter(if (!is.null(input$job_type)) failed_job_type %in% input$job_type else TRUE) %>%
        filter(if (!is.null(input$owner_filter)) content_owner %in% input$owner_filter else TRUE) %>%
        filter(if (!is.null(input$failure_reason)) failure_reason %in% input$failure_reason else TRUE) %>%
        gt() %>%
          fmt_markdown(columns = c(log_url, owner_email)) %>%
          sub_missing(columns = everything(), missing_text = " ") %>%
          cols_label(job_failed_at = "Date of Failure",
                     failure_reason = "Reason for Failure",
                     failed_job_type = "Job Type",
                     content_owner = "Owner",
                     owner_email = "Email Owner",
                     log_url = "Open Logs") %>% 
          cols_hide(content_recovered) %>%
          opt_interactive(use_page_size_select = TRUE,
                          use_sorting = TRUE,
                          use_search = TRUE)
  })
}

shinyApp(ui, server)
