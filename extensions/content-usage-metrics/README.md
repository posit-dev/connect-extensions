# Content Usage Metrics

A Shiny app that helps you understand content usage patterns on your Connect server. Browse an overview of usage across your published content, and dive into a detailed breakdown of visit-level data for each piece of content.

### Setup

After deploying this app, you'll need to add a Visitor API Key integration to allow it to access data on the Connect server using the identity of whoever's using the app.

In the app's control panel on the right of the screen, in the Access tab, click **"Add integration"**, then select a **Visitor API Key** integration.

If you don't see one in the list, an administrator must enable this feature on your Connect server.
See the [Admin Guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/) for setup instructions.
