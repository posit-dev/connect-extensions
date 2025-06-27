box::use(
  lubridate,
  shiny[div, moduleServer, NS, numericInput, reactive, req, selectInput, tags],
)
#' @export
default_min_time_list <- list(number = 0, unit = "minutes")

#' Return a list used by the ui component to set the default values
#' @param min_time A string in the format "HH:MM:SS" giving the minimum duration
#'  of each session to be used in the filter
#' @details Given `min_time`, this function needs to return a list
#'  with two elements: `number` (any integer) and `unit` (
#'  any of `c("seconds", "minutes", "hours")`).
#'
#'  So, "00:00:30" returns `list(number=30, unit="seconds")`,
#'  "00:03:00" returns `list(number=3, unit="minutes")`,
#'  "00:01:30" returns `list(number=90, unit="seconds")` and so on.
#'
#' @export
get_min_time <- function(min_time) {

  # covers the case when min_time is a list with just one element
  if (is.list(min_time)) {
    min_time <- min_time[[1]]
  }

  min_time_in_seconds <-
    lubridate$hms(min_time) |>
    lubridate$seconds() |>
    as.integer()

  # if it failed to parse or it is negative, just use the default "0 minutes"
  if (is.na(min_time_in_seconds) || min_time_in_seconds <= 0) {
    return(default_min_time_list)
  }

  # if it is an hour
  if (min_time_in_seconds %% 3600 == 0) {
    return(list(number = min_time_in_seconds %/% 3600, unit = "hours"))
  } # if it is a minute
  if (min_time_in_seconds %% 60 == 0) {
    return(list(number = min_time_in_seconds %/% 60, unit = "minutes"))
  }

  list(number = min_time_in_seconds, unit = "seconds")
}

#' @export
ui <- function(id, min_time = NULL) {
  ns <- NS(id)

  min_time_list <- get_min_time(min_time)
  duration_units <- c("seconds", "minutes", "hours")

  div(
    class = "form-group shiny-input-container",
    tags$label("Minimum session duration", class = "control-label"),
    div(
      class = "session-duration-input-controls",
      div(
        numericInput(
          inputId = ns("value"),
          label = NULL,
          value = min_time_list$number,
          min = 0,
          max = 99999,
          step = 1
        )
      ),
      div(
        selectInput(
          inputId = ns("unit"),
          label = NULL,
          choices = duration_units,
          selected = min_time_list$unit
        )
      )
    )
  )
}

#' @export
server <- function(id) {
  moduleServer(
    id, function(input, output, session) {
      session_duration_seconds <- reactive({
        req(input$value, input$unit)

        session_duration <- lubridate$duration(input$value, input$unit)
        as.numeric(session_duration)
      })

      session_duration_seconds
    }
  )
}
