test_that("content_icon_path returns the right SVG for known modes", {
  expect_equal(content_icon_path("quarto-static"), "icons/quarto.svg")
  expect_equal(content_icon_path("quarto-shiny"),  "icons/quarto.svg")
  expect_equal(content_icon_path("rmd-static"),    "icons/rmarkdown.svg")
  expect_equal(content_icon_path("rmd-shiny"),     "icons/rmarkdown.svg")
  expect_equal(content_icon_path("shiny"),         "icons/shiny.svg")
  expect_equal(content_icon_path("python-shiny"),  "icons/shiny.svg")
  expect_equal(content_icon_path("python-streamlit"), "icons/streamlit.svg")
  expect_equal(content_icon_path("python-dash"),   "icons/dash.svg")
  expect_equal(content_icon_path("python-api"),    "icons/api.svg")
  expect_equal(content_icon_path("api"),           "icons/api.svg")
  expect_equal(content_icon_path("jupyter-static"), "icons/jupyter.svg")
  expect_equal(content_icon_path("jupyter-voila"),  "icons/jupyter.svg")
  expect_equal(content_icon_path("static"),        "icons/static.svg")
})

test_that("content_icon_path returns unknown.svg for unrecognized modes", {
  expect_equal(content_icon_path("something-weird"), "icons/unknown.svg")
  expect_equal(content_icon_path(""),                "icons/unknown.svg")
  expect_equal(content_icon_path(NULL),              "icons/unknown.svg")
  expect_equal(content_icon_path(NA),                "icons/unknown.svg")
})

test_that("content_type_label returns human-readable name for known modes", {
  expect_equal(content_type_label("quarto-static"), "Quarto")
  expect_equal(content_type_label("rmd-static"),    "R Markdown")
  expect_equal(content_type_label("shiny"),         "Shiny")
  expect_equal(content_type_label("python-streamlit"), "Streamlit")
  expect_equal(content_type_label("python-dash"),   "Dash")
})

test_that("content_type_label falls back to the raw mode for unknown modes", {
  expect_equal(content_type_label("something-weird"), "something-weird")
  expect_equal(content_type_label(""),                "")
  expect_equal(content_type_label(NULL),              "")
})
