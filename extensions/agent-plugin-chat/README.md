# Python Shiny: Chat with Connect-managed skills

## About this example

A [Shiny for Python](https://shiny.posit.co/py/) chat app whose skills come from **agent plugin marketplaces** that Posit Connect decides a viewer may read.

The point it teaches: the capabilities an agent has are governed by **Connect**, per viewer, rather than by the app or by whoever deployed it.

One deployment serves everyone. There is no need to publish a copy per person.

## How it works

- The chat UI is built with Shiny, and [chatlas](https://posit-dev.github.io/chatlas/) drives the LLM (Anthropic, OpenAI, Google, AWS Bedrock, and others).
- When a viewer opens the app, Connect attaches a short-lived `Posit-Connect-User-Session-Token` to the request.
- The app posts that token to `POST /__api__/v1/agent-plugins/credentials`, authenticated with its own `CONNECT_API_KEY`.
  Both are needed: the key says which content is asking, the token says who is looking at it.
  The token travels in the request body, because Connect deletes an inbound copy of that header before any handler sees it — otherwise a caller could claim to be anyone.
- Connect answers with the viewer's identity, the marketplaces their access lists admit, and a credential for each.
- The app then clones each marketplace **from its own upstream** — Package Manager, GitHub, wherever it lives.
  Connect is not in the clone path.

A marketplace the viewer may not read is absent from that response, so the app never learns its URL and never gets a credential for it.

There is deliberately no fallback to the deploying user's identity. That would hand every viewer the owner's marketplaces, which is the bypass this design exists to prevent.

### How a skill reaches the model

Three ways, and the difference is who chooses:

| Route | Who decides |
| --- | --- |
| `load_skill` tool | the model, when it judges a skill relevant |
| `/<skill-name>` slash command | the person, when they already know which applies |
| Pinned in the sidebar | the publisher of the turn, for the whole conversation |

Slash commands come from [shinychat](https://posit-dev.github.io/shinychat/), the chat widget — not from Connect and not from chatlas. Connect decides *which* skills exist for this viewer; the client decides how they are offered.

## Deploy it

Install it from the Connect Gallery, then configure it (below).
To run a customized version, edit the source and publish with [`rsconnect deploy shiny`](https://docs.posit.co/rsconnect-python/):

```bash
rsconnect deploy shiny extensions/agent-plugin-chat
```

Requires Posit Connect 2026.10.0 or later, with OAuth integrations enabled and `AgentPlugins.Enabled` turned on.

## Setup

After deploying, in the content's settings:

- **Add the Agent Plugins integration.** On the **Runtime** tab, add it under **Integrations**.
  Connect ships it, so it is already there.

  This is the *only* switch that turns agent plugins on for a piece of content; without it the app refuses and says so.
  Adding it allows every marketplace — each marketplace's own access list then decides what a given viewer receives.
  So the app can be enabled here and still show a particular viewer nothing, which is a normal answer rather than a failure.

  The content cannot be public. Connect refuses to add a viewer-scoped integration to content anyone can open, because there is no viewer to name.
  Signed-in users, or a specific list of users and groups, both work.
- **Set an LLM provider and its API key** on the **Runtime** tab, under **Environment Variables**.
  For example, for Anthropic:

  ```
  CHATLAS_CHAT_PROVIDER_MODEL = anthropic/claude-sonnet-4-5-20250929
  ANTHROPIC_API_KEY           = <your Anthropic API key>
  ```

  Other providers follow the same pattern with their own model string and key (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, ...); see the [chatlas `ChatAuto` docs](https://posit-dev.github.io/chatlas/reference/ChatAuto.html) for the full list.

The app's setup screen shows whichever of these is still outstanding, so you can deploy first and configure after.

The provider is checked by actually asking the model once, not by looking at whether a variable is set.
chatlas reports a missing or rejected credential on the first request rather than when the client is built, so a model that is configured but unusable would otherwise only fail once someone had typed a message.
If the model refuses, the setup screen says so and shows what the provider returned.

A successful check is remembered for the life of the content process; a failure is retried, so a rate limit or a momentary network fault does not hide the chat until someone restarts the content.

## Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `CHATLAS_CHAT_PROVIDER_MODEL` | yes | Which LLM to use, for example `anthropic/claude-sonnet-4-5-20250929`. |
| *provider API key* | yes | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and so on, matching the model. |
| `CONNECT_SERVER` | injected | Where to ask for credentials. |
| `CONNECT_API_KEY` | injected | Says which content is asking. Connect provides it when `Applications.DefaultAPIKeyEnv` is enabled. |

The app needs no marketplace names of its own. It is told which marketplaces the viewer may read, so an administrator is free to call them anything.

## Where the plugins come from

An administrator adds marketplaces under **System** › **Agent plugins** and controls who may read each one.
The upstream is any git repository carrying a `marketplace.json` — including an authenticated Posit Package Manager plugins repository, for which Connect exchanges its workload identity for a short-lived token and passes that to the app for the clone.

To try it without a Package Manager, register [posit-dev/skills](https://github.com/posit-dev/skills), a public collection of Posit-maintained skills that needs no credential:

```
https://github.com/posit-dev/skills.git
```

Grant it to one user and not another to see the same deployment offer each of them a different set.

Access is **per marketplace**, not per plugin. Package Manager authorizes whole repositories, so nothing finer can be enforced once the app clones an upstream directly.

## Two things the app has to do for itself

Content reads each upstream as its author published it, so two things this app cannot assume away are handled here:

**Resolving each plugin's declared source.** A plugin's location comes from its entry in the marketplace document, not from a directory named after it. A repository that is itself one plugin declares `"./"` and keeps its skills at the root; both `cloudflare/skills` and `stripe/ai` are that shape. An entry can also name its skills with a `skills` list of paths, each one skill directory or a directory of them. When the entry's source is the repository root, only those paths load, which is how one repository such as `posit-dev/skills` or `anthropics/skills` publishes several plugins from a shared tree. Otherwise they add to the plugin's `skills/` directory, as a `skills` field in the plugin's own `.claude-plugin/plugin.json` does.

**Coping with the upstream's transport.** A shallow clone is what a marketplace consumer wants, but not every host offers one — a repository served as static files over HTTP has no upload-pack to negotiate with. The app tries shallow, then falls back.

### Colliding skill names

Two plugins can carry a skill of the same name, and two marketplaces can carry a plugin of the same name.
The model addresses a skill by a single string, so the app separates them first: it prefers the bare name, falls back to `plugin:skill`, then to `plugin:skill@marketplace`, and says in the sidebar and the log that it had to qualify.

Resolving silently by clone order would make which skill the model gets depend on ordering.
That is the failure mode MCP clients avoid by refusing to register colliding tool names at all.

## The limit it still inherits

**Skills arrive as prompt text.**
Nothing here runs a plugin's hooks or launches its MCP servers.
A plugin's stdio MCP server would be a subprocess under the content account on a shared server.

## Learn more

- [Posit Connect OAuth integrations](https://docs.posit.co/connect/user/oauth-integrations/)
- [chatlas](https://posit-dev.github.io/chatlas/)
- [Shiny for Python chat](https://shiny.posit.co/py/components/display-messages/chat/)
