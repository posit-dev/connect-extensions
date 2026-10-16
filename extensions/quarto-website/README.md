# Quarto: Content Hub

## About this extension

A content hub for your Posit Connect server: one page where people can browse
the reports, apps, APIs, and other content published there. Featured content
appears as cards at the top. Below it is a table of all the content, which
viewers can search and filter by title, type, owner, or tag, and sort by any
column.

The hub is a static Quarto document. Each time it renders, it asks the Connect
Server API for the content list with the publisher's permissions and writes the
result into the page. Every viewer sees the same page, and viewing it starts no
process on the server. Schedule the hub to render regularly so the list stays
current.

The hub is for anyone who wants a friendlier way into Connect than the content
list in the dashboard, such as a front door for a team or project, or a
curated page of published work.

If each viewer should see only the content they can access, use the
[R Shiny: Content Hub](https://github.com/posit-dev/connect-extensions/tree/main/extensions/shiny-content-hub)
extension instead. It's an interactive app that lists content with each
viewer's own permissions, with a tab for each of your tags.

## Who can see what

The hub lists everything its publisher can see, and shows that list to anyone
it's shared with. A viewer can't open content they lack access to, but they can
see its title, description, and owner on the hub. Before you share the hub,
make sure the people who can view it may see what's listed. For example:

- Share the hub only with people who can access everything the publisher can.
- Publish the hub from an account that can see only the content meant for the
  hub's audience.

If the hub is published by an administrator, it lists every item on the server.

## Setup

Deploy the hub from the Connect Gallery. It works as installed: Connect supplies
the server address and an API key for the publisher when it renders the hub, so
there's nothing to configure.

To keep the list current, open the hub's **Schedule** settings and have it
render regularly, for example daily. The page shows when the list was last
updated.

Optionally, choose which content to feature:

1. Tag the content you want to feature in Connect, for example with a
   `showcase` tag.
2. In the hub's settings, on the **Runtime** tab (**Advanced** before Connect
   2026.08.0), under **Environment Variables**, set `FEATURED_TAGS` to the tag
   name. To feature several tags, separate them with commas
   (`showcase, onboarding`). Tag names are not case-sensitive.
3. Re-render the hub so it picks up the setting.

The hub features up to 12 tagged items, the most recently updated ones.
Without `FEATURED_TAGS`, or if no content carries the featured tags, it
features the six most recently updated items instead.

## Use it

- Select a card or a title in the table to open that item in Connect.
- Type in the table's **Search** box to search every column at once, or in the
  boxes under the column headers to filter one column.
- Select a column header to sort by that column.

## Customize it

To customize the hub, get the
[extension source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/quarto-website),
make your changes, and publish it with
[`quarto publish connect`](https://quarto.org/docs/publishing/rstudio-connect.html),
[`rsconnect::deployDoc()`](https://rstudio.github.io/rsconnect/), or a
[git-backed deployment](https://docs.posit.co/connect/user/git-backed/).

- Change the hub's title and the introduction at the top of `index.qmd`.
- Change which content appears by filtering `items` in `index.qmd`, for
  example to list only content with a particular tag.
- `content_hub.R` turns the content list into cards and the table. Edit
  `content_type()` there to change how content types are grouped and labeled,
  or `content_card()` to change what each card shows.
- Change the look by choosing different
  [Bootswatch themes](https://quarto.org/docs/output-formats/html-themes.html)
  in `_quarto.yml`, or by editing `styles.css`.

To render the hub locally, set `CONNECT_SERVER` to your Connect server's URL and
`CONNECT_API_KEY` to your own API key, then run `quarto render`. After changing
the hub's files or packages, regenerate `manifest.json` with
`make update-manifest`.

## Learn more

- [connectapi](https://posit-dev.github.io/connectapi/)
- [bslib cards](https://rstudio.github.io/bslib/articles/cards/)
- [reactable](https://glin.github.io/reactable/)
- [Scheduling content on Posit Connect](https://docs.posit.co/connect/user/scheduling/)
