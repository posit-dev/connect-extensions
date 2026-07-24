# Publisher Command Center

## About this extension

Publisher Command Center gives publishers one place to manage the content they
have deployed to Posit Connect. It lists every app and dashboard you own or
collaborate on, and for each one shows its metadata, author, collaborators, and
source-version history. From the same screen you can rename or lock content,
delete it, and see and stop the processes it currently has running.

## How it works

- **Runs as the signed-in viewer.** The app calls the Connect API with the
  viewer's own identity, through a Connect Visitor API Key integration, so each
  person only sees and manages the content they already have access to. No admin
  API key is stored in the app, and the home screen shows whose identity it is
  acting as.
- **One list, per-item detail.** The home page lists the content you own or edit,
  with each item's running-process count and dates. Opening an item shows its
  rendered preview alongside its running processes, author, collaborators, and
  source versions.
- **Manage in place.** Rename, lock/unlock, or delete content, and stop a running
  process, all as the viewer, using their Connect permissions.

## Deploy it

Deploy it straight from the Connect Gallery to get a copy running, then configure
it (below). To run a customized version, get the
[extension source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/publisher-command-center),
make your changes, and publish with
[`rsconnect deploy fastapi`](https://docs.posit.co/rsconnect-python/) or a
[git-backed deployment](https://docs.posit.co/connect/user/git-backed/). Requires
Connect 2025.04.0 or newer with API Publishing and OAuth Integrations enabled.

## Setup

The app acts as the signed-in viewer, so it needs a Visitor API Key integration
to call the Connect API with that person's identity.

After deploying, open the content's settings and, on the **Access** tab, add a
**Connect Visitor API Key** integration under **Integrations**. Until it is added,
the app shows a setup screen with these instructions. If the integration is not
listed, an administrator must first create a **Connect API** integration on your
server, with its **Max Role** set to Administrator or Publisher (Viewer will not
work, since the app manages content on the viewer's behalf). See the
[OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/)
and the
[Connect API section of the Admin Guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/).

## Customize it

- **Change the columns or actions** shown for each item in the Mithril components
  under `src/`.
- **Adjust the backend behavior** (which content is listed, the API routes) in
  `app.py`.

## Learn more

- [Posit Connect OAuth integrations](https://docs.posit.co/connect/user/oauth-integrations/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Mithril.js](https://mithril.js.org/)
