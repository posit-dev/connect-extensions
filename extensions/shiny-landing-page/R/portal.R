# Helpers that turn Connect's tag hierarchy into the page's tabs and sections.
#
# Connect tags form a tree: a top-level tag such as "Departments" can hold
# "Finance" and "Marketing", which can hold tags of their own. The page shows
# one level of that tree as tabs, and groups each tab's content into sections
# by the level below.

# Turn the list from GET /v1/tags into a data frame with one row per tag.
# Top-level tags have no parent_id.
tag_table <- function(tags) {
  data.frame(
    id = vapply(tags, function(tag) as.character(tag$id), character(1)),
    name = vapply(tags, function(tag) tag$name, character(1)),
    parent_id = vapply(tags, function(tag) as.character(tag$parent_id %||% NA), character(1))
  )
}

# The tags directly under `parent_id`, or the top-level tags if it's NA,
# sorted by name.
child_tags <- function(tags, parent_id = NA) {
  is_child <- if (is.na(parent_id)) is.na(tags$parent_id) else tags$parent_id %in% parent_id
  children <- tags[is_child, , drop = FALSE]
  children[order(tolower(children$name)), , drop = FALSE]
}

# The IDs of every tag below `id`, at any depth.
descendant_ids <- function(tags, id) {
  found <- character(0)
  parents <- id
  while (length(parents) > 0) {
    parents <- setdiff(tags$id[tags$parent_id %in% parents], found)
    found <- c(found, parents)
  }
  found
}

# A tag's full path from the top of the tree, such as "Departments/Finance".
tag_path <- function(tags, id) {
  path <- character(0)
  # Stopping after nrow(tags) steps guards against a malformed tree.
  for (i in seq_len(nrow(tags))) {
    row <- match(id, tags$id)
    if (is.na(row)) {
      break
    }
    path <- c(tags$name[[row]], path)
    id <- tags$parent_id[[row]]
  }
  paste(path, collapse = "/")
}

# Find the tag that PARENT_TAG names, by its path ("Departments/Finance") or just
# its name ("Finance"), ignoring case. Tag names needn't be unique, so if the
# name matches several tags, pick the one nearest the top of the tree.
# Returns NA if no tag matches.
find_tag <- function(tags, x) {
  x <- tolower(trimws(x))
  paths <- tolower(vapply(tags$id, function(id) tag_path(tags, id), character(1), USE.NAMES = FALSE))
  matches <- which(paths == x)
  if (length(matches) == 0) {
    matches <- which(tolower(tags$name) == x)
  }
  if (length(matches) == 0) {
    return(NA_character_)
  }
  depth <- lengths(strsplit(paths[matches], "/", fixed = TRUE))
  tags$id[[matches[[which.min(depth)]]]]
}

# A content search query for content tagged with `name` or any tag below it.
# The value is quoted so names with spaces or commas work, escaping
# backslashes and quotes as the search syntax requires.
tag_query <- function(name) {
  escaped <- gsub('"', '\\"', gsub("\\", "\\\\", name, fixed = TRUE), fixed = TRUE)
  sprintf('tag:"%s"', escaped)
}

# Which items carry any of the tags with these IDs.
has_any_tag <- function(items, ids) {
  vapply(items$tag_ids, function(item_tag_ids) any(item_tag_ids %in% ids), logical(1))
}

# Group a tab's items into sections, one for each tag directly under the tab's
# tag that has content, in name order. An item tagged with several of those
# tags appears in each of their sections. Items that fit no section, such as
# those tagged with the tab's own tag, come last, under "Other". If no
# sections have content, there's a single section with no heading.
tab_sections <- function(items, tags, tab_id) {
  children <- child_tags(tags, tab_id)
  placed <- rep(FALSE, nrow(items))
  sections <- list()
  for (i in seq_len(nrow(children))) {
    in_section <- has_any_tag(items, c(children$id[[i]], descendant_ids(tags, children$id[[i]])))
    if (any(in_section)) {
      sections[[length(sections) + 1]] <- list(heading = children$name[[i]], items = items[in_section, , drop = FALSE])
      placed <- placed | in_section
    }
  }
  if (length(sections) == 0) {
    return(list(list(heading = NULL, items = items)))
  }
  if (!all(placed)) {
    sections[[length(sections) + 1]] <- list(heading = "Other", items = items[!placed, , drop = FALSE])
  }
  sections
}
