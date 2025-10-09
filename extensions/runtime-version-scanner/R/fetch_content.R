library(connectapi)

app_mode_groups <- function() {
  list(
    "API" = c("api", "python-fastapi", "python-api", "tensorflow-saved-model"),
    "Application" = c(
      "shiny",
      "python-shiny",
      "python-dash",
      "python-gradio",
      "python-streamlit",
      "python-bokeh"
    ),
    "Jupyter" = c("jupyter-static", "jupyter-voila"),
    "Quarto" = c("quarto-shiny", "quarto-static"),
    "R Markdown" = c("rmd-shiny", "rmd-static"),
    "Pin" = c("pin"),
    "Other" = c("unknown")
  )
}

fetch_content <- function(client, content_type_filter = NULL) {
  owner <- "owner:@me"
  type <- type_query(content_type_filter)

  parts <- Filter(nzchar, c(owner, type))
  query <- paste(parts, collapse = " ")

  search_content(client, q = query, include = "owner")
}

type_query <- function(content_types) {
  if (length(content_types) == 0 || is.null(content_types)) {
    return(character(0))
  }
  app_modes <- paste(unlist(app_mode_groups()[content_types]), collapse = ",")
  if (!nzchar(app_modes)) {
    return(character(0))
  }
  paste0("type:", app_modes)
}

content_list_to_data_frame <- function(content_list) {
  connectapi:::parse_connectapi_typed(
    content_list,
    connectapi:::connectapi_ptypes$content
  )
}
