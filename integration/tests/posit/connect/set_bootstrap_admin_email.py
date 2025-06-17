"""
Sets the email of the bootstrap admin user in Posit Connect.

This script makes the following API requests to Posit Connect:
1. Gets the current user (bootstrap admin) via the API
2. Updates the admin user's email to 'admin@example.com'

Setting an email for the bootstrap user prevents Connect from logging
an error about the user having no email address when Connect attempts 
to send an email to the user, such as a deployment failure notification.

Environment Variables:
    CONNECT_API_KEY: API key for Posit Connect authentication
    CONNECT_SERVER: URL of the Posit Connect server

Returns:
    0 on success, 1 on failure
"""

from posit import connect
import sys

try:
    # Instantiate a Connect client using posit-sdk where api_key and url are automatically read from our environment vars
    client = connect.Client()
    
    # Set the current user's email (this will be the bootstrap admin since we only use the bootstrap user in these tests)
    current_user = client.me.UpdateUser({"email": "admin@example.com"})
    
    print(f"✅ Admin email set to {current_user}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
