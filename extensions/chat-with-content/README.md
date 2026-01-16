# Chat with Content Extension

The "Chat with Content" extension for Posit Connect provides a way to interact with and query your static content using a chat interface powered by a Large Language Model (LLM).

## Overview

This Shiny application allows users to select a piece of static content (such as static R Markdown, Quarto, or Jupyter Notebook documents) deployed on Posit Connect and ask questions about it. The application extracts the content from the selected document, provides it as context to an LLM, and displays the answers in a chat window.

Key features:
- Lists available static content from Connect for the user to choose from.
- Displays the selected content in an iframe.
- Provides a chat interface to ask questions about the content.
- Uses an LLM to generate answers based *only* on the provided content.
- Suggests relevant questions to ask about the content.

## Setup

### Administrator Setup

As a Posit Connect administrator, you need to configure the environment for this extension to run correctly.

1.  **Publish the Extension**: Publish this application to Posit Connect.

2.  **Configure Environment Variables**: In the "Vars" pane of the content settings, you need to set environment variables to configure the LLM provider. This extension uses the `chatlas` library, which supports various LLM providers like OpenAI, Google Gemini, and Anthropic on AWS Bedrock.

    Set `CHATLAS_CHAT_PROVIDER_MODEL` to specify the provider and model in the format `provider/model`. You also need to provide the API key for the chosen service.

    **Example for OpenAI:**

    -   `CHATLAS_CHAT_PROVIDER_MODEL`: `openai/gpt-4o`
    -   `OPENAI_API_KEY`: `<your-openai-api-key>` (Set this as a secret)

    **Example for Google Gemini:**

    -   `CHATLAS_CHAT_PROVIDER_MODEL`: `google/gemini-1.5-flash`
    -   `GOOGLE_API_KEY`: `<your-google-api-key>` (Set this as a secret)

    **Example for Anthropic:**

    -   `CHATLAS_CHAT_PROVIDER_MODEL`: `anthropic/claude-sonnet-4-20250514`
    -   `ANTHROPIC_API_KEY`: `<your-anthropic-api-key>` (Set this as a secret)

    **Example for Anthropic on AWS Bedrock:**

    The application uses the [botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/credentials.html) credential chain for AWS authentication. If the Connect server is running on an EC2 instance with an IAM role that grants access to Bedrock, credentials are automatically detected and no configuration is needed. In this case, the application uses the `us.anthropic.claude-sonnet-4-20250514-v1:0` model by default.

    To use Bedrock without an IAM role, set the standard AWS environment variables in the "Vars" pane:

    -   `AWS_ACCESS_KEY_ID`: `<your-aws-access-key>`
    -   `AWS_SECRET_ACCESS_KEY`: `<your-aws-secret-key>` (Set this as a secret)
    -   `AWS_REGION`: `<your-aws-region>` (e.g., `us-east-1`)
    -   `AWS_SESSION_TOKEN`: `<your-session-token>` (Optional, for temporary credentials)

    For more details on supported providers and their arguments, see the [Chatlas documentation](https://posit-dev.github.io/chatlas/reference/ChatAuto.html).

3.  **Enable Visitor API Key Integration**: This extension requires access to the Connect API on behalf of the visiting user to list their available content. In the "Access" pane of the content settings, add a "Connect Visitor API Key" integration.

### User Setup

Once the administrator has configured the extension, users can start using it. There is no specific setup required for end-users.

## Usage

1.  Open the "Chat with Content" application in Posit Connect.
2.  Use the dropdown menu to select a piece of content you want to chat with. The list shows static content you have access to.
3.  The selected content will be displayed in the main panel.
4.  The chat panel on the left will show a summary of the content and suggest some questions you can ask.
5.  Type your questions about the content in the chat input box and press enter. The assistant will answer based on the information available in the document.
