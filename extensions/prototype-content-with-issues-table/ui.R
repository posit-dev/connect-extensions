help_information <- tags$div(
                  p("This interactive table displays failed content jobs ",
                    "grouped by content item. Job logs are accessible via ",
                    "the", strong("Go to logs")," link, and selecting the email ",
                    "icon (✉) will open a pre-populated message to the owner of ",
                    "the content."), 
                  p(strong("Types of content jobs in this table:")),
                  tags$ul(
                    tags$li(tags$span(strong("Render: "), 
                                      "Rendering Shiny and PyShiny applications.")),
                    tags$li(tags$span(strong("Runtime: "), 
                                      paste("Running Shiny, PyShiny, Bokeh, Dash, Streamlit, ",
                                           "Gradio, or Voila applications, or Plumber, Flask ",
                                           "FastAPI, and Tensorflow model APIs."))),
                    tags$li(tags$span(strong("Build: "), 
                                      "Building a report, Python notebook, or site.")),
                    tags$li(tags$span(strong("Environment restore: "),
                                      HTML("Python, R, or Quarto environment ",
                                      "restore from an environment file such as ",
                                      "<code>requirements.txt</code> or <code>manifest.json</code>."))),
                    tags$li(tags$span(strong("Report configuration: "),
                                      "Configuration of a parameterized report.")),
                    tags$li(tags$span(strong("Parameter extraction: "), 
                                      "Extracting parameters for Python notebooks."))
                  ),
                  p(strong("Not included in this table:")),
                  tags$ul(
                    # temporary restriction to help with performance
                    tags$li(tags$span(strong("Failed deployment information: "), 
                                      paste("Deploy jobs initiated by push-button, CLI, Git, or ",
                                            "an automated deploy process are not included in ",
                                            "content jobs history."))),
                    tags$li(tags$span(strong("Content without a bundle activation in 1y :"), 
                                      paste("Bundles are pieces of content that are typically ", 
                                            "activated after they are uploaded as part of a ",
                                            "push-button, CLI, Git, or automated deployment ",
                                            "process. Activating an old bundle on a content ",
                                            "item is considered a deployment."))),
                    tags$li(tags$span(strong("Unpublished content: "), 
                                      "Unpublished content does not have jobs history.")),
                    tags$li(tags$span(strong("Self-tests: "),
                                      paste("Manually triggered and scheduled system tests ",
                                      "of process execution environments and the ",
                                      "Connect server itself are not included in ",
                                      "content jobs history.")))
                    ),
                   p(strong("Available filters:")),
                   tags$ul(
                     tags$li(strong("Broken content:"), 
                             " display items where the latest job ended in failure."),
                     tags$li(strong("Owner not notified:"), 
                             paste(" display failed runtime, report configuration, ",
                             "environment restore and parameter extraction jobs. ",
                             "Content owners are always emailed on Python, ",
                             "Quarto, and R report build or render failure.")),
                     tags$li(strong("Failure reason:"), " 
                             display items that match the selected cause for failure."),
                     tags$li(strong("Job type:"), " 
                             display items that match the selected content job.")
                   )
)
  

ui <- fluidPage(
  useShinyjs(),
  fluidRow(
    add_busy_bar(), 
    column(2,
          actionButton("show_help", 
                      label = tagList(icon("question-circle"), 
                                     "Help"), 
                      class = "btn-info"),
          p(strong("Filter by: ")),
          checkboxInput("currently_failing", "Broken content"),
          checkboxInput("not_notified", "Owner not notified"),
          selectInput("job_type", "Job Type", c("Running", 
                                                "Rendering", 
                                                "Extracting parameters", 
                                                "Building",
                                                "Restoring environment",
                                                "Configuring report"),
                     multiple = TRUE,
                     selected = NULL
                     ),
          selectInput("failure_reason", "Reason for Failure", 
                                      c("out of memory",
                                        "process terminated by server",
                                        "configuration / permissions error",
                                        "failed to run / error during running"),
                    multiple = TRUE,
                    selected = FALSE
                    ),
        ),
    titlePanel(h4("Failed content jobs:")),
    gt_output("jobs"),
  )
)
 