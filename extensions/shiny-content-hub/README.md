# R Shiny: Content Hub

## About this extension

A content hub for your Posit Connect server that's personal to each viewer:
one page where people can browse, search, and filter the reports, apps, APIs,
and other content they have access to. Featured content appears at the top.
Below it is the full list, which viewers can search by title, description,
owner, or tag, filter by type and tag, and show as cards or a table.

Each viewer sees only the content they can open. The app lists content with
the viewer's own Connect permissions, through a Connect API integration, rather
than with a shared publisher API key. That makes it safe to share the hub with
everyone on the server: nobody sees the titles of content they can't access.

The hub is for anyone who wants a friendlier way into Connect than the content
list in the dashboard: a front door for a team or a whole organization, or a
quick way for each person to find what's been published for them.

If everyone should see the same list, or you'd rather not run an app, use the
[Quarto: Content Hub](https://github.com/posit-dev/connect-extensions/tree/main/extensions/quarto-website)
extension instead. It's a static page that lists what the publisher can see.

## Requirements

- Posit Connect 2025.04.0 or newer, with OAuth integrations enabled.
- A **Connect API** integration, created by a Connect administrator. Any
  **Max Role** works; viewers never get more access than their own role
  allows. See the
  [Connect API integration guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/).

## Setup

1. Deploy the hub from the Connect Gallery.
2. In the hub's settings, on the **Runtime** tab (**Access** before Connect
   2026.08.0), add the Connect API integration under **Integrations**.
3. Share the hub with the people who should use it. Each viewer needs a
   Connect account and must be logged in.

Until the integration is added, the hub shows a message explaining how to add
it instead of a content list.

Optionally, choose which content to feature:

1. Tag the content you want to feature in Connect, for example with a
   `showcase` tag.
2. In the hub's settings, on the **Runtime** tab (**Advanced** before Connect
   2026.08.0), under **Environment Variables**, set `FEATURED_TAGS` to the tag
   name. To feature several tags, separate them with commas
   (`showcase, onboarding`). Tag names are not case-sensitive.

The hub features up to 12 tagged items, the most recently updated ones.
Without `FEATURED_TAGS`, it features each viewer's six most recently updated
items instead. It does the same if none of the featured content is
visible to the viewer, so the top of the page is never empty.

## Use it

- Select a card or a title in the table to open that item in Connect.
- Type in **Search** to narrow the list. Each word you enter must appear
  somewhere in the item's title, description, owner, type, or tags, in any
  order.
- Use **Type** and **Tag** to filter the list, and **View** to switch between
  cards and a sortable table. The card view shows the 30 most recently
  updated matches; the table shows them all.

The list is fetched when a viewer opens the hub, so it's always current.
Reload the page to pick up content published since then.

Like any Shiny app on Connect, the hub takes a few seconds to start if no
process is already running. To keep one ready, set **Min processes** to 1 in
the hub's settings, on the **Runtime** tab (**Advanced** before Connect
2026.08.0).

Administrators see every item on the server, because Connect gives
administrators access to all content.

## Customize it

To customize the hub, get the
[extension source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/shiny-content-hub),
make your changes, and publish it with
[`rsconnect::deployApp()`](https://rstudio.github.io/rsconnect/) or a
[git-backed deployment](https://docs.posit.co/connect/user/git-backed/).

- `app.R` holds the page layout and the per-viewer connection.
- `R/content_hub.R` turns the content list into cards and the table. Edit
  `content_type()` there to change how content types are grouped and labeled,
  or `content_card()` to change what each card shows.
- `www/styles.css` holds the hub's few custom styles. To restyle the whole
  page, pass a theme to `bs_theme()` in `app.R`; see
  [bslib theming](https://rstudio.github.io/bslib/articles/theming/).

To run the hub locally, set `CONNECT_SERVER` to your Connect server's URL and
`CONNECT_API_KEY` to your own API key, then run `shiny::runApp()`. Off Connect,
the hub lists content with that key instead of a viewer's permissions.

Run the tests with `make test`. After changing the app's files or packages,
regenerate `manifest.json` with `make update-manifest`.

## Learn more

- [OAuth integrations in Posit Connect](https://docs.posit.co/connect/user/oauth-integrations/)
- [connectapi](https://posit-dev.github.io/connectapi/)
- [bslib](https://rstudio.github.io/bslib/)
