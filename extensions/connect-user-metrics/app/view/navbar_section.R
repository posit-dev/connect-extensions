# The application header.
# Includes branding and navigation
box::use(
  imola[flexPanel],
  shiny[
    a,
    h1,
    img,
    moduleServer,
    NS
  ],
)

box::use(
  app/logic/ui_utils[
    brand,
    breakpoints,
    is_credits_enabled
  ],
  app/logic/utils[
    create_image_path,
  ],
)

if (is_credits_enabled) {
  box::use(
    app/view/about_section,
  )
}

homepage_link <- brand$meta$credits$about$references$homepage$link

app_title_header <- h1(
  class = "title",
  brand$meta$app_title
)

navbar_logo <- a(
  class = "logo-link",
  href = if (is_credits_enabled) homepage_link,
  target = "_blank",
  rel = "noopener noreferrer",
  img(
    class = "logo",
    src = create_image_path(brand$logo),
    height = "40px" # !!!
  )
)

navbar_cta <- a(
  "Let's Talk",
  class = "btn-cta",
  href = paste0(homepage_link, "/#contact"),
  target = "_blank",
  rel = "noopener noreferrer"
)

#' @export
ui <- function(id) {
  ns <- NS(id)

  flexPanel(
    id = "app_header",
    class = "app-header",
    breakpoint_system = breakpoints,
    align_items = "center",
    justify_content = "space-between",
    gap = "24px",
    height = "40px",
    navbar_logo,
    app_title_header,
    # The navigation
    flexPanel(
      id = "navigation",
      class = "navigation",
      breakpoint_system = breakpoints,
      align_items = "center",
      direction = list(
        default = "column",
        l = "row"
      ),
      gap = "10px",
      onclick = "App.handleNavbar(event);"
    ),

    # The info icon
    if (is_credits_enabled) about_section$ui(ns("about")),

    # The call to action button
    if (is_credits_enabled) navbar_cta
  )
}

#' @export
server <- function(id) {
  moduleServer(id, function(input, output, session) {
    if (is_credits_enabled) {
      about_section$server("about")
    }
  })
}
