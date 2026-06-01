test_that("share_url uses vanity_url when present", {
  url <- share_url("https://connect.example.com",
                   list(guid = "g1", vanity_url = "/team/dashboard/"))
  expect_equal(url, "https://connect.example.com/team/dashboard/")
})

test_that("share_url adds a leading slash to vanity_url if missing", {
  url <- share_url("https://connect.example.com",
                   list(guid = "g1", vanity_url = "team/dash"))
  expect_equal(url, "https://connect.example.com/team/dash")
})

test_that("share_url falls back to /content/<guid> when vanity_url is empty", {
  url <- share_url("https://connect.example.com",
                   list(guid = "g1", vanity_url = ""))
  expect_equal(url, "https://connect.example.com/content/g1")
})

test_that("share_url falls back when vanity_url is missing", {
  url <- share_url("https://connect.example.com", list(guid = "g1"))
  expect_equal(url, "https://connect.example.com/content/g1")
})

test_that("share_url strips a trailing slash from connect_server", {
  url <- share_url("https://connect.example.com/",
                   list(guid = "g1"))
  expect_equal(url, "https://connect.example.com/content/g1")
})

test_that("current_user returns NULL on httr2 error and logs a message", {
  # Force the error path by hitting a host that won't resolve.
  out <- suppressMessages(
    current_user("http://no-such-host.invalid", "fake-key")
  )
  expect_null(out)
})

test_that("attach_visitor_integration returns FALSE when no integration GUID is resolvable", {
  withr::with_envvar(
    list(CONNECT_VISITOR_INTEGRATION_GUID = "", CONNECT_CONTENT_GUID = ""),
    {
      out <- suppressMessages(
        attach_visitor_integration(
          connect_server = "http://no-such-host.invalid",
          connect_api_key = "fake-key",
          content_guid = "abc-123"
        )
      )
      expect_false(out)
    }
  )
})

test_that("attach_visitor_integration uses CONNECT_VISITOR_INTEGRATION_GUID when set", {
  # With an unresolvable host, the call must still pass the integration-
  # resolution stage (no 'no integration GUID' message) and fail at the
  # HTTP layer instead.
  msgs <- capture.output({
    withr::with_envvar(
      list(CONNECT_VISITOR_INTEGRATION_GUID = "integration-xyz"),
      {
        out <- attach_visitor_integration(
          connect_server = "http://no-such-host.invalid",
          connect_api_key = "fake-key",
          content_guid = "abc-123"
        )
        expect_false(out)
      }
    )
  }, type = "message")
  # The "no integration GUID" message should NOT appear — we have an env var.
  expect_false(any(grepl("no integration GUID", msgs)))
})
