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


# Testing

If customizing the code in this report here are some general test scenarios to consider:

 - No MONITORED_CONTENT_GUID env var set
     - If scheduled, DOES NOT send an email
 - Invalid GUID
     - If scheduled, sends an email
 - Valid GUID for content you are a owner of
 - Valid GUID for content you are a collaborator of
 - Valid GUID for content you are a viewer of
 - Valid GUID for content you do not have access to (not in ACL, etc.)
     - In the above setup, where the monitored content passing validation, if scheduled, DOES NOT send an email
 - Valid GUID, content is published but fails validation
     - If scheduled, sends an email
