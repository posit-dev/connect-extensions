# R Shiny: Custom Landing Page

## About this example

A custom landing page for your Posit Connect server, built with R Shiny,
organized by your tags and personal to each viewer. Each tag gets a tab, such
as one per department or team, listed down the side of the page. Each tab
groups its content into sections by the tags under it: a Finance tab might
have Reports and Dashboards sections, for example. Viewers can search within a
tab by title, description, owner, type, or tag.

Each viewer sees only the content they can open. The app lists content with
the viewer's own Connect permissions, through a Connect API integration, rather
than with a shared publisher API key. That makes it safe to share the page with
everyone on the server: nobody sees the titles of content they can't access.

This example is for organizations that already tag their content by team,
project, or topic, and want a front door that follows that structure, rather
than the single flat list in the Connect dashboard. Use it as a starting point
for your own landing page.

For a simpler page, see the
[Static HTML: Landing Page](https://github.com/posit-dev/connect-extensions/tree/main/extensions/landing-page)
example, which needs no API access, or the
[Quarto: Content Hub](https://github.com/posit-dev/connect-extensions/tree/main/extensions/quarto-website)
extension, a static page that lists what the publisher can see.

## Requirements

- Posit Connect 2025.04.0 or newer, with OAuth integrations enabled.
- A **Connect API** integration, created by a Connect administrator. Any
  **Max Role** works; viewers never get more access than their own role
  allows. See the
  [Connect API integration guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/).
- Tags on your content. Connect administrators create tags, and publishers
  apply them to their content. See
  [Tags](https://docs.posit.co/connect/user/content-settings/#tags).

## Setup

1. Deploy the landing page from the Connect Gallery.
2. In its settings, on the **Runtime** tab (**Access** before Connect
   2026.08.0), add the Connect API integration under **Integrations**.
3. Choose which tags become tabs. By default, each top-level tag is a tab. To
   use the tags under one tag instead, set the `PARENT_TAG` environment
   variable to that tag's name, on the **Runtime** tab (**Advanced** before
   Connect 2026.08.0), under **Environment Variables**. For example, with a
   `Departments` tag holding `Finance` and `Marketing`, setting `PARENT_TAG`
   to `Departments` gives Finance and Marketing tabs. If several tags share
   the name, give the tag's full path, such as `Departments/Finance`. Tag
   names are not case-sensitive.
4. Share the page with the people who should use it. Each viewer needs a
   Connect account and must be logged in.

Until the integration is added, the page shows a message explaining how to add
it instead of any tabs.

## Use it

- Select a tab to see the content under that tag, and a card to open that
  item in Connect. On narrow screens, the tabs form a row that scrolls
  sideways.
- Content tagged with a tag under the tab's tag appears in that tag's section.
  Content can appear in more than one section. Content that fits no section,
  such as content tagged with the tab's own tag, appears under **Other**.
- Type in **Search** to narrow the tab's content. Each word you enter must
  appear somewhere in the item's title, description, owner, type, or tags, in
  any order.
- Each section shows its 30 most recently updated items. Search to find
  others.

The page fetches a tab's content the first time the viewer opens it, so a
server with many tags doesn't make it slow to load. Reload the page to pick up
content published since then.

Like any Shiny app on Connect, the page takes a few seconds to start if no
process is already running. To keep one ready, set **Min processes** to 1 in
its settings, on the **Runtime** tab (**Advanced** before Connect 2026.08.0).

Administrators see every item on the server, because Connect gives
administrators access to all content.

## Customize it

To customize the page, get the
[example source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/shiny-landing-page),
make your changes, and publish it with
[`rsconnect::deployApp()`](https://rstudio.github.io/rsconnect/) or a
[git-backed deployment](https://docs.posit.co/connect/user/git-backed/).

- `app.R` holds the page layout, the per-viewer connection, and each tab.
  Change the title and the introduction at the top of the page there.
- `R/portal.R` turns the tag hierarchy into tabs and sections. Edit
  `tab_sections()` there to change how a tab's content is grouped.
- `R/content_hub.R` turns the content list into cards. Edit `content_type()`
  there to change how content types are grouped and labeled, or
  `content_card()` to change what each card shows.
- `www/styles.css` holds the page's few custom styles. To restyle the whole
  page, pass a theme to `bs_theme()` in `app.R`; see
  [bslib theming](https://rstudio.github.io/bslib/articles/theming/).

To run the page locally, set `CONNECT_SERVER` to your Connect server's URL and
`CONNECT_API_KEY` to your own API key, then run `shiny::runApp()`. Off Connect,
the page lists content with that key instead of a viewer's permissions.

Run the tests with `make test`. After changing the app's files or packages,
regenerate `manifest.json` with `make update-manifest`.

## Learn more

- [OAuth integrations in Posit Connect](https://docs.posit.co/connect/user/oauth-integrations/)
- [Content search in the Connect API](https://docs.posit.co/connect/api/#get-/v1/search/content)
- [connectapi](https://posit-dev.github.io/connectapi/)
- [bslib](https://rstudio.github.io/bslib/)
