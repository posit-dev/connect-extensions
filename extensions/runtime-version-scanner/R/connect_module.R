library(shiny)
library(connectapi)


# Full-screen takeover shown when the app can't act as the signed-in viewer
# (no session token, or no "Connect Visitor API Key" integration configured). It
# gives manual setup instructions and never falls back to the publisher's own
# credentials, matching the other Connect extensions.
show_setup_takeover <- function() {
  oauth_docs_url <- "https://docs.posit.co/connect/user/oauth-integrations/"
  insertUI(
    selector = "body",
    where = "beforeEnd",
    ui = div(
      class = "visitor-setup-takeover",
      div(
        class = "card shadow-sm visitor-setup-card",
        div(
          class = "card-body p-4",
          h1("Setup", class = "h5 text-center mb-3"),
          p(
            class = "text-body-secondary",
            HTML(paste0(
              "This app needs a \"Connect Visitor API Key\" integration to list ",
              "your content as the signed-in viewer. In the content settings, on ",
              "the <strong>Access</strong> tab, add the \"Connect Visitor API ",
              "Key\" integration under <strong>Integrations</strong>."
            ))
          ),
          p(
            class = "text-body-secondary mb-0",
            HTML(paste0(
              "For more information, see the ",
              "<a href=\"", oauth_docs_url, "\" target=\"_blank\" ",
              "rel=\"noopener\">OAuth Integrations documentation</a>."
            ))
          )
        )
      )
    )
  )
}

connectVisitorClient <- function(id = ".connect_visitor_client") {
  moduleServer(id, function(input, output, session) {
    tryCatch(
      connect(token = session$request$HTTP_POSIT_CONNECT_USER_SESSION_TOKEN),
      error = function(e) {
        show_setup_takeover()
        NULL
      }
    )
  })
}
