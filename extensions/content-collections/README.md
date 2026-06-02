# Content Collection Configurator

A Shiny app for creating and editing curated content collections on Posit Connect — no server changes required.

Publishers use the configurator to choose Connect content (or a tag), set a title, description, intro markdown, and theme. Each collection is itself a Connect content item — a Quarto document — published by the configurator using the `rsconnect` package.

**Features:**

- Create new collections or edit existing ones in place
- Search and select Connect content, or pick a tag for dynamic resolution
- Set title, description, intro markdown, and a visual theme
- Settings travel with the published bundle (`collection.json`); no pins
- Async publish with progress + success/error toasts
- Per-viewer filtering: each collection mints a viewer-scoped API key at render time and only shows content the viewer is allowed to access

The Quarto template ships inside the configurator at `dashboard_template/` and is bundled into each published collection.

## Requirements

- Posit Connect 2025.01 or later (required for Visitor API Key OAuth integrations)
- R 4.5 or later
- Connect features:
  - **API Publishing** — for the configurator to publish collections via `rsconnect::deployApp`
  - **OAuth Integrations** — for visitor-scoped API keys
  - **Current User Execution** — so each collection renders in the viewer's session

## Setup

### 1. Deploy the configurator

Deploy this directory to Connect as a Shiny app. The configurator uses the auto-injected `CONNECT_SERVER` and `CONNECT_API_KEY` environment variables.

### 2. Attach a Visitor API Key integration

So that each collection is published as the user clicking **Save & Publish** — rather than as the publisher of the configurator — associate a **Visitor API Key** OAuth integration with the deployed configurator content.

1. As a Connect admin, create an OAuth integration of type **Posit Connect API** (Visitor API Key). Pick the maximum role (Viewer / Publisher / Administrator) you want minted keys to carry.
2. On the deployed configurator's **Access** sidebar, add the integration.
3. (Optional) If more than one integration is attached, set the `CONNECT_VISITOR_INTEGRATION_GUID` environment variable on the configurator content to the GUID of the one to use.

If no integration is attached (e.g. local development), the configurator falls back to the publisher's `CONNECT_API_KEY` — useful for testing but means publishes will be attributed to the publisher.

See: <https://docs.posit.co/connect/user/oauth-integrations/>.

> The configurator re-uses the same integration when publishing each new collection — you do **not** need to attach it manually to every collection. If you want collections to use a different integration than the configurator itself, set `CONNECT_VISITOR_INTEGRATION_GUID` on the configurator's content environment to the GUID of the integration to use for published collections.

### 3. Create or edit a collection

1. Open the configurator.
2. Choose **Create new collection...** (or pick an existing collection from the dropdown).
3. Search and select content (or pick a tag).
4. Set title, description, intro, theme.
5. Click **Save & Publish**. The configurator stages a bundle, deploys via `rsconnect`, and shows a progress toast.
6. When the toast switches to "Your collection is ready!", click the link to open the new (or updated) Connect content item.

## How it works

The configurator copies `dashboard_template/` into a tempdir, writes a generated `collection.json` next to `index.qmd`, and calls `rsconnect::deployApp()` in a `callr` background process. On CREATE, it sets the Connect content `name` to `__content-collection__-<uuid>` (used as the discovery marker). On UPDATE, it passes `appId = <guid>` so Connect updates the same content item — preserving its URL, ACLs, schedule, and thumbnail.

The Quarto template at render time reads `collection.json` from the bundle and resolves content metadata (and tag-based queries) via the Connect API.

Each published collection itself runs as a Shiny-backed Quarto document. At render time, the collection's Shiny session mints a viewer-scoped API key (via the same Visitor API Key OAuth integration mechanism the configurator uses) and fetches the collection's items through Connect's content API. Items the viewer cannot access are filtered out before the page is rendered — the viewer never sees a card for content they lack permission on. The configurator attaches the integration to each new collection automatically at publish time; no manual setup is required for individual collections.
