library(shiny)
library(connectapi)
library(purrr)
library(dplyr)
library(shinyjs)


connectVisitorClient <- function(
  id = ".connect_visitor_client",
  publisher_client = connect()
) {
  moduleServer(id, function(input, output, session) {
    selected_integration_guid <- reactiveVal(NULL)

    client <- NULL
    tryCatch(
      {
        client <- connect(
          token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN
        )
      },
      error = function(e) {
        eligible_integrations <- get_eligible_integrations(publisher_client)
        selected_integration <- eligible_integrations %>%
          arrange(config) %>%
          slice_head(n = 1)
        selected_integration_guid(selected_integration$guid)

        if (nrow(selected_integration) == 1) {
          message <- paste0(
            "This content uses a <strong>Visitor API Key</strong> ",
            "integration to show users the content they have access to. ",
            "A compatible integration is already available; use it below.",
            "<br><br>",
            "For more information, see ",
            "<a href='https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key' ",
            "target='_blank'>documentation on Visitor API Key integrations</a>."
          )
        } else if (nrow(selected_integration) == 0) {
          integration_settings_url <- publisher_client$server_url(
            connectapi:::unversioned_url(
              "connect",
              "#",
              "system",
              "integrations"
            )
          )
          message <- paste0(
            "This content needs permission to ",
            " show users the content they have access to.",
            "<br><br>",
            "To allow this, an Administrator must configure a ",
            "<strong>Connect API</strong> integration on the ",
            "<strong><a href='",
            integration_settings_url,
            "' target='_blank'>Integration Settings</a></strong> page. ",
            "<br><br>",
            "On that page, select <strong>'+ Add Integration'</strong>. ",
            "In the 'Select Integration' dropdown, choose <strong>'Connect API'</strong>. ",
            "The 'Max Role' field must be set to <strong>'Administrator'</strong> ",
            "or <strong>'Publisher'</strong>; 'Viewer' will not work. ",
            "<br><br>",
            "See the <a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/' ",
            "target='_blank'>Connect API section of the Admin Guide</a> for more detailed setup instructions."
          )
        }

        footer <- if (nrow(selected_integration) == 1) {
          button_label <- HTML(paste0(
            "Use the ",
            "<strong>'",
            selected_integration$name,
            "'</strong> ",
            "Integration"
          ))
          actionButton(
            inputId = session$ns("auto_add_integration"),
            label = button_label,
            icon = icon("plus"),
            class = "btn btn-primary"
          )
        } else {
          NULL
        }

        showModal(
          modalDialog(
            footer = footer,
            HTML(message)
          )
        )
      }
    )

    # “Use the ‘…’ Integration” button logic
    observeEvent(input$auto_add_integration, {
      auto_add_integration(publisher_client, selected_integration_guid())
      runjs("window.top.location.reload(true);")
    })

    return(client)
  })
}

# ----

get_eligible_integrations <- function(client) {
  tryCatch(
    {
      integrations <- client$GET("v1/oauth/integrations")
      map_dfr(integrations, function(record) {
        main_fields <- discard(record, is.list)
        config <- paste(
          imap_chr(record$config, ~ paste(.y, .x, sep = ": ")),
          collapse = ", "
        )
        c(main_fields, config = config)
      }) %>%
        filter(
          template == "connect",
          config %in% c("max_role: Admin", "max_role: Publisher")
        )
    },
    error = function(e) {
      tibble() # return empty if the GET fails
    }
  )
}

auto_add_integration <- function(client, integration_guid) {
  client$PUT(
    connectapi:::v1_url(
      "content",
      Sys.getenv("CONNECT_CONTENT_GUID"),
      "oauth",
      "integrations",
      "associations"
    ),
    body = list(list(oauth_integration_guid = integration_guid))
  )
}
