# Helpers that turn the Connect content list into the hub's cards and table.
#
# The same file ships in both content hub extensions, as
# quarto-website/content_hub.R (the static Quarto hub) and
# shiny-content-hub/R/content_hub.R (the per-viewer Shiny hub). Keep the
# copies identical; the Shiny hub's tests cover both.

library(bslib)
library(htmltools)
library(reactable)

# Connect identifies content by its app_mode (plus content_category for static
# content). Viewers think in terms of what they'll get when they open it, so
# collapse the many app modes into a few familiar types. Anything not
# recognized here, including app modes added in future Connect releases, is
# shown as a document.
content_type <- function(app_mode, content_category) {
  vapply(
    seq_along(app_mode),
    function(i) {
      mode <- app_mode[[i]] %|NA|% ""
      category <- content_category[[i]] %|NA|% ""
      if (mode %in% c("api", "python-api", "python-fastapi")) {
        "API"
      } else if (mode == "tensorflow-saved-model") {
        "Model"
      } else if (mode == "static" && category == "plot") {
        "Plot"
      } else if (mode == "static" && category == "pin") {
        "Pin"
      } else if (
        # Every remaining python-* mode is an app framework (Shiny, Dash,
        # Streamlit, Bokeh, Gradio, Panel, ...); APIs were handled above.
        mode %in% c("shiny", "jupyter-voila", "nodejs") || startsWith(mode, "python-")
      ) {
        "Application"
      } else {
        "Document"
      }
    },
    character(1)
  )
}

# Bootstrap Icons (https://icons.getbootstrap.com) names, drawn with
# bsicons::bs_icon(). They're inline SVG in the current text color, so they
# follow the page's theme, including dark mode.
type_icons <- c(
  API = "plug",
  Model = "cpu",
  Plot = "bar-chart-line",
  Pin = "pin-angle",
  Application = "window",
  Document = "file-earmark-text"
)

type_label <- function(type, icon) {
  span(class = "hub-type", bsicons::bs_icon(icon, a11y = "deco"), type)
}

`%|NA|%` <- function(x, default) {
  if (is.null(x) || is.na(x)) default else x
}

owner_name <- function(owner) {
  if (length(owner) == 0) {
    return("")
  }
  full_name <- trimws(paste(owner$first_name %||% "", owner$last_name %||% ""))
  if (nzchar(full_name)) full_name else owner$username %||% ""
}

# Normalize the data frame from connectapi::get_content() into one row per
# item, holding only what the hub displays, newest first.
hub_items <- function(content) {
  # Content that has never been successfully deployed has no bundle, and its
  # link leads to an empty page, so leave it out.
  content <- content[!is.na(content$bundle_id), , drop = FALSE]

  type <- content_type(content$app_mode, content$content_category)
  title <- ifelse(is.na(content$title) | content$title == "", content$name, content$title)
  description <- ifelse(is.na(content$description), "", content$description)
  owner <- vapply(content$owner, owner_name, character(1))
  item_tags <- lapply(content$tags, function(tags) vapply(tags, function(tag) tag$name, character(1)))

  items <- data.frame(
    title = title,
    description = description,
    owner = owner,
    type = type,
    icon = unname(type_icons[type]),
    # dashboard_url opens the item inside Connect's own frame, with its title,
    # info panel, and sharing controls, rather than bare.
    url = content$dashboard_url,
    updated = content$last_deployed_time
  )
  items$tags <- item_tags
  # Tag names aren't unique across the tag hierarchy, so keep the IDs too.
  items$tag_ids <- lapply(content$tags, function(tags) vapply(tags, function(tag) tag$id, character(1)))
  # Lowercased once here so searching stays cheap.
  items$search_text <- tolower(paste(
    title,
    description,
    owner,
    type,
    vapply(item_tags, paste, character(1), collapse = " ")
  ))

  items <- items[order(items$updated, decreasing = TRUE), , drop = FALSE]
  rownames(items) <- NULL
  items
}

# Parse FEATURED_TAGS ("showcase, Onboarding") into lowercased tag names, so
# featured tags match case-insensitively.
parse_tags <- function(x) {
  tags <- trimws(strsplit(x, ",", fixed = TRUE)[[1]])
  tolower(tags[nzchar(tags)])
}

# Content tagged with any featured tag is featured, up to `max` items (the
# most recently updated ones), so a widely used tag can't bury the page in
# cards. If no tags are configured, or nothing visible carries them, show the
# `n` most recently updated items instead so the top of the page is never
# empty.
featured_items <- function(items, featured_tags, n = 6, max = 12) {
  tagged <- vapply(items$tags, function(tags) any(tolower(tags) %in% featured_tags), logical(1))
  if (any(tagged)) {
    list(heading = "Featured", items = utils::head(items[tagged, , drop = FALSE], max))
  } else {
    list(heading = "Recently updated", items = utils::head(items, n))
  }
}

# Keep the items matching a free-text search and type and tag selections.
# Every search term must appear somewhere in the item, in any order, so
# "sales quarterly" finds "Quarterly Sales Report". An empty selection means
# "any".
filter_items <- function(items, search = "", types = NULL, tags = NULL) {
  terms <- strsplit(tolower(trimws(search %||% "")), "\\s+")[[1]]
  terms <- terms[nzchar(terms)]
  keep <- rep(TRUE, nrow(items))
  for (term in terms) {
    keep <- keep & grepl(term, items$search_text, fixed = TRUE)
  }
  if (length(types) > 0) {
    keep <- keep & items$type %in% types
  }
  if (length(tags) > 0) {
    keep <- keep & vapply(items$tags, function(item_tags) any(item_tags %in% tags), logical(1))
  }
  items[keep, , drop = FALSE]
}

# The whole card is the link (the title's stretched-link covers it). Links use
# target="_top" so that, when the hub is viewed inside Connect's dashboard, the
# item replaces the dashboard instead of opening in the hub's iframe.
content_card <- function(item) {
  item_tags <- item$tags[[1]]
  # Drop the day's leading zero: "Mar 1, 2026", not "Mar 01, 2026".
  updated <- sub(" 0", " ", format(item$updated, "%b %d, %Y"), fixed = TRUE)
  card(
    class = "hub-card",
    card_body(
      gap = "0.5rem",
      type_label(item$type, item$icon),
      tags$h3(
        # no-anchor stops Quarto from adding a section link to each title.
        class = "hub-card-title no-anchor",
        tags$a(class = "stretched-link", href = item$url, target = "_top", item$title)
      ),
      if (nzchar(item$description)) {
        tags$p(class = "hub-card-description", item$description)
      },
      # mt-auto pins the tags and byline to the bottom of the card, so they
      # line up across a row of cards with different description lengths.
      div(
        class = "mt-auto",
        if (length(item_tags) > 0) {
          div(class = "hub-tags", lapply(item_tags, function(tag) span(class = "hub-tag", tag)))
        },
        tags$p(
          class = "hub-card-byline",
          paste(Filter(nzchar, c(item$owner, paste("Updated", updated))), collapse = " · ")
        )
      )
    )
  )
}

card_grid <- function(items) {
  cards <- lapply(seq_len(nrow(items)), function(i) content_card(items[i, , drop = FALSE]))
  layout_column_wrap(
    width = "16rem",
    fill = FALSE,
    heights_equal = "row",
    class = "hub-grid",
    # auto-fill rather than layout_column_wrap()'s auto-fit keeps a column's
    # width when there are fewer cards than columns, so one card doesn't
    # stretch across the page. This comes after the style the function sets,
    # so it wins.
    style = "grid-template-columns: repeat(auto-fill, minmax(min(16rem, 100%), 1fr))",
    !!!cards
  )
}

# A sortable table of items. `searchable` adds reactable's own search box and
# per-column filters, for the static hub, which has no other way to filter.
content_table <- function(items, searchable = FALSE) {
  # Build the linked titles and icon labels as HTML strings up front.
  # Returning htmltools tags from a cell function is much slower: reactable
  # converts each one, which takes seconds for a few thousand rows. The data
  # columns keep the plain values, so sorting and filtering use those.
  title_html <- sprintf(
    '<a href="%s" target="_top">%s</a>',
    htmlEscape(items$url, attribute = TRUE),
    htmlEscape(items$title)
  )
  icon_svgs <- vapply(
    unique(items$icon),
    function(icon) as.character(bsicons::bs_icon(icon, a11y = "deco")),
    character(1)
  )
  type_html <- sprintf(
    '<span class="hub-type">%s%s</span>',
    icon_svgs[items$icon],
    htmlEscape(items$type)
  )

  data <- data.frame(
    title = items$title,
    type = items$type,
    owner = items$owner,
    updated = items$updated,
    tags = vapply(items$tags, paste, character(1), collapse = ", ")
  )
  reactable(
    data,
    searchable = searchable,
    filterable = searchable,
    defaultPageSize = 20,
    defaultSorted = list(updated = "desc"),
    highlight = TRUE,
    # Inherit colors from the page so the table follows its light or dark
    # theme instead of reactable's fixed white.
    theme = reactableTheme(
      color = "inherit",
      backgroundColor = "transparent",
      borderColor = "rgba(127, 127, 127, 0.25)",
      highlightColor = "rgba(127, 127, 127, 0.1)",
      inputStyle = list(backgroundColor = "transparent", color = "inherit"),
      pageButtonStyle = list(color = "inherit")
    ),
    columns = list(
      title = colDef(
        name = "Title",
        minWidth = 200,
        html = TRUE,
        cell = function(value, index) title_html[[index]]
      ),
      type = colDef(
        name = "Type",
        html = TRUE,
        cell = function(value, index) type_html[[index]]
      ),
      owner = colDef(name = "Owner"),
      updated = colDef(name = "Updated", format = colFormat(date = TRUE)),
      tags = colDef(name = "Tags")
    )
  )
}
