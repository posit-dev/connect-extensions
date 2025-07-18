# Content Health Monitor

This report uses the publisher’s API key to monitor a single piece of content. It checks whether the content is 
reachable, but does not validate its functionality. If scheduled to run regularly, it will send an email alert if the 
content becomes unreachable.

# Setup

The following environment variables are required when previewing the report locally.

```bash:
CONNECT_SERVER  # Set automatically when deployed to Connect
CONNECT_API_KEY # Set automatically when deployed to Connect
MONITORED_CONTENT_GUID # GUID for the content to monitor
```	

# Usage

Deploy the the Content Health Monitor to Connect, then follow the setup instructions, and then refresh (re-render) the report. 
