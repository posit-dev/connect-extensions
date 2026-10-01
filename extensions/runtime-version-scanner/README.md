# Runtime Version Scanner

See the Python, R, and Quarto versions used by your content. Filter by version, content type, and usage to identify items that need updating. Quickly find content that uses end-of-life language versions.

## Setup

The app acts as the signed-in viewer, so it needs a Visitor API Key integration
to call the Connect API with that person's identity.

After deploying, open the content's settings and, on the **Access** tab, add a
**Connect Visitor API Key** integration under **Integrations**. Until it is added,
the app shows a setup screen with these instructions. If the integration is not
listed, an administrator must first create a **Connect API** integration on your
server, with its **Max Role** set to Administrator or Publisher (Viewer will not
work). See the
[OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/)
and the
[Connect API section of the Admin Guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/).
