get_eligible_integrations <- function(client) {
  tryCatch(
    {
      # TODO When https://github.com/posit-dev/connectapi/issues/413 is closed,
      # remove this and use that functionality instead.
      integrations <- client$GET("v1/oauth/integrations")

      integrations_df <- purrr::map_dfr(integrations, function(record) {
        # Extract main fields
        main_fields <- purrr::discard(record, is.list) # Discard list fields like 'config'

        # Extract and combine the config fields with field names and values
        config <- paste(
          purrr::imap_chr(record$config, ~ paste(.y, .x, sep = ": ")),
          collapse = ", "
        )

        # Combine both into a single list
        c(main_fields, config = config)
      })

      print(integrations_df)

      eligible_integrations <- integrations_df |>
        dplyr::filter(
          template == "connect",
          config %in% c("max_role: Admin", "max_role: Publisher")
        )
    },
    error = function(e) {
      data.frame()
    }
  )
}

auto_add_integration <- function(client, integration_guid) {
  print("About to PUT the integration!")

  # TODO When https://github.com/posit-dev/connectapi/issues/414 is implemented,
  # delete this and use that instead.
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
