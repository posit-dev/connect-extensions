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
