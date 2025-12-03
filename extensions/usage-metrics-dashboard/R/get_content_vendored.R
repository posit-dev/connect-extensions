get_content_stock_vendored <- function(
  src,
  guid = NULL,
  owner_guid = NULL,
  name = NULL,
  ...,
  .p = NULL
) {
  connectapi:::validate_R6_class(src, "Connect")
  if (connectapi:::compare_connect_version(src$version, "2024.06.0") < 0) {
    include <- "tags,owner"
    content_ptype <- connectapi:::connectapi_ptypes$content[,
      names(connectapi:::connectapi_ptypes$content) != "vanity_url"
    ]
  } else {
    include <- "tags,owner,vanity_url"
    content_ptype <- connectapi:::connectapi_ptypes$content
  }
  res <- src$content(
    guid = guid,
    owner_guid = owner_guid,
    name = name,
    include = include
  )
  if (!is.null(guid)) {
    res <- list(res)
  }
  if (!is.null(.p)) {
    res <- res %>% purrr::keep(.p = .p)
  }
  out <- connectapi:::parse_connectapi_typed(res, content_ptype)
  return(out)
}

get_content_noparse <- function(
  src,
  guid = NULL,
  owner_guid = NULL,
  name = NULL,
  ...,
  .p = NULL
) {
  connectapi:::validate_R6_class(src, "Connect")
  if (connectapi:::compare_connect_version(src$version, "2024.06.0") < 0) {
    include <- "tags,owner"
    content_ptype <- connectapi:::connectapi_ptypes$content[,
      names(connectapi:::connectapi_ptypes$content) != "vanity_url"
    ]
  } else {
    include <- "tags,owner,vanity_url"
    content_ptype <- connectapi:::connectapi_ptypes$content
  }

  # Also vendor the client's content function, just to add parser = NULL to the args.
  src_content <- function(
    guid = NULL,
    owner_guid = NULL,
    name = NULL,
    include = "tags,owner"
  ) {
    if (!is.null(guid)) {
      return(src$GET(connectapi:::v1_url("content", guid), query = list(include = include)))
    }
    query <- list(owner_guid = owner_guid, name = name, include = include)
    path <- connectapi:::v1_url("content")
    src$GET(path, query = query, parser = NULL)
  }

  res <- src_content(
    guid = guid,
    owner_guid = owner_guid,
    name = name,
    include = "owner"
  )
  if (!is.null(guid)) {
    res <- list(res)
  }
  if (!is.null(.p)) {
    res <- res %>% purrr::keep(.p = .p)
  }
  res_text <- httr::content(res, as = "text")
  jsonlite::fromJSON(res_text, flatten = TRUE)
}

