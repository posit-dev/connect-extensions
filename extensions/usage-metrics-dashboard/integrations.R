library(connectapi)
library(purrr)
library(dplyr)

get_eligible_integrations <- function(client) {
  tryCatch(
    {
      integrations <- client$GET("v1/oauth/integrations")

      integrations_df <- map_dfr(integrations, function(record) {
        # Extract main fields
        main_fields <- discard(record, is.list) # Discard list fields like 'config'

        # Extract and combine the config fields with field names and values
        config <- paste(
          imap_chr(record$config, ~ paste(.y, .x, sep = ": ")),
          collapse = ", "
        )

        # Combine both into a single list
        c(main_fields, config = config)
      })

      print(integrations_df)

      eligible_integrations <- integrations_df |>
        filter(
          template == "connect",
          config %in% c("max_role: Admin", "max_role: Publisher")
        ) |>
        arrange(desc(config))
    },
    error = function(e) {
      data.frame()
    }
  )
}

auto_add_integration <- function(client, integration_guid) {
  print("About to PUT the integration!")

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
  print("Done adding the integration")
}
