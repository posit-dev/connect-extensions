# Shiny: Chat with your content

## About this extension

Chat with your content turns a report or data app you have published to Posit
Connect into something you can ask questions about. Pick a piece of static
content from a dropdown, and the app extracts its text, hands it to a Large
Language Model (LLM), and answers your questions about it in a chat panel beside
the rendered page. It opens each document with a short summary and a few
suggested questions, and answers using only the selected content.

It works with static, rendered content: Quarto, R Markdown, and Jupyter
documents, and static HTML.

## How it works

- **Runs as the signed-in viewer.** The app calls the Connect API with the
  viewer's own identity, through a Connect Visitor API Key integration, so each
  person only sees and chats with the content they already have permission to
  open. No admin API key is stored in the app.
- **Answers only from the selected content.** When you choose a document, the app
  renders it in the main panel, converts it to markdown, and sends that markdown
  to the LLM as the only context. A system prompt instructs the model to answer
  from that content alone and to say when it can't.
- **Provider-agnostic.** The LLM connection is built with
  [chatlas](https://posit-dev.github.io/chatlas/), so you can point it at OpenAI,
  Azure OpenAI, Anthropic, Google Gemini, or Anthropic on AWS Bedrock by setting
  environment variables (see [Setup](#setup)).
- **Keeps requests bounded.** Very large pages are truncated before they are sent
  to the model, so a big report won't overflow the model's context window.

## Deploy it

Deploy it straight from the Connect Gallery to get a copy running, then configure
it (below). To run a customized version, get the
[extension source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/chat-with-content),
make your changes, and publish with
[`rsconnect deploy shiny`](https://docs.posit.co/rsconnect-python/) or a
[git-backed deployment](https://docs.posit.co/connect/user/git-backed/). Requires
Connect 2025.04.0 or newer with OAuth Integrations enabled.

## Setup

After deploying, open the content's settings and configure two things.

### 1. Choose an LLM provider

Set the `CHATLAS_CHAT_PROVIDER_MODEL` environment variable to a
`provider/model` string, plus the API key for that provider (set the key as a
secret). Until a provider is configured, the app shows a setup screen. See the
[chatlas documentation](https://posit-dev.github.io/chatlas/reference/ChatAuto.html)
for the full list of providers and arguments.

**OpenAI**

- `CHATLAS_CHAT_PROVIDER_MODEL`: `openai/gpt-4o`
- `OPENAI_API_KEY`: `<your-openai-api-key>`

**Anthropic**

- `CHATLAS_CHAT_PROVIDER_MODEL`: `anthropic/claude-sonnet-4-5-20250929`
- `ANTHROPIC_API_KEY`: `<your-anthropic-api-key>`

**Google Gemini**

- `CHATLAS_CHAT_PROVIDER_MODEL`: `google/gemini-2.0-flash`
- `GOOGLE_API_KEY`: `<your-google-api-key>`

**Azure OpenAI**

Set `CHATLAS_CHAT_PROVIDER_MODEL` to `azure-openai` (no model suffix) and pass the
deployment-specific arguments via `CHATLAS_CHAT_ARGS`:

- `CHATLAS_CHAT_PROVIDER_MODEL`: `azure-openai`
- `AZURE_OPENAI_API_KEY`: `<your-azure-openai-api-key>`
- `CHATLAS_CHAT_ARGS`: `{"deployment_id": "gpt-4.1-mini", "endpoint": "https://{your-resource-name}.openai.azure.com", "api_version": "2025-03-01-preview"}`
  (see [Azure OpenAI API versions](https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation))

**Anthropic on AWS Bedrock**

The app uses the
[botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/credentials.html)
credential chain for AWS. If Connect runs on an EC2 instance with an IAM role that
grants Bedrock access, credentials are detected automatically and no configuration
is needed; the app defaults to the `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
model. To use Bedrock without an IAM role, set:

- `AWS_ACCESS_KEY_ID`: `<your-aws-access-key>`
- `AWS_SECRET_ACCESS_KEY`: `<your-aws-secret-key>` (set as a secret)
- `AWS_REGION`: `<your-aws-region>` (e.g. `us-east-1`)
- `AWS_SESSION_TOKEN`: `<your-session-token>` (optional, for temporary credentials)

### 2. Add a Connect Visitor API Key integration

The app lists and reads content as the signed-in viewer, so it needs a Visitor
API Key integration to call the Connect API with that person's identity. On the
content's **Access** tab, add a **Connect Visitor API Key** integration under
**Integrations**. Until it is added, the app shows the setup screen. If you don't
see one in the list, an administrator must enable it on your Connect server. See
the [OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/).

## Customize it

- **Swap the model or provider** by changing the environment variables above.
- **Change how the assistant behaves** by editing the system prompt in `app.py`
  (for example, to change its tone or the suggested-prompt format).
- **Adjust the context limit** by changing `MAX_CONTEXT_CHARS` in `helpers.py`.

## Learn more

- [chatlas](https://posit-dev.github.io/chatlas/)
- [Shiny for Python](https://shiny.posit.co/py/)
- [Posit Connect OAuth integrations](https://docs.posit.co/connect/user/oauth-integrations/)
