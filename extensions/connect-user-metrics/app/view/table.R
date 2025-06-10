box::use(
  reactable[colDef, reactable],
)

#' @export
reactable2 <- function(df, ...) {
  reactable(
    df, highlight = TRUE, striped = TRUE,
    compact = TRUE, paginationType = "numbers",
    defaultColDef = colDef(align = "left"),
    ...
  )
}
