# Nameservice Inspector

A Streamlit app for Connect administrators to visualize nameservice user and group data configured on their Posit Connect server.

## Purpose

When using [current user execution](https://docs.posit.co/connect/admin/process-management/#runas-current) with OAuth2, SAML, or LDAP authentication, Connect stores POSIX user and group information in its [nameservice](https://docs.posit.co/connect/admin/nameservice/) database. This app provides a simple UI to inspect that data, showing:

- **Users Table**: All nameservice users with their username, POSIX UID, primary GID, supplementary groups, and Connect user ID
- **Groups Table**: All nameservice groups with their group name and POSIX GID

## Requirements

This app requires two OAuth integrations to be configured on your Connect server and associated with the deployed content:

1. **Viewer API Key integration** - Used to access the nameservice APIs (`/v1/nameservice/*`)
2. **Admin API Key integration** - Used to access the groups API (`/v1/groups`)

### Setting up OAuth Integrations

See the [OAuth Integrations documentation](https://docs.posit.co/connect/user/oauth-integrations/) for details.

1. Create or identify a Viewer API Key integration on your Connect server
2. Create or identify an Admin API Key integration on your Connect server
3. After deploying this app, associate both integrations with the content item

### Environment Variables

After deploying, configure the following environment variables in the content settings:

| Variable                   | Description                                        |
|----------------------------|----------------------------------------------------|
| `VIEWER_INTEGRATION_GUID`  | The GUID of your Viewer API Key OAuth integration  |
| `ADMIN_INTEGRATION_GUID`   | The GUID of your Admin API Key OAuth integration   |

## Post-Installation Setup

After installing from the Connect Gallery:

1. Associate both OAuth integrations with the content
2. Set the environment variables for the integration GUIDs
3. Grant access to administrators who need to view nameservice data

## Development

To test changes:

```bash
rsconnect deploy manifest ./manifest.json --server <your-connect-server> --api-key <your-api-key>
```
