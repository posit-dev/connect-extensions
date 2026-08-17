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

test_that("visitor_api_key returns status='anonymous' off-Connect with no fallback", {
  withr::with_envvar(
    list(CONNECT_CONTENT_GUID = ""),
    {
      out <- visitor_api_key(session = NULL,
                             connect_server = "https://x",
                             fallback_api_key = "")
      expect_equal(out$status, "anonymous")
      expect_equal(out$key, "")
    }
  )
})

test_that("visitor_api_key returns status='fallback' off-Connect with a publisher key", {
  withr::with_envvar(
    list(CONNECT_CONTENT_GUID = ""),
    {
      out <- visitor_api_key(session = NULL,
                             connect_server = "https://x",
                             fallback_api_key = "pub-key")
      expect_equal(out$status, "fallback")
      expect_equal(out$key, "pub-key")
    }
  )
})

test_that("visitor_api_key returns status='anonymous' on-Connect with no session token", {
  withr::with_envvar(
    list(CONNECT_CONTENT_GUID = "some-guid"),
    {
      out <- visitor_api_key(session = NULL,
                             connect_server = "https://x",
                             fallback_api_key = "pub-key")
      # On Connect, never leak publisher perms to an unauthenticated viewer.
      expect_equal(out$status, "anonymous")
      expect_equal(out$key, "")
    }
  )
})

test_that("api_request strips a trailing slash from connect_server", {
  req <- api_request("https://connect.example.com/", "fake-key",
                     "/__api__/v1/foo")
  expect_equal(req$url, "https://connect.example.com/__api__/v1/foo")
})

test_that("api_request leaves connect_server alone when there's no trailing slash", {
  req <- api_request("https://connect.example.com", "fake-key",
                     "/__api__/v1/foo")
  expect_equal(req$url, "https://connect.example.com/__api__/v1/foo")
})

test_that("api_request handles NULL connect_server defensively", {
  req <- api_request(NULL, "fake-key", "/__api__/v1/foo")
  expect_equal(req$url, "/__api__/v1/foo")
})

test_that(".content_url strips a trailing slash from connect_server", {
  expect_equal(
    .content_url("https://connect.example.com/", "g1"),
    "https://connect.example.com/content/g1/"
  )
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

test_that(".scrub_secrets masks a literal API key", {
  key <- "AbCdEf0123456789AbCdEf0123456789"
  out <- .scrub_secrets(
    sprintf("ran with key=%s and then failed", key),
    api_keys = key
  )
  expect_false(grepl(key, out, fixed = TRUE))
  expect_match(out, "<redacted>", fixed = TRUE)
})

test_that(".scrub_secrets masks Authorization headers without a known literal", {
  out <- .scrub_secrets("Authorization: Key x12345678901234567890abcdef")
  expect_false(grepl("x12345678901234567890abcdef", out))
  expect_match(out, "<redacted>", fixed = TRUE)
})

test_that(".scrub_secrets masks bare Bearer and Key tokens", {
  out <- .scrub_secrets("got 401 with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp.foo.bar")
  expect_false(grepl("eyJhbGci", out))
})

test_that(".scrub_secrets masks api_key in URLs", {
  out <- .scrub_secrets("GET /__api__/v1/foo?api_key=abc12345xyz&include=owner")
  expect_false(grepl("abc12345xyz", out))
  expect_match(out, "include=owner", fixed = TRUE)
})

test_that(".scrub_secrets leaves ordinary errors alone", {
  out <- .scrub_secrets("ordinary error: file not found")
  expect_equal(out, "ordinary error: file not found")
})

test_that(".scrub_secrets tolerates empty api_keys vector and empty entries", {
  out <- .scrub_secrets("plain text", api_keys = character(0))
  expect_equal(out, "plain text")
  out2 <- .scrub_secrets("plain text", api_keys = c("", ""))
  expect_equal(out2, "plain text")
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
