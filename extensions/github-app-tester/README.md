# GitHub App Integration Tester

A Shiny for Python app to test GitHub App (service account) integrations on Posit Connect.

## Features

- Automatically obtains an installation token using the posit-sdk
- Shows token information (type, prefix)
- Lists all accessible repositories with their permissions
- Displays rate limit status

## Deployment to Connect

1. Deploy this app to your Posit Connect server
2. Associate it with your GitHub App integration in the Connect UI (Settings > OAuth Integrations)
3. Run the app - it will automatically get an installation token and show accessible repositories

## How it works

When deployed on Connect with a GitHub App integration:

1. Connect provides a `CONNECT_CONTENT_SESSION_TOKEN` environment variable
2. The app uses posit-sdk to exchange this token for GitHub credentials:
   ```python
   from posit import connect
   client = connect.Client()
   credentials = client.oauth.get_content_credentials(content_session_token)
   ```
3. The `access_token` from the credentials is a GitHub App installation token (`ghs_...`)
4. This token is used to query the GitHub API

## What this app tests

1. **Token exchange**: Can the app exchange the content session token for GitHub credentials?
2. **Token type**: Is the token a valid GitHub App installation token (`ghs_` prefix)?
3. **Repository access**: Which repositories can the token access?
4. **Permissions**: What permissions does the token have on each repository?

## Troubleshooting

- **"CONNECT_CONTENT_SESSION_TOKEN not available"**: Make sure a GitHub App integration is associated with this content
- **"No repositories accessible"**: The GitHub App may not be installed on any repositories
- **403 errors**: The GitHub App may not have the required permissions
