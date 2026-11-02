COLLECTION_NAME_MARKER <- "__content-collection__"

build_config <- function(title, description, intro_markdown, theme,
                         source_type, guids, tag, owner_email = "") {
  cfg <- list(
    title = title %||% "",
    description = description %||% "",
    intro_markdown = intro_markdown %||% "",
    theme = theme %||% "minimal",
    source_type = source_type %||% "manual",
    owner_email = owner_email %||% ""
  )
  if (identical(source_type, "tag")) {
    cfg$source_tag <- tag %||% ""
  } else {
    cfg$guids <- as.character(guids %||% character(0))
  }
  cfg
}

parse_config <- function(cfg) {
  cfg <- cfg %||% list()
  list(
    title          = cfg$title %||% "",
    description    = cfg$description %||% "",
    intro_markdown = cfg$intro_markdown %||% "",
    theme          = cfg$theme %||% "minimal",
    source_type    = cfg$source_type %||% "manual",
    source_tag     = cfg$source_tag %||% "",
    guids          = as.character(unlist(cfg$guids %||% character(0))),
    owner_email    = cfg$owner_email %||% ""
  )
}

make_collection_name <- function() {
  paste0(COLLECTION_NAME_MARKER, "-", uuid::UUIDgenerate())
}

# Null-coalescing operator. Treats both NULL and a length-1 NA as "missing"
# so config values from JSON or partial Connect API responses fall back to
# defaults consistently.
`%||%` <- function(a, b) if (is.null(a) || (length(a) == 1 && is.na(a))) b else a
