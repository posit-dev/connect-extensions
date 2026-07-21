# Chat with Content

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

After deploying, in the content's settings:

- **Choose an LLM** by setting `CHATLAS_CHAT_PROVIDER_MODEL` (for example
  `openai/gpt-4o`) plus the matching API key (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, ...) on the **Advanced** tab, under
  **Environment Variables**. See the
  [chatlas `ChatAuto` docs](https://posit-dev.github.io/chatlas/reference/ChatAuto.html)
  for provider/model strings. On AWS Bedrock with an instance role, credentials
  are detected automatically and no vars are needed. (The older
  `CHATLAS_CHAT_PROVIDER` and `CHATLAS_CHAT_ARGS` still work but are deprecated.)
- **Add a Visitor API Key integration** so the app lists and reads content as the
  viewer: on the **Access** tab, add a "Connect Visitor API Key" integration under
  **Integrations**. If it isn't listed, an administrator must first create a
  **Connect API** integration on your server. See the
  [OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/).

Until an LLM provider and the integration are configured, the app shows a setup
screen with just the step(s) still missing.

## Customize it

- **Swap the model or provider** by changing the environment variables above.
- **Change how the assistant behaves** by editing the system prompt in `app.py`
  (for example, to change its tone or the suggested-prompt format).
- **Adjust the context limit** by changing `MAX_CONTEXT_CHARS` in `helpers.py`.

## Learn more

- [chatlas](https://posit-dev.github.io/chatlas/)
- [Shiny for Python](https://shiny.posit.co/py/)
- [Posit Connect OAuth integrations](https://docs.posit.co/connect/user/oauth-integrations/)
