# Python Shiny App using an Azure OpenAI OAuth Integration

## Overview

A Python Shiny app that uses `chatlas` to create an interactive chat interface that answers questions about the `palmerpenguins` dataset. The app demonstrates the OAuth credential handoff made possible by the Azure OpenAI OAuth integration which gives the shiny app access to an Azure OpenAI resource.

## Setup

### Azure Administrator Setup

An Azure Administrator must first register a new OAuth application in Microsoft Entra ID. For a step by step guide on how to do this see the [admin guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/azure-openai/).

The Azure Administrator then passes the `tenant_id`, `client_id`, and `client_secret` to a Connect Administrator to be used in the configuration of the OAuth integration in Connect.

### Posit Connect Administrator Setup

1.  **Configure OAuth integration in Connect**: Using the information from the Azure Administrator, the Connect Administrator configures an Azure OpenAI OAuth integration. This can either be done from the "System" tab or by using `curl` and the [Connect Server API](https://docs.posit.co/connect/api/#post-/v1/oauth/integrations).

2.  **Publish the Extension**: Publish this application to Posit Connect.

3.  **Configure Environment Variables**: In the "Vars" pane of the content settings,

    Set `DEPLOYMENT_ID`, `API_VERSION`, and `ENDPOINT`, all of which are specific to the Azure OpenAI resource that you want to utilize.

    **Example**

    -   `DEPLOYMENT_ID`: `gpt-4o-mini`
    -   `API_VERSION`: `2023-05-15`
    -   `ENDPOINT`: `https://your-resource-name.openai.azure.com`

## Usage

1.  Open the application in Posit Connect.
2.  Type your questions about the `palmerpenguins` dataset in the chat box.