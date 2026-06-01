# Connect API helpers. All functions take connect_server / connect_api_key as
# explicit arguments so they're easy to test or stub.

# Returns an API key scoped to the visitor making the current Shiny request,
# minted via `connectapi::connect()`'s OAuth token exchange. Requires that a
# "Posit Connect API" (Visitor API Key) OAuth integration is associated with
# the deployed Configurator content — see README.
#
# Falls back to `fallback_api_key` (the publisher's CONNECT_API_KEY) only
# when running outside Connect (local dev with no `CONNECT_CONTENT_GUID`
# env var injected). When running on deployed Connect:
#   - If a session token is present but token exchange fails, returns "".
#   - If no session token is present at all (e.g. anonymous viewer), also
#     returns "".
# Returning "" in those cases forces the rendered page into its empty-state
# path rather than silently using the publisher's view permissions.
#
# Mint per-action rather than once per session: Connect-minted visitor keys
# are short-lived, so caching at session start would break long-lived
# Shiny sessions. The caller can layer its own session-scoped cache if the
# extra HTTP cost matters.
visitor_api_key <- function(session, connect_server, fallback_api_key) {
  token <- if (!is.null(session)) {
    session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
  } else {
    NULL
  }
  if (is.null(token) || !nzchar(token)) {
    # Distinguish "no Connect at all" (local-dev, quarto preview) from
    # "deployed Connect with no session token" (anonymous viewer of a
    # collection that allows anonymous access). The publisher key is a
    # reasonable fallback for the former but a silent privilege leak for
    # the latter, so we return "" on Connect and let the empty-state UX
    # take over.
    on_connect <- nzchar(Sys.getenv("CONNECT_CONTENT_GUID", ""))
    return(if (on_connect) "" else fallback_api_key)
  }

  audience <- Sys.getenv("CONNECT_VISITOR_INTEGRATION_GUID", "")
  audience <- if (nzchar(audience)) audience else NULL

  tryCatch({
    client <- connectapi::connect(
      server          = connect_server,
      api_key         = fallback_api_key,
      token           = token,
      audience        = audience,
      .check_is_fatal = FALSE
    )
    client$api_key
  }, error = function(e) {
    warning(sprintf(
      "visitor_api_key: token exchange failed (%s); returning empty key to force the empty-state UX rather than silently using publisher permissions.",
      conditionMessage(e)
    ))
    ""
  })
}

api_request <- function(connect_server, connect_api_key, path) {
  req <- httr2::request(paste0(connect_server, path))
  if (nzchar(connect_api_key)) {
    req <- httr2::req_headers(req, Authorization = paste("Key", connect_api_key))
  }
  req
}

search_content <- function(connect_server, connect_api_key, query) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/search/content") |>
      httr2::req_url_query(
        q = paste("published:true locked:false", query),
        include = "owner",
        page_size = 20
      ) |>
      httr2::req_perform()
    httr2::resp_body_json(resp)$results %||% list()
  }, error = function(e) {
    message("search_content error: ", e$message)
    list()
  })
}

get_tags <- function(connect_server, connect_api_key) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/tags") |>
      httr2::req_perform()
    httr2::resp_body_json(resp)
  }, error = function(e) { message("get_tags error: ", e$message); list() })
}

get_content <- function(connect_server, connect_api_key, guid) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key,
                        paste0("/__api__/v1/content/", guid)) |>
      httr2::req_url_query(include = "owner") |>
      httr2::req_perform()
    httr2::resp_body_json(resp)
  }, error = function(e) { message("get_content error: ", e$message); NULL })
}

# Look up a content item by its Connect `name` (the URL-slug-style identifier,
# not the title). Returns the first match, or NULL. Used after a CREATE
# deploy when rsconnect's deployment record carries the integer content ID
# instead of the GUID — the marker-based name we generate is unique enough
# to resolve the GUID via the v1/content collection endpoint.
get_content_by_name <- function(connect_server, connect_api_key, name) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/content") |>
      httr2::req_url_query(name = name) |>
      httr2::req_perform()
    results <- httr2::resp_body_json(resp)
    if (length(results) > 0) results[[1]] else NULL
  }, error = function(e) {
    message("get_content_by_name error: ", e$message); NULL
  })
}

# Discovery: list collection dashboards via the marker in `name`.
# Uses the search endpoint (broad text match) and filters client-side so
# we only return items where the marker is actually the name prefix.
fetch_collection_dashboards <- function(connect_server, connect_api_key) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/search/content") |>
      httr2::req_url_query(
        q = COLLECTION_NAME_MARKER,
        include = "owner",
        page_size = 100
      ) |>
      httr2::req_perform()
    result <- httr2::resp_body_json(resp)
    items <- result$results %||% list()
    matched <- Filter(function(d) {
      n <- d$name %||% ""
      startsWith(n, paste0(COLLECTION_NAME_MARKER, "-"))
    }, items)
    message(sprintf(
      "fetch_collection_dashboards: search returned %d items, %d matched marker prefix",
      length(items), length(matched)
    ))
    matched
  }, error = function(e) {
    message("fetch_collection_dashboards error: ", e$message)
    list()
  })
}

# Download the content's currently-active source bundle to a tempfile.
# Returns the tempfile path, or NULL on failure.
download_active_bundle <- function(connect_server, connect_api_key, guid) {
  tryCatch({
    info <- get_content(connect_server, connect_api_key, guid)
    bundle_id <- info$bundle_id %||% NULL
    if (is.null(bundle_id)) return(NULL)

    out <- tempfile(fileext = ".tar.gz")
    api_request(connect_server, connect_api_key,
                paste0("/__api__/v1/content/", guid,
                       "/bundles/", bundle_id, "/download")) |>
      httr2::req_perform(path = out)
    out
  }, error = function(e) {
    message("download_active_bundle error: ", e$message)
    NULL
  })
}

# List collections owned by the current user via Connect's `owner:@me` token.
fetch_my_collections <- function(connect_server, connect_api_key) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/search/content") |>
      httr2::req_url_query(
        q = paste("published:true locked:false", "owner:@me", COLLECTION_NAME_MARKER),
        include = "owner",
        page_size = 100
      ) |>
      httr2::req_perform()
    items <- httr2::resp_body_json(resp)$results %||% list()
    Filter(function(d) {
      n <- d$name %||% ""
      startsWith(n, paste0(COLLECTION_NAME_MARKER, "-"))
    }, items)
  }, error = function(e) {
    message("fetch_my_collections error: ", e$message)
    list()
  })
}

# Build a shareable URL for a piece of Connect content. Prefers vanity_url
# (a path on the server) and falls back to the canonical /content/<guid> URL.
share_url <- function(connect_server, content) {
  server <- sub("/$", "", connect_server %||% "")
  vu <- content$vanity_url %||% ""
  if (nzchar(vu)) {
    if (!startsWith(vu, "/")) vu <- paste0("/", vu)
    paste0(server, vu)
  } else {
    paste0(server, "/content/", content$guid %||% "")
  }
}

# GET /v1/user — returns the caller's own profile. Used at publish time to
# bake the publisher's email into the collection so the rendered empty-state
# can show a mailto link. Returns NULL on error.
current_user <- function(connect_server, connect_api_key) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/user") |>
      httr2::req_perform()
    httr2::resp_body_json(resp)
  }, error = function(e) {
    message("current_user error: ", e$message)
    NULL
  })
}

# Look up which Posit Connect API integrations are currently associated
# with `content_guid`. Returns a character vector of integration GUIDs
# (first element is the first association), or NULL on error / none.
list_content_integrations <- function(connect_server, connect_api_key,
                                      content_guid) {
  tryCatch({
    resp <- api_request(
      connect_server, connect_api_key,
      paste0("/__api__/v1/content/", content_guid,
             "/oauth/integrations/associations")
    ) |>
      httr2::req_perform()
    items <- httr2::resp_body_json(resp)
    if (length(items) == 0) return(NULL)
    guids <- vapply(items,
                    function(i) i$oauth_integration_guid %||% NA_character_,
                    character(1))
    guids <- guids[!is.na(guids) & nzchar(guids)]
    if (length(guids) == 0) NULL else guids
  }, error = function(e) {
    message("list_content_integrations error: ", e$message)
    NULL
  })
}

# Resolve the visitor-integration GUID to attach to a freshly-published
# collection. Preference order:
#   1. CONNECT_VISITOR_INTEGRATION_GUID env var (explicit override)
#   2. The integration currently attached to the Configurator content
#      itself (CONNECT_CONTENT_GUID, auto-injected by Connect for
#      deployed content)
# Returns NULL if neither is available.
resolve_visitor_integration_guid <- function(connect_server, connect_api_key) {
  override <- Sys.getenv("CONNECT_VISITOR_INTEGRATION_GUID", "")
  if (nzchar(override)) return(override)

  self_guid <- Sys.getenv("CONNECT_CONTENT_GUID", "")
  if (!nzchar(self_guid)) return(NULL)

  guids <- list_content_integrations(connect_server, connect_api_key, self_guid)
  if (is.null(guids) || length(guids) == 0) NULL else guids[[1]]
}

# Attach the resolved visitor integration to a content item. Idempotent —
# PUT replaces associations with the array body provided. Returns TRUE on
# success, FALSE on any failure (including a missing/unresolvable
# integration GUID). Failures are message()'d and do not throw.
attach_visitor_integration <- function(connect_server, connect_api_key,
                                       content_guid) {
  integ <- resolve_visitor_integration_guid(connect_server, connect_api_key)
  if (is.null(integ) || is.na(integ) || !nzchar(integ)) {
    message("attach_visitor_integration: no integration GUID resolvable; ",
            "set CONNECT_VISITOR_INTEGRATION_GUID or run inside a ",
            "Configurator with an integration attached.")
    return(FALSE)
  }

  tryCatch({
    api_request(
      connect_server, connect_api_key,
      paste0("/__api__/v1/content/", content_guid,
             "/oauth/integrations/associations")
    ) |>
      httr2::req_method("PUT") |>
      httr2::req_body_json(list(list(oauth_integration_guid = integ))) |>
      httr2::req_perform()
    TRUE
  }, error = function(e) {
    message("attach_visitor_integration error: ", e$message)
    FALSE
  })
}

# Search Connect for content matching the given tag.
fetch_content_by_tag <- function(connect_server, connect_api_key, tag_name) {
  tryCatch({
    resp <- api_request(connect_server, connect_api_key, "/__api__/v1/search/content") |>
      httr2::req_url_query(
        q = paste0("published:true locked:false tag:", tag_name),
        include = "owner",
        page_size = 100
      ) |>
      httr2::req_perform()
    httr2::resp_body_json(resp)$results %||% list()
  }, error = function(e) {
    message("fetch_content_by_tag error: ", e$message)
    list()
  })
}
