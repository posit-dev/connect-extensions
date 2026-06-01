# Copy `template_dir`'s contents into a fresh tempdir and write
# collection.json next to them. Returns the staged dir path.
# Skips publisher state and renv build artifacts that should never be
# part of a per-collection deploy bundle.
STAGE_BUNDLE_SKIP <- c(
  ".posit",          # Posit Publisher records
  ".quarto",         # Quarto build cache
  "_freeze",         # Quarto frozen renders
  "_site",           # Quarto rendered site
  "rsconnect"        # rsconnect deployment record from prior calls
)

# Files copied into every staged bundle from the configurator's R/ directory.
# These are needed by the deployed dashboard's index.qmd at render time.
STAGE_BUNDLE_R_FILES <- c("render.R", "icons.R", "connect_api.R")

stage_bundle <- function(template_dir, config) {
  if (!dir.exists(template_dir)) {
    stop(sprintf("stage_bundle: template directory not found: %s", template_dir))
  }
  staged <- tempfile("collection-bundle-")
  dir.create(staged)

  entries <- list.files(template_dir, full.names = TRUE, all.files = TRUE,
                        no.. = TRUE)
  entries <- entries[!basename(entries) %in% STAGE_BUNDLE_SKIP]
  file.copy(entries, staged, recursive = TRUE)

  # Inside renv/, drop everything except activate.R and settings.json
  staged_renv <- file.path(staged, "renv")
  if (dir.exists(staged_renv)) {
    keep <- c("activate.R", "settings.json")
    inside <- list.files(staged_renv, full.names = TRUE, all.files = TRUE,
                         no.. = TRUE)
    drop <- inside[!basename(inside) %in% keep]
    if (length(drop) > 0) unlink(drop, recursive = TRUE)
  }

  # Copy shared R helpers used by the deployed dashboard's .qmd
  for (f in STAGE_BUNDLE_R_FILES) {
    src <- file.path("R", f)
    if (file.exists(src)) {
      file.copy(src, file.path(staged, f), overwrite = TRUE)
    }
  }

  # Copy www/icons/ -> icons/ so build_collection_html's <img src="icons/...">
  # resolves at render time. embed-resources: true inlines them as base64.
  icons_src <- file.path("www", "icons")
  if (dir.exists(icons_src)) {
    file.copy(icons_src, staged, recursive = TRUE)
  }

  jsonlite::write_json(
    config,
    file.path(staged, "collection.json"),
    auto_unbox = TRUE,
    pretty = TRUE,
    null = "null"
  )
  staged
}

# One-time per-process rsconnect setup. Idempotent.
setup_rsconnect <- function(connect_server, connect_api_key,
                            server_name = "connect",
                            account_name = "configurator") {
  rsconnect::addServer(
    url   = paste0(connect_server, "/__api__/"),
    name  = server_name,
    quiet = TRUE
  )
  rsconnect::connectApiUser(
    account = account_name,
    server  = server_name,
    apiKey  = connect_api_key
  )
  invisible(list(server = server_name, account = account_name))
}

# Spawn deploy in a background process. Returns a callr handle.
# On CREATE, pass appId = NULL — the child generates an appName via marker+uuid.
# On UPDATE, pass appId = <guid> — the existing name is preserved by Connect.
launch_deploy <- function(staged_dir, app_id, app_title,
                          connect_server, connect_api_key,
                          marker = COLLECTION_NAME_MARKER) {
  callr::r_bg(
    func = function(staged_dir, app_id, app_title,
                    connect_server, connect_api_key, marker) {
      rsconnect::addServer(
        url   = paste0(connect_server, "/__api__/"),
        name  = "connect",
        quiet = TRUE
      )
      rsconnect::connectApiUser(
        account = "configurator",
        server  = "connect",
        apiKey  = connect_api_key
      )

      app_name <- if (is.null(app_id)) {
        paste0(marker, "-", uuid::UUIDgenerate())
      } else {
        NULL
      }

      # rsconnect calls `quarto inspect` during deploy; on Connect the
      # binary often isn't on the Shiny process's PATH. Probe common
      # locations, set both RSCONNECT_QUARTO and prepend to PATH so
      # findQuarto() and any later Sys.which() both see it.
      versioned <- sort(Sys.glob("/opt/quarto/*/bin/quarto"), decreasing = TRUE)
      candidates <- c(
        unname(Sys.which("quarto")),
        Sys.getenv("QUARTO_PATH"),
        Sys.getenv("RSCONNECT_QUARTO"),
        versioned,
        "/opt/quarto/bin/quarto",
        "/usr/local/bin/quarto",
        "/usr/lib/rstudio-server/bin/quarto/bin/quarto"
      )
      candidates <- candidates[nzchar(candidates)]
      quarto_bin <- ""
      for (p in candidates) {
        if (file.exists(p)) { quarto_bin <- p; break }
      }
      if (!nzchar(quarto_bin)) {
        stop(sprintf(
          "Quarto binary not found. Tried: %s. Set QUARTO_PATH or RSCONNECT_QUARTO as an env var on the configurator's content settings.",
          paste(candidates, collapse = ", ")
        ))
      }
      Sys.setenv(RSCONNECT_QUARTO = unname(quarto_bin))
      Sys.setenv(PATH = paste(dirname(quarto_bin), Sys.getenv("PATH"), sep = .Platform$path.sep))
      message("Using quarto: ", quarto_bin)

      ok <- rsconnect::deployApp(
        appDir         = staged_dir,
        appId          = app_id,
        appName        = app_name,
        appTitle       = app_title,
        server         = "connect",
        account        = "configurator",
        forceUpdate    = TRUE,
        launch.browser = FALSE,
        logLevel       = "normal"
      )
      if (!isTRUE(ok)) stop("deployApp returned a non-TRUE result")

      # rsconnect writes a deployment record into staged_dir/rsconnect/.
      # Read the most recent record to get the real Connect URL and GUID.
      records <- rsconnect::deployments(appPath = staged_dir)
      if (nrow(records) == 0) {
        stop("deployApp succeeded but no deployment record was written")
      }
      latest <- records[nrow(records), ]

      # Resolve the GUID with explicit NULL/NA-safe fallbacks because the
      # callr child does not have R/config.R's %||% in scope.
      guid <- if (!is.null(latest$appGuid) && nchar(latest$appGuid) > 0) {
        latest$appGuid
      } else if (!is.null(latest$appId) && nchar(latest$appId) > 0) {
        latest$appId
      } else {
        NA_character_
      }

      list(
        url  = as.character(latest$url),
        guid = as.character(guid),
        name = if (!is.null(latest$name) && nchar(latest$name) > 0)
          as.character(latest$name) else app_name
      )
    },
    args = list(
      staged_dir       = staged_dir,
      app_id           = app_id,
      app_title        = app_title,
      connect_server   = connect_server,
      connect_api_key  = connect_api_key,
      marker           = marker
    ),
    supervise = TRUE
  )
}
