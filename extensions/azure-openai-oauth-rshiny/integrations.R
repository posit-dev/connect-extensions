library(connectapi)
library(purrr)

get_eligible_integrations <- function(client) {
  tryCatch(
    {

      integrations <- client$GET("v1/oauth/integrations")

      integrations_df <- purrr::map(integrations, \(record) {
        # Extract main fields
        main_fields <- purrr::discard(record, is.list) 
        data.frame(main_fields)
      }) |>
        purrr::list_rbind()

      eligible_integrations <- integrations_df |>
        filter(
          template == "azure-openai"
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