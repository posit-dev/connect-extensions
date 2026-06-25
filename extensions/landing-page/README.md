# HTML: Landing Page

## About this example

A static HTML landing page served from Posit Connect. It gives your organization
a branded "front door" that welcomes your team, points them to key resources, and
links out to the content you publish. It uses no Connect API and has no
server-side code; it's just static files, which makes it the simplest way to put
a custom page in front of your Connect deployment.

## Who it's for

Teams who want a friendly, branded entry point to their published reports, apps,
and datasets, rather than sending people straight to a raw content listing.

## Customize it

The page is a template built around a placeholder "Example Organization." Make it
your own by editing `index.html` (each customizable spot is flagged with an HTML
comment):

- Replace "Example Organization" throughout with your organization's name.
- Replace `images/logo.png` with your own logo (it's set as the hero background
  image in `css/example-landing.css`).
- Point the "Getting Started Guide" link and the contact `mailto:` address at your
  own onboarding doc and team email.
- Swap the sample FAQs for the questions your users actually ask.

## Deploy

Publish the directory as static content with `rsconnect deploy html`, or push it
through a git-backed deployment. There's nothing to build.

## Requirements

* None
