# App Canary

A Quarto dashboard that tests one or more applications that have been deployed to Connect and validates if the app is 
successfully running and displays the results.

# Setup

The following environment variables are required

```bash:
CONNECT_SERVER  # Set automatically on Connect, otherwise set to your Connect server URL
CONNECT_API_KEY # Set automatically on Connect, otherwise set to your Connect API key
CANARY_GUIDS    # Comma separated list of GUIDs for the applications to test
```	

# Usage

Deploy the app to Connect and then render the dashboard. 
