# R Shiny Translator App using a Vertex AI OAuth Integration
## Overview
An R Shiny app that uses `ellmer` and `mall` to translate text that a user inputs into a variety of languages. The app demonstrates the OAuth credential handoff made possible by the Vertex AI OAuth integration which gives the shiny app access to the model that performs the translation.
## Setup
### Google Administrator Setup
A Google Administrator must first create an OAuth CLient ID. For a step by step guide on how to do this see the [admin guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/google/).
The Google Administrator then passes the `client_id`, and `client_secret` to a Connect Administrator to be used in the configuration of the OAuth integration in Connect.
### Posit Connect Administrator Setup
1.  **Configure OAuth integration in Connect**: Using the information from the Google Administrator, the Connect Administrator configures a Vertex AI OAuth integration. This can either be done from the "System" tab or by using `curl` and the [Connect Server API](https://docs.posit.co/connect/api/#post-/v1/oauth/integrations).
2.  **Publish the Extension**: Publish this application to Posit Connect.
3.  **Configure Environment Variables**: In the "Vars" pane of the content settings,
    Set `LOCATION`, `PROJECT_ID`, and `MODEL`, all of which are specific to the Vertex AI resource that you want to utilize.
    **Example**
    -   `LOCATION`: `us-central1`
    -   `PROJECT_ID`: `my-gcp-project-123`
    -   `MODEL`: `gemini-2.5-flash`
## Usage
1.  Open the application in Posit Connect.
2.  Use the dropdown to select the language that you want to translate your text to
3.  Type your text into the first box and then press "Translate"










