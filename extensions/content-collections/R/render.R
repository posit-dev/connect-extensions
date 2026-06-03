THEME_COLORS <- list(
  warm    = list(label = "Warm",    bg = "#fffbeb", accent = "#d97706", border = "#fde68a", text = "#92400e"),
  cool    = list(label = "Cool",    bg = "#eff6ff", accent = "#2563eb", border = "#bfdbfe", text = "#1e40af"),
  minimal = list(label = "Minimal", bg = "#fafafa", accent = "#525252", border = "#e5e5e5", text = "#404040"),
  fun     = list(label = "Fun",     bg = "#fdf2f8", accent = "#db2777", border = "#fbcfe8", text = "#9d174d"),
  bold    = list(label = "Bold",    bg = "#eef2ff", accent = "#4338ca", border = "#c7d2fe", text = "#3730a3"),
  earth   = list(label = "Earth",   bg = "#f0fdf4", accent = "#15803d", border = "#bbf7d0", text = "#166534")
)

# Internal helpers
# Returns HTML: <time datetime="ISO">FALLBACK</time>. The fallback text is
# formatted server-side in the server's local TZ; a small JS snippet
# (DATETIME_LOCALIZER_JS, injected in app.R and into the rendered HTML)
# rewrites the visible text in the viewer's browser TZ + locale on load.
# Returning HTML means callers must render it via shiny::HTML() / raw HTML.
.format_datetime <- function(dt) {
  if (is.null(dt) || !nzchar(dt)) return("")
  parsed <- tryCatch(
    as.POSIXct(sub("\\.\\d+", "", dt),
               format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    error = function(e) NA
  )
  if (is.na(parsed)) return("")
  s <- format(parsed, "%m/%d/%y %I:%M%p", tz = "")
  s <- sub("^0(\\d/)",  "\\1",  s)   # leading 0 on month
  s <- sub("/0(\\d/)",  "/\\1", s)   # leading 0 on day
  s <- sub(" 0(\\d:)",  " \\1", s)   # leading 0 on hour
  fallback <- sub("AM$", "am", sub("PM$", "pm", s))
  iso <- format(parsed, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  sprintf('<time datetime="%s">%s</time>',
          htmltools::htmlEscape(iso, attribute = TRUE),
          htmltools::htmlEscape(fallback))
}

# Client-side script that rewrites every <time datetime="..."> in the page
# using the viewer's browser TZ + locale. Injected once at the top level of
# the Shiny UI and once at the top of each rendered Quarto collection HTML.
DATETIME_LOCALIZER_JS <- '
(function () {
  function fmt(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return d.toLocaleString(undefined, {
      year: "2-digit", month: "numeric", day: "numeric",
      hour: "numeric", minute: "2-digit"
    });
  }
  function rewrite(root) {
    var nodes = (root && root.querySelectorAll)
      ? root.querySelectorAll("time[datetime]")
      : document.querySelectorAll("time[datetime]");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var t = fmt(el.getAttribute("datetime"));
      if (t) el.textContent = t;
    }
  }
  function init() {
    rewrite();
    if (window.Shiny) {
      document.addEventListener("shiny:value", function (e) { rewrite(e.target); });
      document.addEventListener("shiny:bound", function (e) { rewrite(e.target); });
    }
    if (window.MutationObserver && document.body) {
      new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
          var added = muts[i].addedNodes;
          for (var j = 0; j < added.length; j++) {
            if (added[j].nodeType === 1) rewrite(added[j]);
          }
        }
      }).observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else
    init();
})();
'

.owner_name <- function(item) {
  owner <- item$owner
  if (is.list(owner)) {
    first <- owner$first_name %||% ""
    last  <- owner$last_name %||% ""
  } else {
    first <- item$owner_first_name %||% ""
    last  <- item$owner_last_name %||% ""
  }
  trimws(paste(first, last))
}

.content_url <- function(connect_server, guid) {
  paste0(sub("/$", "", connect_server %||% ""), "/content/", guid, "/")
}

# Build a data: URI for the content-type icon SVG, so the <img onerror>
# fallback works inside the deployed embed-resources HTML — Quarto's
# inliner only scans `src=` attributes, not JS strings, so a relative
# path inside onerror would not be inlined and the sibling icons/ folder
# may not be served at runtime.
.icon_data_uri <- function(app_mode) {
  rel <- content_icon_path(app_mode)
  candidates <- c(
    rel,                                  # deployed bundle (icons/ sibling)
    file.path("www", rel),                # cwd = configurator/
    file.path("..", "..", "www", rel),    # cwd = configurator/tests/testthat/
    file.path("..", "www", rel)           # cwd = configurator/tests/
  )
  for (p in candidates) {
    if (file.exists(p)) {
      bytes <- readBin(p, "raw", n = file.info(p)$size)
      enc <- base64enc::base64encode(bytes)
      return(paste0("data:image/svg+xml;base64,", enc))
    }
  }
  rel  # last-resort: relative path; works in environments that serve icons/
}

# Connect content descriptions sometimes contain stray HTML (from prior
# tooling, or copy-pasted markup). Strip tags so cards show plain text only.
.strip_html <- function(text) {
  if (is.null(text) || !nzchar(text)) return("")
  # Remove tags and collapse whitespace.
  out <- gsub("<[^>]*>", " ", text)
  out <- gsub("\\s+", " ", out)
  trimws(out)
}

# Render a collection to a single HTML string.
# `items` is a list of lists with at least: guid, title, description,
# app_mode, last_deployed_time, owner (or owner_first/last_name fields).
# `connect_server` is used to build per-item links; pass "" or NULL if unknown.
build_collection_html <- function(config, items, theme_colors,
                                  connect_server = NULL,
                                  include_chrome = TRUE) {
  colors <- theme_colors[[config$theme %||% "minimal"]] %||% theme_colors$minimal

  esc <- htmltools::htmlEscape

  # Style block
  style_html <- sprintf('<style>
body { background-color: %s; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.collection-header { max-width: 960px; margin: 0 auto; padding: 2rem 2rem 0; }
.collection-title { font-size: 1.75rem; font-weight: 700; color: #111; margin: 0; }
.collection-description { margin-top: 0.25rem; color: #666; font-size: 1rem; }
.collection-panel { max-width: 960px; margin: 1.5rem auto; background: white; border-radius: 0.5rem; padding: 1.25rem; border: 1px solid %s; }
.collection-intro { border-left: 4px solid %s; font-size: 0.9rem; line-height: 1.6; }
.collection-intro h1, .collection-intro h2, .collection-intro h3 { margin-top: 0.75rem; margin-bottom: 0.5rem; font-weight: 600; }
.collection-intro p { margin-bottom: 0.5rem; }
.collection-intro a { color: %s; }
.collection-count { font-size: 0.875rem; font-weight: 500; color: #666; margin-bottom: 1rem; }
.collection-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
@media (max-width: 640px) { .collection-grid { grid-template-columns: 1fr; } }
.collection-card { display: flex; flex-direction: column; padding: 1.125rem 1.25rem; background: white; border: 1px solid %s; border-radius: 0.75rem; text-decoration: none; color: #111; transition: box-shadow 0.15s ease, border-color 0.15s ease; }
.collection-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-color: %s; }
.collection-card__header { display: flex; align-items: center; gap: 0.625rem; }
.collection-card__icon { width: 48px; height: 48px; flex-shrink: 0; object-fit: cover; border-radius: 4px; }
.collection-card__title { font-size: 1rem; font-weight: 600; color: %s; }
.collection-card__description { margin-top: 0.75rem; font-size: 0.875rem; color: #444; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; flex: 1; }
.collection-card__meta { margin-top: 0.875rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.8125rem; color: #555; gap: 0.5rem; }
.collection-card__byline { color: #555; }
.collection-card__date { color: #555; white-space: nowrap; }
#quarto-header, #quarto-footer, .quarto-title-block, #title-block-header { display: none !important; }
/* Strip default styling from Quarto cell wrappers so empty cells (from the
   include:false setup chunk and from results:asis output containers) do not
   render as visible empty boxes. */
.cell, .cell-output, .cell-output-stdout, .cell-output-display, .quarto-layout-row {
  margin: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.cell:empty, .cell-output:empty { display: none !important; }
</style>',
    colors$bg, colors$border, colors$accent, colors$accent,
    colors$border, colors$accent, colors$accent)

  parts <- character(0)

  if (include_chrome) {
    parts <- c(parts, style_html)
    parts <- c(parts, sprintf("<script>%s</script>", DATETIME_LOCALIZER_JS))

    # Header
    parts <- c(parts, '<div class="collection-header">')
    parts <- c(parts, sprintf('<h1 class="collection-title">%s</h1>',
                              esc(config$title %||% "")))
    desc <- config$description %||% ""
    if (nzchar(desc)) {
      parts <- c(parts, sprintf('<p class="collection-description">%s</p>',
                                esc(desc)))
    }
    parts <- c(parts, '</div>')

    # Intro panel
    intro <- config$intro_markdown %||% ""
    if (nzchar(intro)) {
      intro_html <- markdown::markdownToHTML(text = intro, fragment.only = TRUE)
      parts <- c(parts, sprintf(
        '<div class="collection-panel collection-intro">%s</div>', intro_html))
    }
  } else {
    # Even when chrome is suppressed, emit the grid-specific CSS so the cards
    # render correctly. The body/header/intro CSS lives only in chrome.
    parts <- c(parts, style_html)
  }

  # Items panel
  parts <- c(parts, '<div class="collection-panel">')
  parts <- c(parts, sprintf('<div class="collection-count">%d item(s)</div>',
                            length(items)))
  parts <- c(parts, '<div class="collection-grid">')

  for (item in items) {
    guid <- item$guid %||% ""
    title <- item$title %||% item$name %||% "Untitled"
    description <- .strip_html(item$description %||% "")
    if (nchar(description) > 120) {
      description <- paste0(substr(description, 1, 120), "...")
    }
    app_mode <- item$app_mode %||% ""
    date <- .format_datetime(item$last_deployed_time)
    owner <- .owner_name(item)
    url <- .content_url(connect_server, guid)
    type <- content_type_label(app_mode)
    icon_uri <- .icon_data_uri(app_mode)
    thumb_src <- if (nzchar(guid) && nzchar(connect_server %||% "")) {
      paste0(sub("/$", "", connect_server), "/content/", guid, "/__thumbnail__")
    } else {
      icon_uri
    }
    byline <- if (nzchar(owner)) paste(type, "·", owner) else type

    parts <- c(parts, sprintf(
      '<a class="collection-card" href="%s" target="_blank">
         <div class="collection-card__header">
           <img class="collection-card__icon" src="%s" alt=""
                onerror="this.onerror=null;this.src=\'%s\';">
           <div class="collection-card__title">%s</div>
         </div>
         <div class="collection-card__description">%s</div>
         <div class="collection-card__meta">
           <span class="collection-card__byline">%s</span>
           <span class="collection-card__date">%s</span>
         </div>
       </a>',
      esc(url), esc(thumb_src), esc(icon_uri), esc(title), esc(description),
      esc(byline), date))  # date is pre-rendered <time> HTML, do not escape
  }

  parts <- c(parts, '</div></div>')
  paste(parts, collapse = "\n")
}

# Render the empty-state panel shown when, after viewer-scoped filtering,
# no items remain visible. If `config$owner_email` is non-empty, includes
# a mailto link with a prefilled subject; otherwise renders a static line.
empty_state_html <- function(config, theme_colors) {
  colors <- theme_colors[[config$theme %||% "minimal"]] %||% theme_colors$minimal
  esc <- htmltools::htmlEscape

  title <- config$title %||% ""
  email <- config$owner_email %||% ""

  cta <- if (nzchar(email)) {
    subject <- utils::URLencode(
      sprintf("Requesting access to collection: %s", title),
      reserved = TRUE
    )
    sprintf(
      '<a class="empty-state-cta" href="mailto:%s?subject=%s">Email the collection owner to request access</a>',
      esc(email, attribute = TRUE), subject
    )
  } else {
    '<p class="empty-state-line">If you think this is a mistake, contact the collection owner.</p>'
  }

  sprintf(
    '<div class="collection-panel empty-state" style="border-color:%s;">
       <p class="empty-state-message">You don&#39;t have access to any of the items in this collection.</p>
       %s
     </div>
     <style>
       .empty-state { text-align:center; padding:2rem; }
       .empty-state-message { font-size:1rem; color:#444; margin-bottom:1rem; }
       .empty-state-cta { display:inline-block; padding:0.5rem 1rem; background:%s; color:white !important; border-radius:0.375rem; text-decoration:none; }
       .empty-state-line { color:#666; }
     </style>',
    colors$border, cta, colors$accent
  )
}
