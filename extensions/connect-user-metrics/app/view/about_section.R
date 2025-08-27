box::use(
  htmltools[
    h4,
  ],
  shiny,
)

box::use(
  app/logic/ui_utils[
    brand
  ],
  app/logic/utils[
    create_image_path
  ],
  app/view/ui_components[
    card,
  ],
)

about_credits <- brand$meta$credits$about

about_section <- shiny$div(
  class = "brand-section",
  shiny$div(
    class = "brand-summary",
    shiny$markdown("
Posit Connect User Metrics makes it easy to monitor **application adoption**,
track **user engagement** and access detailed **usage analytics**
for all your Shiny applications deployed on Posit Connect.
Some key features:

- **Time-based analysis**: View data by day, week, or month across custom time periods
- **Flexible grouping**: Combine metrics by application, user, and date for different perspectives
- **Interactive charts**: Visualize session counts and unique users with dynamic filtering
- **Smart filtering**: Set minimum session duration and filter by specific apps or users
- **Data export**: Download raw and aggregated data as CSV files for further analysis
")
  )
)

tech_section <- shiny$div(
  class = "tech-section",
  h4(class = "tech-heading", "Powered by"),
  lapply(
    about_credits$powered_by,
    function(x) {
      card(
        href_link = x$link,
        img_link = create_image_path(x$img_name),
        card_header = x$name,
        card_text = x$desc
      )
    }
  )
)

brand_section <- shiny$div(
  class = "brand-section",
  shiny$a(
    class = "brand-logo",
    href = about_credits$references$homepage$link,
    target = "_blank",
    rel = "noopener noreferrer",
    shiny$img(
      src = create_image_path(brand$logo),
      alt = "Appsilon"
    )
  ),
  shiny$p(
    class = "brand-summary",
    shiny$span(
      about_credits$summary,
      shiny$a(
        "Learn more about Appsilon",
        href = about_credits$references$homepage$link,
        target = "_blank",
        rel = "noopener noreferrer",
        class = "brand-link"
      )
    )
  )
)

#' @export
ui <- function(id) {
  ns <- shiny$NS(id)
  shiny$div(
    class = "info-btns",
    shiny$actionButton(
      inputId = ns("open_about_modal"),
      class = "info-btn",
      label = "",
      icon = shiny$icon("info-circle")
    )
  )
}

#' @export
server <- function(id) {
  shiny$moduleServer(id, function(input, output, session) {
    ns <- session$ns

    shiny$observeEvent(
      input$open_about_modal,
      ignoreNULL = TRUE,
      {
        shiny$showModal(
          shiny$modalDialog(
            easyClose = TRUE,
            title = brand$meta$app_title,
            size = "xl",
            h4(class = "brand-heading", "About this app"),
            about_section,
            tech_section,
            brand_section
          )
        )
      }
    )
  })
}
