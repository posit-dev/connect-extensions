CONTENT_TYPE_ICONS <- list(
  "quarto-static"    = "icons/quarto.svg",
  "quarto-shiny"     = "icons/quarto.svg",
  "rmd-static"       = "icons/rmarkdown.svg",
  "rmd-shiny"        = "icons/rmarkdown.svg",
  "shiny"            = "icons/shiny.svg",
  "python-shiny"     = "icons/shiny.svg",
  "python-streamlit" = "icons/streamlit.svg",
  "python-dash"      = "icons/dash.svg",
  "python-bokeh"     = "icons/python.svg",
  "python-fastapi"   = "icons/api.svg",
  "python-api"       = "icons/api.svg",
  "api"              = "icons/api.svg",
  "jupyter-static"   = "icons/jupyter.svg",
  "jupyter-voila"    = "icons/jupyter.svg",
  "static"           = "icons/static.svg"
)

CONTENT_TYPE_LABELS <- list(
  "shiny"            = "Shiny",
  "rmd-shiny"        = "R Markdown",
  "rmd-static"       = "R Markdown",
  "static"           = "Static",
  "api"              = "Plumber API",
  "jupyter-static"   = "Jupyter",
  "python-api"       = "Python API",
  "python-dash"      = "Dash",
  "python-streamlit" = "Streamlit",
  "python-bokeh"     = "Bokeh",
  "python-panel"     = "Panel",
  "python-fastapi"   = "FastAPI",
  "quarto-shiny"     = "Quarto",
  "quarto-static"    = "Quarto",
  "python-shiny"     = "Shiny for Python",
  "jupyter-voila"    = "Voila",
  "python-gradio"    = "Gradio",
  "proxied"          = "Proxied"
)

content_icon_path <- function(app_mode) {
  if (is.null(app_mode) || (length(app_mode) == 1 && is.na(app_mode))) {
    return("icons/unknown.svg")
  }
  CONTENT_TYPE_ICONS[[app_mode]] %||% "icons/unknown.svg"
}

content_type_label <- function(app_mode) {
  if (is.null(app_mode) || (length(app_mode) == 1 && is.na(app_mode))) return("")
  CONTENT_TYPE_LABELS[[app_mode]] %||% app_mode
}
