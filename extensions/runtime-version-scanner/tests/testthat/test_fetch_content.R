with_mock_api({
  client <- Connect$new("https://connect.example", api_key = "fake")
  client$version # To hydrate the version property

  without_internet({
    test_that("fetch_content() with no type query makes expected request", {
      expect_GET(
        fetch_content(client),
        "https://connect.example/__api__/v1/search/content?q=owner%3A%40me&page_number=1&page_size=500&include=owner"
      )
    })
    test_that("fetch_content() with type query makes expected request", {
      expect_GET(
        fetch_content(client, content_type_filter = "Pin"),
        "https://connect.example/__api__/v1/search/content?q=owner%3A%40me%20type%3Apin&page_number=1&page_size=500&include=owner"
      )
    })
  })
})

test_that("type_query handles NULL, empty, and unknown inputs", {
  expect_equal(type_query(NULL), character(0))
  expect_equal(type_query(character(0)), character(0))
  expect_equal(type_query("NonExistent"), character(0))
})

test_that("type_query returns correct queries for single content types", {
  expect_equal(
    type_query("API"),
    "type:api,python-fastapi,python-api,tensorflow-saved-model"
  )
  expect_equal(
    type_query("Application"),
    "type:shiny,python-shiny,python-dash,python-gradio,python-streamlit,python-bokeh"
  )
  expect_equal(type_query("Jupyter"), "type:jupyter-static,jupyter-voila")
  expect_equal(type_query("Quarto"), "type:quarto-shiny,quarto-static")
  expect_equal(type_query("R Markdown"), "type:rmd-shiny,rmd-static")
  expect_equal(type_query("Pin"), "type:pin")
  expect_equal(type_query("Other"), "type:unknown")
})

test_that("type_query handles multiple content types", {
  result <- type_query(c("API", "Jupyter"))
  expect_true(grepl("^type:", result))
  expect_true(grepl("api", result))
  expect_true(grepl("jupyter-static", result))
})
