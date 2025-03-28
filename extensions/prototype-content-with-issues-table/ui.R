help_information <- tags$div(
                  p("This interactive table displays failed content jobs ",
                    "grouped by content item. Click the notepad (🗒) to open ",
                    "job logs, and select the the email icon (✉) to send a ",
                    "message to the content owner. Select the content title to ",
                    "open its dashboard view."), 
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
                  p(strong("Filtering and sorting")),
                  p("Use the filters in the sidebar to display jobs matching ",
                    "the chosen criteria. When selecting options within a filter ",
                    "the failed jobs shown match any of the options chosen. For ",
                    "example, filtering by a job type of", strong("Running"), "or", strong("Building"),
                    "displays jobs of either the runtime or build type. When ",
                    "filters are combined the jobs shown match all of the chosen ",
                    "criteria across filters. For instance, selecting", strong("Broken content,"),
                    strong("Email not generated,"), "and owners", strong("bob"), "and", strong("sally"),
                    "will filter down to items owned by either user with a last ",
                    "job that ended in failure", em("and"), "where an email was not generated."),
                  p("Select a header within the table to sort the displayed ",
                    "page by the chosen column in descending or ascending order. ",
                    "Use the table-wide search, available filters, and customizable ",
                    "page size to show only the data you're looking for in the ",
                    "appropriate order."),
                   tags$ul(
                     tags$li(strong("Broken content:"), 
                             " display items where the latest job ended in failure."),
                     tags$li(strong("Email not generated:"),
                             # emails are not sent in OHE env, see:
                             # https://github.com/posit-dev/connect/issues/19737
                             paste(" display failed runtime, report configuration, ",
                             "environment restore and parameter extraction jobs. ",
                             "A message containing failure details is sent to ",
                             "owners and collaborators by default following a ",
                             "Python, Quarto, or R report build or render failure.")),
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
          p(strong("Filters")),
          checkboxInput("currently_failing", "Broken content"),
          checkboxInput("not_notified", "Email not generated"),
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
          selectInput("owner_filter", 
                      "Content Owner", 
                      NULL, 
                      multiple = TRUE,
                      selected = FALSE
                      ),
        ),
    gt_output("jobs"),
  )
)
 