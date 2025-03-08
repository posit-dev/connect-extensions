# Create a list of `Content` objects from the data frame of all content items.
as_content_list <- function(content_df, client) {
  cdf_split <- split(content_df, 1:nrow(content_df))
  purrr::map(cdf_split, function(x) {
    x <- x[, !(names(x) %in% c("owner", "tags"))]
    x <- as.list(x)
    connectapi::Content$new(client, x)
  })
}
