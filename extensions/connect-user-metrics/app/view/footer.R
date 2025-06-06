box::use(
  shiny[
    a,
    div
  ],
)

box::use(
  app/logic/ui_utils[
    brand,
  ],
)

footer_credits <- brand$meta$credits$footer

#' @export
ui <- function() {
  div(
    footer_credits$text,
    a(
      footer_credits$link$label,
      class = "link",
      href =  footer_credits$link$url,
      target = "_blank",
      rel = "noopener noreferrer"
    )
  )
}
