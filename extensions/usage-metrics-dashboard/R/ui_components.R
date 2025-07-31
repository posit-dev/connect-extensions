library(shiny)

# Create a bar chart HTML element for use in the content reactable.
bar_chart <- function(
  value,
  max_val,
  height = "1rem",
  fill = "#7494b1",
  background = NULL
) {
  width <- paste0(value * 100 / max_val, "%")
  value <- format(value, width = nchar(max_val), justify = "right")
  bar <- div(class = "bar", style = list(background = fill, width = width))
  chart <- div(class = "bar-chart", style = list(background = background), bar)
  label <- span(class = "number", value)
  div(class = "bar-cell", label, chart)
}

# Construct full URL from Shiny session
full_url <- function(session) {
  paste0(
    session$clientData$url_protocol,
    "//",
    session$clientData$url_hostname,
    if (nzchar(session$clientData$url_port)) {
      paste0(":", session$clientData$url_port)
    },
    session$clientData$url_pathname
  )
}
