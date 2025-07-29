
test_that("bar_chart creates expected structure", {
  chart <- bar_chart(50, 100)

  expect_equal(chart$name, "div")
  expect_equal(chart$attribs$class, "bar-cell")

  # Verify the bar div has the right class and properties
  bar_chart_div <- chart$children[[2]]
  expect_equal(bar_chart_div$attribs$class, "bar-chart")

  # Check the inner bar has the right width
  bar <- bar_chart_div$children[[1]]
  expect_equal(bar$attribs$class, "bar")
  expect_equal(bar$attribs$style$width, "50%")
})

test_that("full_url handles port correctly", {
  mock_session <- list(
    clientData = list(
      url_protocol = "https:",
      url_hostname = "example.com",
      url_port = "443",
      url_pathname = "/app/"
    )
  )

  # Test with port
  expect_equal(full_url(mock_session), "https://example.com:443/app/")

  # Test without port
  mock_session$clientData$url_port <- ""
  expect_equal(full_url(mock_session), "https://example.com/app/")
})
