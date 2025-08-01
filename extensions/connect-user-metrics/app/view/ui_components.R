box::use(
  bslib[card_header],
  shiny[
    HTML,
    a,
    div,
    icon,
    img,
    tags,
  ],
)

# bslib card header
#' @export
card_header_with_content <- function(title, content) {
  card_header(
    tags$div(
      class = "card-header-with-content no-busy-indicator",
      tags$span(tags$h5(tags$b(title))),
      tags$span(content)
    )
  )
}

#' @export
inline_info_text <- function(
  text1 = NULL, value1 = NULL, change1 = NULL,
  text2 = NULL, value2 = NULL, change2 = NULL
) {
  tags$div(
    class = "inline-info-wrapper",
    text1, tags$b(value1), change1,
    HTML("&emsp;"),
    text2, tags$b(value2), change2,
    HTML("&emsp;")
  )
}

#' Creates a hyperlink with the specified label and URL.
#'
#' @param label The text to display for the hyperlink.
#' @param hyperlink The URL or path to link to.
#' @return A string representing the HTML code for the hyperlink.
#'
#' @export
link <- function(label, hyperlink) {
  a(
    class = "link",
    href = hyperlink,
    target = "_blank",
    rel = "noopener noreferrer",
    icon("link"),
    label
  )
}

#' Creates a card element with a hyperlink, image, header, and text.
#'
#' @param href_link The hyperlink for the card.
#' @param img_link The image link for the card.
#' @param card_header The header text for the card.
#' @param card_text The text content for the card.
#'
#' @return A card element with the specified properties.
#'
#' @examples
#' card("https://example.com", "image.jpg", "Card Header", "Card Text")
#' card <- function(href_link, img_link, card_header, card_text) {
#'   # Function implementation goes here
#' }
#'
#' @export
card <- function(href_link, img_link, card_header, card_text) {
  div(
    class = "card-package",
    a(
      class = "card-logo",
      href = href_link,
      target = "_blank",
      rel = "noopener noreferrer",
      img(
        src = img_link,
        alt = card_header
      )
    ),
    div(
      class = "card-heading",
      card_header
    ),
    div(
      class = "card-content",
      card_text
    ),
    a(
      class = "card-link rhino",
      href = href_link,
      target = "_blank",
      rel = "noopener noreferrer",
      "Learn more"
    ),
    a(
      class = "card-link technologies",
      href = "https://go.appsilon.com/rhino-user-metrics-app",
      target = "_blank",
      rel = "noopener noreferrer",
      "More Appsilon Technologies"
    )
  )
}
