# Python Shiny App using an Azure OpenAI OAuth Integration

A Python Shiny app that uses `chatlas` to create an interactive chat interface that answers questions about the `palmerpenguins` dataset. The app demonstrates the OAuth credential handoff made possible by the Azure OpenAI OAuth integration which gives the shiny app access to Azure OpenAI resources.

# Setup

An Azure OpenAI OAuth Integration must be configured by the Posit Connect administrator using application specific fields from the Azure administrator.

# Usage

Deploy the app to Connect.

**Note**: 

Only members of the "Connect" group have been assigned the proper data action role to use the Azure OpenAI `gpt-4o-mini` deployment that this app is set up to interact with. Because of this, the primary purpose of the app is to serve as a blueprint for what utilizing the Azure OpenAI OAuth integration might look like.

To adapt this shiny app to a different azure endpoint and model deployment, the `deployment_id`, `api_version`, and `endpoint` arguments passed to `ChatAzureOpenAI`, must be respecified.