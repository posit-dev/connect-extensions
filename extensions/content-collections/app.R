library(shiny)
library(shinyjs)
library(bslib)
library(httr2)
library(jsonlite)

# Source helper modules into the global environment so the server function
# and the UI builders can see them.
local({
  helpers <- list.files("R", pattern = "\\.R$", full.names = TRUE)
  for (f in helpers) source(f, local = FALSE)
})

connect_server  <- Sys.getenv("CONNECT_SERVER", "http://localhost:3939")
connect_api_key <- Sys.getenv("CONNECT_API_KEY", "")

# Configure rsconnect once at startup if a key is present.
if (nzchar(connect_api_key)) {
  tryCatch(
    setup_rsconnect(connect_server, connect_api_key),
    error = function(e) message("setup_rsconnect: ", e$message)
  )
}

# ---------- UI ----------
ui <- page_fillable(
  title = "Collection Configurator",
  theme = bs_theme(preset = "shiny"),
  shinyjs::useShinyjs(),
  tags$head(
    tags$script(HTML(DATETIME_LOCALIZER_JS)),
    tags$style("
      @media (prefers-reduced-motion: reduce) { .spinner-border { animation: none; } }

      /* App body never scrolls; modal contains its own scroll region */
      body { overflow: hidden; }

      /* Modal sizing: fit viewport, scroll inside the body */
      .modal-dialog {
        max-width: 760px;
        max-height: 90vh;
        margin: 5vh auto;
        display: flex;
        align-items: stretch;
      }
      .modal-content {
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        width: 100%;
      }
      .modal-body {
        overflow-y: auto;
        flex: 1 1 auto;
        min-height: 480px;
      }

      /* Footer layout: Share feedback far-left, buttons far-right */
      .modal-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .modal-footer > .wizard-footer-row {
        flex: 1 1 auto;
      }

      /* Compact, more-rounded buttons in the wizard footer */
      .btn-compact {
        padding: 0.375rem 1.25rem;
        border-radius: 0.5rem;
        font-size: 0.9rem;
      }

      /* Modal title wrapper needs to fill the header width so the BETA pill
         can sit flush against the right margin. */
      .modal-title { width: 100%; }

      /* Search-results / Selected subtab — active state uses a custom mid
         gray instead of Bootstrap's btn-secondary. */
      #select_subtab_results.btn-secondary,
      #select_subtab_selected.btn-secondary {
        background-color: #707073;
        border-color: #707073;
        color: #fff;
      }

      /* Result list scrolls inside the modal body if it overflows */
      .wizard-step-body .result-list {
        max-height: 40vh;
        overflow-y: auto;
      }

      /* Row toggle: each search result is an actionButton spanning the row.
         Counter-based (immune to DOM-rebind misfires) but visually a checkbox
         row. NOTE: shiny::actionButton wraps its content inside
         span.action-label, so the flex layout has to live on that inner
         span -- not on the button itself. */
      .row-toggle {
        width: 100%;
        text-align: left;
        background: white;
        border: none;
        border-top: 1px solid #dee2e6;
        border-radius: 0;
        padding: 0.5rem 0.75rem;
        color: inherit;
      }
      .row-toggle .action-label {
        display: flex !important;
        flex-direction: row;
        flex-wrap: nowrap;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
      }
      .row-toggle .action-label > * { flex-shrink: 0; }
      .row-toggle .action-label > .row-info {
        flex: 1 1 auto;
        min-width: 0;
        overflow: hidden;
      }
      .row-toggle .action-label > .row-info > div {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      /* Force readable text in all interactive states — Bootstrap's .btn
         hover/focus rules would otherwise lighten the title color into
         the nearly-invisible range against our hover background. */
      .row-toggle,
      .row-toggle:hover,
      .row-toggle:focus,
      .row-toggle:active,
      .row-toggle:focus-visible {
        color: #212529 !important;
      }
      .row-toggle .text-muted { color: #6c757d !important; }
      .row-toggle:hover { background: #f0f4f8 !important; }
      .row-toggle.selected { background: #e7f1ff !important; }
      .row-toggle.selected:hover { background: #d9e8fc !important; }
      .row-toggle:focus-visible {
        outline: 2px solid #4e6e8e; outline-offset: -2px;
      }
      /* Same single-row enforcement for the Selected-tab row. */
      .selected-row .row-info {
        flex: 1 1 auto; min-width: 0; overflow: hidden;
      }
      .selected-row .row-info > div {
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }
      .row-check {
        display: inline-block;
        width: 18px;
        height: 18px;
        border: 1px solid #adb5bd;
        border-radius: 0.25rem;
        flex-shrink: 0;
        background: white;
      }
      .row-toggle.selected .row-check {
        background-color: #0d6efd;
        border-color: #0d6efd;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22><path fill=%22none%22 stroke=%22white%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22 stroke-width=%223%22 d=%22M4 8l3 3 6-6%22/></svg>');
        background-position: center;
        background-repeat: no-repeat;
        background-size: 70%;
      }
    "),
    tags$script(HTML("
      Shiny.addCustomMessageHandler('clg_copy', function(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text);
        } else {
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
      });
    "))
  ),
  uiOutput("home_ui")
)

# ---------- Server ----------
server <- function(input, output, session) {
  # ---- reactive state ----
  view             <- reactiveVal("home")            # "home" | "wizard"
  wizard_step      <- reactiveVal(1)                 # 1..4
  editing_guid     <- reactiveVal(NULL)              # NULL = create
  search_results   <- reactiveVal(list())
  preview_html     <- reactiveVal("")
  preview_busy     <- reactiveVal(FALSE)
  all_tags         <- reactiveVal(list())
  collections      <- reactiveVal(list())
  deploy_handle    <- reactiveVal(NULL)
  deploy_progress  <- reactiveVal(NULL)
  staged_dir       <- reactiveVal(NULL)
  select_subtab    <- reactiveVal("results")          # "results" | "selected"
  selected_items   <- reactiveVal(list())             # cache: guid -> item
  collection_meta  <- reactiveVal(list())             # cache: guid -> meta
  meta_queue       <- reactiveVal(character(0))       # guids pending fetch
  is_publishing    <- reactiveVal(FALSE) 

  # Track which per-button observers we've registered so refreshes of
  # collections() / search_results() / selected items don't stack duplicate
  # handlers.
  registered_edit_guids    <- reactiveValues()
  registered_copy_guids    <- reactiveValues()
  registered_result_guids  <- reactiveValues()
  registered_remove_guids  <- reactiveValues()

  wizard_state <- reactiveValues(
    title = "", description = "", intro_markdown = "",
    theme = "minimal", source_type = "manual",
    guids = character(0), source_tag = ""
  )

  # Visitor-scoped API key minted from the Connect Visitor API Key OAuth
  # integration attached to this content. Cached once per session for
  # browse/read calls; refresh_key() is called immediately before publish
  # so the deploy receives a fresh-as-possible key (Connect-minted keys are
  # ephemeral). When no token header is present, this resolves to the
  # publisher's CONNECT_API_KEY — see visitor_api_key() in connect_api.R.
  visitor_key <- NULL
  refresh_key <- function() {
    visitor_key <<- visitor_api_key(session, connect_server, connect_api_key)
    visitor_key
  }
  key <- function() {
    if (is.null(visitor_key)) refresh_key() else visitor_key
  }

  notify <- function(msg, type = "default") {
    showNotification(msg, type = type,
                     duration = if (type == "error") NULL else 5)
  }

  reset_wizard_state <- function() {
    wizard_state$title          <- ""
    wizard_state$description    <- ""
    wizard_state$intro_markdown <- ""
    wizard_state$theme          <- "minimal"
    wizard_state$source_type    <- "manual"
    wizard_state$guids          <- character(0)
    wizard_state$source_tag     <- ""
    is_publishing(FALSE)
    search_results(list())
    preview_html("")
    select_subtab("results")
    selected_items(list())
  }

  # ---- initial loads ----
  observe({
    collections(fetch_my_collections(connect_server, key()))
  })
  observe({
    all_tags(get_tags(connect_server, key()))
  })

  # ---- home view ----
  output$home_ui <- renderUI({
    if (view() == "home") {
      home_view(collections(),
                connect_server = connect_server,
                collection_meta = collection_meta())
    } else NULL    # wizard is rendered into a modal via showModal
  })

  # Enqueue any new collection guids that don't have cached metadata yet.
  observe({
    current <- vapply(collections(),
                      function(c) c$guid %||% "", character(1))
    current <- current[nzchar(current)]
    cached  <- names(collection_meta())
    pending <- meta_queue()
    needed  <- setdiff(current, c(cached, pending))
    if (length(needed) > 0) meta_queue(c(pending, needed))
  })

  # Process the queue one guid at a time. Each fetch downloads the active
  # bundle, parses its collection.json, and caches the source-type +
  # item-count summary for that collection. The home view re-renders as
  # each entry lands.
  observe({
    q <- meta_queue()
    if (length(q) == 0) return()
    g <- q[1]
    # Pop first so a re-fire (e.g. from collections() refresh) won't
    # double-process this guid.
    meta_queue(q[-1])
    bundle <- download_active_bundle(connect_server, key(), g)
    cfg <- if (!is.null(bundle)) extract_collection_json(bundle) else NULL
    parsed <- parse_config(cfg %||% list())
    cache <- collection_meta()
    cache[[g]] <- list(
      source_type = parsed$source_type,
      n_items     = if (identical(parsed$source_type, "manual"))
                      length(parsed$guids) else NA_integer_,
      source_tag  = parsed$source_tag,
      description = parsed$description
    )
    collection_meta(cache)
  })

  observeEvent(input$new_collection, {
    reset_wizard_state()
    editing_guid(NULL)
    wizard_step(1)
    view("wizard")
    show_wizard()
  })

  # Edit buttons in the home list. Register at most one observer per guid
  # so refreshes of collections() do not stack duplicate handlers.
  observe({
    for (coll in collections()) {
      g <- coll$guid
      if (is.null(g) || isTRUE(registered_edit_guids[[g]])) next
      registered_edit_guids[[g]] <- TRUE
      local({
        c_guid <- g
        observeEvent(input[[paste0("edit_", c_guid)]], {
          load_existing(c_guid)
        }, ignoreInit = TRUE)
      })
    }
  })

  # Copy-link buttons. Resolve the share URL on click (uses vanity_url if
  # the content has one, else falls back to /content/<guid>).
  observe({
    for (coll in collections()) {
      g <- coll$guid
      if (is.null(g) || isTRUE(registered_copy_guids[[g]])) next
      registered_copy_guids[[g]] <- TRUE
      local({
        c_guid <- g
        observeEvent(input[[paste0("copy_", c_guid)]], {
          info <- get_content(connect_server, key(), c_guid)
          url <- share_url(connect_server, info %||% list(guid = c_guid))
          session$sendCustomMessage("clg_copy", url)
          notify("Link copied to clipboard.", "message")
        }, ignoreInit = TRUE)
      })
    }
  })

  load_existing <- function(guid) {
    info <- get_content(connect_server, key(), guid)
    bundle_path <- download_active_bundle(connect_server, key(), guid)
    cfg <- if (!is.null(bundle_path)) extract_collection_json(bundle_path) else NULL

    if (is.null(cfg)) {
      reset_wizard_state()
      if (!is.null(info)) {
        wizard_state$title       <- info$title       %||% ""
        wizard_state$description <- info$description %||% ""
      }
      notify("This collection has no saved settings yet. Saving will publish a fresh configuration.",
             type = "warning")
    } else {
      parsed <- parse_config(cfg)
      wizard_state$title          <- parsed$title
      wizard_state$description    <- parsed$description
      wizard_state$intro_markdown <- parsed$intro_markdown
      wizard_state$theme          <- parsed$theme
      wizard_state$source_type    <- parsed$source_type
      wizard_state$guids          <- parsed$guids
      wizard_state$source_tag     <- parsed$source_tag
    }
    editing_guid(guid)
    wizard_step(1)
    view("wizard")
    show_wizard()
  }

  # ---- wizard render ----
  show_wizard <- function() {
    step  <- wizard_step()
    mode  <- if (is.null(editing_guid())) "create" else "edit"
    body  <- step_body_for(step)
    showModal(wizard_modal_dialog(step = step, mode = mode,
                                  state = isolate(reactiveValuesToList(wizard_state)),
                                  body = body,
                                  busy = is_publishing()))
  }

  step_body_for <- function(step) {
    s <- isolate(reactiveValuesToList(wizard_state))
    switch(as.character(step),
      "1" = step_select_ui(state = s,
                           search_query = isolate(input$search_query) %||% "",
                           search_results = search_results(),
                           all_tags = all_tags(),
                           subtab = select_subtab(),
                           selected_items = selected_items(),
                           connect_server = connect_server),
      "2" = step_describe_ui(state = s),
      "3" = step_theme_ui(state = s),
      "4" = step_preview_ui(html_string = preview_html(),
                            source_type = s$source_type,
                            busy = preview_busy(),
                            theme = s$theme)
    )
  }

  # ---- bindings: keep wizard_state in sync with inputs ----
  observeEvent(input$collection_title,       { wizard_state$title          <- input$collection_title       }, ignoreInit = TRUE)
  observeEvent(input$collection_description, { wizard_state$description    <- input$collection_description }, ignoreInit = TRUE)
  observeEvent(input$collection_intro,       { wizard_state$intro_markdown <- input$collection_intro       }, ignoreInit = TRUE)
  # Source-type toggle: two actionButtons act as a segmented control.
  observeEvent(input$source_type_manual, {
    wizard_state$source_type <- "manual"
    show_wizard()
  }, ignoreInit = TRUE)
  observeEvent(input$source_type_tag, {
    wizard_state$source_type <- "tag"
    show_wizard()
  }, ignoreInit = TRUE)
  observeEvent(input$tag_select,             { wizard_state$source_tag     <- input$tag_select %||% ""      }, ignoreInit = TRUE)

  # Sub-tab nav (Search results / Selected) inside Select-content mode
  observeEvent(input$select_subtab_results, {
    select_subtab("results")
    show_wizard()
  }, ignoreInit = TRUE)
  observeEvent(input$select_subtab_selected, {
    # Lazy-fetch details for any selected guids we don't already have cached.
    cache <- selected_items()
    missing <- setdiff(wizard_state$guids, names(cache))
    if (length(missing) > 0) {
      for (g in missing) {
        item <- get_content(connect_server, key(), g)
        if (!is.null(item)) cache[[g]] <- item
      }
      selected_items(cache)
    }
    select_subtab("selected")
    show_wizard()
  }, ignoreInit = TRUE)

  # Theme button clicks
  observe({
    lapply(names(THEME_COLORS), function(id) {
      observeEvent(input[[paste0("theme_", id)]], {
        wizard_state$theme <- id
        show_wizard()  # re-render to update selected state
      }, ignoreInit = TRUE)
    })
  })

  # Debounce the search input so typing doesn't fire a search on every
  # keystroke — that previously caused show_wizard() to re-render the modal
  # mid-typing and drop characters. The reactive only fires 600ms after the
  # last change.
  debounced_search_query <- shiny::debounce(
    reactive(input$search_query), millis = 600
  )

  observeEvent(debounced_search_query(), {
    q <- debounced_search_query()
    if (!is.null(q) && nchar(trimws(q)) > 0) {
      search_results(search_content(connect_server, key(), q))
    } else {
      search_results(list())
    }
    show_wizard()
    # show_wizard() rebuilds the modal, which destroys the #search_query
    # input the user is typing into. Restore focus + cursor-at-end so they
    # can keep typing without re-clicking the field.
    shinyjs::runjs(
      "setTimeout(function () {
         var el = document.getElementById('search_query');
         if (el) {
           el.focus();
           var n = (el.value || '').length;
           try { el.setSelectionRange(n, n); } catch (e) {}
         }
       }, 0);"
    )
  }, ignoreInit = TRUE)

  # select_all is now an actionButton (counter); toggle select/deselect visible results
  observeEvent(input$select_all, {
    results <- search_results()
    all_guids <- vapply(results, function(r) r$guid %||% "", character(1))
    # Toggle: if every visible result is currently selected, deselect them all;
    # otherwise add them all to the selection AND cache their details.
    all_selected <- length(all_guids) > 0 && all(all_guids %in% wizard_state$guids)
    if (all_selected) {
      wizard_state$guids <- setdiff(wizard_state$guids, all_guids)
    } else {
      wizard_state$guids <- unique(c(wizard_state$guids, all_guids))
      cache <- selected_items()
      for (r in results) if (!is.null(r$guid)) cache[[r$guid]] <- r
      selected_items(cache)
    }
    show_wizard()
  }, ignoreInit = TRUE)

  observe({
    for (item in search_results()) {
      g <- item$guid
      if (is.null(g) || isTRUE(registered_result_guids[[g]])) next
      registered_result_guids[[g]] <- TRUE
      local({
        guid <- g
        full <- item   # capture full item details for caching on add
        observeEvent(input[[paste0("toggle_", guid)]], {
          if (guid %in% wizard_state$guids) {
            wizard_state$guids <- setdiff(wizard_state$guids, guid)
          } else {
            wizard_state$guids <- c(wizard_state$guids, guid)
            cache <- selected_items()
            cache[[guid]] <- full
            selected_items(cache)
          }
          # Re-render so the visual checkbox state and selected count update.
          show_wizard()
        }, ignoreInit = TRUE)
      })
    }
  })

  # Remove buttons in the "Selected" subtab
  observe({
    for (g in wizard_state$guids) {
      if (is.null(g) || isTRUE(registered_remove_guids[[g]])) next
      registered_remove_guids[[g]] <- TRUE
      local({
        guid <- g
        observeEvent(input[[paste0("remove_", guid)]], {
          wizard_state$guids <- setdiff(wizard_state$guids, guid)
          cache <- selected_items()
          cache[[guid]] <- NULL
          selected_items(cache)
          show_wizard()
        }, ignoreInit = TRUE)
      })
    }
  })

  # ---- wizard navigation ----
  observeEvent(input$wizard_cancel, {
    removeModal()
    view("home")
    collections(fetch_my_collections(connect_server, key()))
  })

  observeEvent(input$wizard_back, {
    wizard_step(max(1, wizard_step() - 1))
    show_wizard()
  })

  # Tab nav (edit mode): clicking a tab jumps to that step
  observe({
    for (i in 1:4) {
      local({
        target <- i
        observeEvent(input[[paste0("wizard_tab_", target)]], {
          wizard_step(target)
          if (target == 4) {
            preview_busy(TRUE)
            show_wizard()
            refresh_preview()
            show_wizard()
          } else {
            show_wizard()
          }
        }, ignoreInit = TRUE)
      })
    }
  })

  observeEvent(input$wizard_next, {
    valid <- validate_step(wizard_step())
    if (!isTRUE(valid$ok)) { notify(valid$msg, "warning"); return() }
    new_step <- wizard_step() + 1
    wizard_step(new_step)
    if (new_step == 4) {
      # Render the modal in busy state first so the user sees the spinner
      # while we synchronously fetch items and build the preview HTML.
      preview_busy(TRUE)
      show_wizard()
      refresh_preview()  # blocking; flips preview_busy to FALSE on completion
      show_wizard()      # re-render with the rendered preview
    } else {
      show_wizard()
    }
  })

  validate_step <- function(step) {
    s <- reactiveValuesToList(wizard_state)
    if (step == 1) {
      if (identical(s$source_type, "manual") && length(s$guids) == 0) {
        return(list(ok = FALSE, msg = "Select at least one item to continue."))
      }
      if (identical(s$source_type, "tag") && !nzchar(s$source_tag)) {
        return(list(ok = FALSE, msg = "Pick a tag to continue."))
      }
    }
    if (step == 2 && !nzchar(trimws(s$title))) {
      return(list(ok = FALSE, msg = "Title is required."))
    }
    list(ok = TRUE, msg = "")
  }

  refresh_preview <- function() {
    s <- reactiveValuesToList(wizard_state)
    preview_busy(TRUE)
    items <- if (identical(s$source_type, "tag") && nzchar(s$source_tag)) {
      fetch_content_by_tag(connect_server, key(), s$source_tag)
    } else {
      lapply(s$guids, function(g) get_content(connect_server, key(), g))
    }
    items <- Filter(Negate(is.null), items)
    preview_html(build_collection_html(s, items, THEME_COLORS,
                                       connect_server = connect_server))
    preview_busy(FALSE)
  }

  # ---- publish ----
  observeEvent(input$wizard_publish, { trigger_publish() })
  trigger_publish <- function() {
    is_edit <- !is.null(editing_guid())
    if (is_edit) {
      # Validate every step; on first failure, switch to that tab and stop.
      for (step in 1:4) {
        v <- validate_step(step)
        if (!isTRUE(v$ok)) {
          wizard_step(step)
          notify(v$msg, "error")
          show_wizard()
          return()
        }
      }
    }
    # Existing create-flow validation already happened step-by-step.
    # Flip to publishing AFTER validation so a failed validation doesn't
    # leave the button disabled. The show_wizard() repaint is what
    # actually swaps the rendered button to disabled.
    is_publishing(TRUE)
    show_wizard()
    publisher <- current_user(connect_server, key())
    publisher_email <- publisher$email %||% ""
    cfg <- build_config(
      title          = wizard_state$title,
      description    = wizard_state$description,
      intro_markdown = wizard_state$intro_markdown,
      theme          = wizard_state$theme,
      source_type    = wizard_state$source_type,
      guids          = wizard_state$guids,
      tag            = wizard_state$source_tag,
      owner_email    = publisher_email
    )
    staged <- tryCatch(
      stage_bundle("dashboard_template", cfg),
      error = function(e) {
        notify(paste("Bundle staging failed:", e$message), "error")
        is_publishing(FALSE); show_wizard()
        NULL
      }
    )
    if (is.null(staged)) return()
    # Refresh the visitor key right before launching so the callr child gets
    # the freshest-possible key; visitor-minted keys are short-lived and the
    # deploy can run for minutes.
    deploy_key <- refresh_key()
    handle <- tryCatch(
      launch_deploy(staged_dir = staged,
                    app_id = editing_guid(),
                    app_title = cfg$title,
                    connect_server = connect_server,
                    connect_api_key = deploy_key),
      error = function(e) {
        notify(paste("Deploy launch failed:", e$message), "error")
        is_publishing(FALSE); show_wizard()
        NULL
      }
    )
    if (is.null(handle)) return()
    progress_id <- showNotification(
      tags$div(tags$span(class = "spinner-border spinner-border-sm me-2"),
               "Publishing your collection..."),
      type = "message", duration = NULL
    )
    deploy_handle(handle); deploy_progress(progress_id); staged_dir(staged)
  }

  observe({
    handle <- deploy_handle()
    req(handle)
    invalidateLater(2000)
    if (handle$is_alive()) return()

    p <- deploy_progress()
    if (!is.null(p)) removeNotification(p)
    sd <- staged_dir(); if (!is.null(sd) && dir.exists(sd)) unlink(sd, recursive = TRUE)

    if (isTRUE(handle$get_exit_status() == 0)) {
      result <- tryCatch(handle$get_result(), error = function(e) e)
      if (inherits(result, "error")) {
        notify(paste("Publish failed:", conditionMessage(result)), "error")
        is_publishing(FALSE)
        if (view() == "wizard") show_wizard()
      } else {
        # Link to the Connect dashboard for this content (not the standalone
        # rendered URL), so the publisher can adjust metadata, sharing, and
        # scheduling from the post-publish toast.
        #
        # rsconnect's deployment record can carry the integer content ID
        # instead of the GUID, so resolve the GUID explicitly: UPDATE already
        # has it in editing_guid(); CREATE looks it up by name.
        guid <- editing_guid()
        if (is.null(guid)) {
          if (!is.null(result$name) && nzchar(result$name)) {
            info <- get_content_by_name(connect_server, key(), result$name)
            if (!is.null(info) && !is.null(info$guid)) guid <- info$guid
          }
        }
        # Attach the visitor integration so the rendered collection's
        # Shiny session can mint per-viewer API keys. Best-effort — if it
        # fails the publish has still succeeded, and the publisher can
        # attach the integration manually from the Connect UI.
        if (!is.null(guid) && !is.na(guid) && nzchar(guid)) {
          ok <- attach_visitor_integration(
            connect_server  = connect_server,
            connect_api_key = key(),
            content_guid    = guid
          )
          if (!isTRUE(ok)) {
            notify(
              "Collection published, but the visitor-key integration could not be attached automatically. Per-viewer item filtering will fall back to the publisher's view until the integration is attached in Connect.",
              type = "warning"
            )
          }
        }
        base <- sub("/$", "", connect_server)
        url <- if (!is.null(guid) && !is.na(guid) && nzchar(guid)) {
          paste0(base, "/connect/#/apps/", guid)
        } else {
          base
        }
        is_publishing(FALSE)
        showNotification(
          tags$div(tags$p("Your collection is ready!"),
                   tags$a(href = url, target = "_blank",
                          class = "btn btn-sm btn-outline-primary mt-2",
                          "Open Collection")),
          type = "message", duration = 15
        )
        removeModal()
        view("home")
        # Invalidate stale metadata for the just-published collection so the
        # row re-fetches with the new source_type/n_items. New collections
        # (no editing_guid) appear as fresh entries and are queued by the
        # enqueue observer automatically.
        eg <- editing_guid()
        if (!is.null(eg)) {
          cache <- collection_meta()
          cache[[eg]] <- NULL
          collection_meta(cache)
        }
        collections(fetch_my_collections(connect_server, key()))
      }
    } else {
      err <- tryCatch(handle$read_error_lines(), error = function(e) character(0))
      msg <- if (length(err) > 0) paste(tail(err, 6), collapse = "\n")
             else sprintf("Deploy exited with status %s", handle$get_exit_status())
      notify(paste("Publish failed:\n", msg), "error")
      is_publishing(FALSE)
      if (view() == "wizard") show_wizard()
    }
    deploy_handle(NULL); deploy_progress(NULL); staged_dir(NULL)
  })
}

shinyApp(ui, server)
