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

# filters content jobs down to failures and sets content_recovered depending on 
# whether or not the latest job ended in error
filter_jobs <- function(jobs) {
  if (is.null(jobs) || nrow(jobs) == 0){
    # content item does not have any jobs
    NULL
  } else {
    # grab the latest job and all failing jobs
    latest_job <- jobs %>%
      slice_max(start_time, with_ties = FALSE)
    failed_jobs <- jobs %>%
      # filter out successful and running jobs 
      filter(exit_code != 0 & !(is.na(exit_code)) & status != 0 & !(is.na(end_time))) |>
      # grab only the columns we use for cleaner dplyr pipeline
      select(end_time, exit_code, tag, key) %>%
      # check if the latest job is a failure
      mutate(
        content_recovered = ifelse(latest_job$key %in% failed_jobs$key, FALSE, TRUE)
      )
    failed_jobs
  }
}

# checks to see if a content item has failed jobs within the last 30d, then 
# compiles content and job data into a tibble, returning it.
get_failed_job_data <- function(item) {
  jobs <- tryCatch(
    {
      get_jobs(item) 
    }, error = function(e) {
      print(paste("Error encountered with item: ", item, e$message))
      NULL
    })
  failed_jobs <- filter_jobs(jobs)
  if (is.null(failed_jobs) || nrow(failed_jobs) == 0) {
    # content item does not have failed jobs
    NULL
  } else {
    all_failed_jobs <- failed_jobs %>% 
      mutate(
        content_title = item$content$title,
        content_guid = item$content$guid,
        content_owner = item$content$owner[[1]]$username,
        content_url = item$content$dashboard_url)
    all_failed_jobs
  }
}

server <- function(input, output, session) {
  # initialize Connect API client
  client <- connect()
  
  # TODO: use `v1/content/failed` when #30414 merges so we only list content we
  # know has failed before, filter to deployed within last year for now
  content_list <- reactive({
    content <- get_content(client, limit = inf)
    content <- content %>%
      filter(last_deployed_time >= (Sys.time() - years(1)))
    as_content_list(content, client)
  }) |> bindCache("static_key")
  
  # cache last 30d of usage (Jobs.MaxCompleted is 30d), takes ~5m to build
  usage <- reactive({
    from = (Sys.time() - days(30))
    to = Sys.time()
    get_usage(client, from, to) # ~100 pages of results
  }) |> bindCache("static_key")
  
  # cache failed jobs data, takes ~2m to build with content filtered to items 
  # deployed within the last year
  bad_content_df <- reactive({
    req(content_list()) 
    bad_content <- map_dfr(content_list(), ~ get_failed_job_data(.x)) 
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
                                            '">', 
                                            first(content_title), 
                                            '</a>')) %>%
              mutate(content_guid = ifelse(!content_recovered,
                paste(content_guid, " <span style='color: red;'>⚠️</span>"),
                content_guid)) %>%
              select(-content_url, -content_title, -key)
  }) |> bindCache("static_key")
  
  # show helpful information about what is and is not in failed jobs data
  observeEvent(input$show_help, {
    toggle("help_section")
  })
  
  # output the great table of failed jobs
  output$jobs <- render_gt({
      bad_content_df() %>%
        filter(if (input$currently_failing) content_recovered == FALSE else TRUE) %>%
        filter(if (input$not_notified) failed_job_type != "Rendering" else TRUE) %>%
        filter(if (!is.null(input$job_type)) failed_job_type %in% input$job_type else TRUE) %>%
        filter(if (!is.null(input$failure_reason)) failure_reason %in% input$failure_reason else TRUE) %>%
        gt() %>%
          # highlight rows where the content item's latest job failed
          tab_style(style = cell_fill(color = "salmon"),
                    locations = cells_body(
                    rows = which(!content_recovered))) %>%
          sub_missing(columns = everything(), missing_text = " ") %>%
          cols_label(job_failed_at = "Date of Failure",
                     failure_reason = "Reason for Failure",
                     failed_job_type = "Job Type",
                     content_owner = "Owner") %>% 
          cols_hide(content_recovered) %>%
          opt_interactive(use_page_size_select = TRUE,
                          use_filters = TRUE)
  })
}

ui <- fluidPage(
  useShinyjs(),
  bsTooltip(id = "extract",
            title = "Extracting parameters for Python notebooks.",
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "render",
            title = "Rendering Shiny and PyShiny applications.",
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "build",
            title = "Building a report, Python notebook, or site.",
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "run",
            title = paste("Running Shiny, PyShiny, Bokeh, Dash, Streamlit, ",
                          "Gradio, or Voila applications, or Plumber, Flask ",
                          "FastAPI, and Tensorflow model APIs."),
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "configure",
            title = "Configuration of a parameterized report.",
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "restore",
            title = "Python or R environment restore.",
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "unpublished",
            title = "Unpublished content does not have jobs history.",
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "what_is_deploy",
            title = paste("Deploy jobs initiated by push-button, CLI, Git, or ",
                          "an automated deploy process are not included in ",
                          "content jobs history."),
            placement = "top",
            trigger = "hover"),
  bsTooltip(id = "what_is_bundle",
            title = paste("Bundles are pieces of content that are typically ", 
                          "activated after they are uploaded as part of a ",
                          "push-button, CLI, Git, or automated deployment ",
                          "process. Activating an old bundle on a content ",
                          "item is considered a deployment."),
            placement = "top",
            trigger = "hover"),
  tags$head(
    # don't cut off long tooltips
    tags$style(HTML(".tooltip-inner {
                    text-align: left !important;
                    max-width: 600px !important;
                    }"))
  ),
  fluidRow(
    column(12,
          actionButton("show_help", "What is included here?", class = "btn-info")),
          tags$div(id = "help_section", 
                   style = "display: none; padding: 20px; border: 2px solid; background-color: #f9f9f9; border-radius: 8px; margin-top: 10px;",
          fluidRow(
            column(4,
                  p(strong("Types of content jobs in this table:")),
                  tags$ul(
                    tags$li(tags$span("Render", id = "render")),
                    tags$li(tags$span("Runtime", id = "run")),
                    tags$li(tags$span("Build", id = "build")),
                    tags$li(tags$span("Environment restore", id = "restore")),
                    tags$li(tags$span("Report configuration", id = "configure")),
                    tags$li(tags$span("Parameter extraction", id = "extract")))
                  ),
            column(6,
                  p(strong("Not included in this table:")),
                  tags$ul(
                    # temporary restriction to help with performance
                    tags$li(tags$span("Content without a bundle activation in 1y", 
                                      id = "what_is_bundle")),
                    tags$li(tags$span("Failed deployment information", 
                                      id = "what_is_deploy")),
                    tags$li(tags$span("Unpublished content", 
                                      id = "unpublished")),
                    tags$li("Self-tests"))
                  )
            ),
          fluidRow(
            column(12,
                   p(strong("Available filters:")),
                   tags$ul(
                     tags$li(strong("Unrecovered content:"), 
                             " display items where the latest job ended in failure."),
                     tags$li(strong("Owner not notified:"), 
                             paste(" display failed runtime, report configuration, ",
                             "environment restore, parameter extraction, and build ",
                             "jobs where someone other than the content owner visited ",
                             "the content during the failed job run period. We use ",
                             "visit data here as a best estimate of who triggered the ",
                             "job. Content owners are always emailed on render failure.")),
                     tags$li(strong("Failure reason:"), " 
                             display items that match the selected cause for failure."),
                     tags$li(strong("Job type:"), " 
                             display items that match the selected content job.")
                   )
            )),
          ),
    column(4, 
          checkboxInput("currently_failing", "Unrecovered content"),
          # TODO: further filtering by owner in visit data
          checkboxInput("not_notified", "WIP: Owner not notified")
           ),
    column(4,
           selectInput("job_type", "Job type", c("Running", 
                                                  "Rendering", 
                                                  "Extracting parameters", 
                                                  "Building",
                                                  "Restoring environment",
                                                  "Configuring report"),
                       multiple = TRUE,
                       selected = NULL
                       )
           ),
    column(4,
           selectInput("failure_reason", "Failure reason", 
                                        c("out of memory",
                                          "process terminated by server",
                                          "configuration / permissions error",
                                          "failed to run / error during running"),
                      multiple = TRUE,
                      selected = FALSE
                      )
           )
  ),
  fluidRow(
    column(12,
           titlePanel(tags$h6("Matching failed jobs:")), 
           gt_output("jobs"),
    )
  )
)

shinyApp(ui, server)
