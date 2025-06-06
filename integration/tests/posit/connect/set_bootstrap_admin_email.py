"""
Sets the email of the bootstrap admin user in Posit Connect.

This script makes the following API requests to Posit Connect:
1. Gets the current user (bootstrap admin) via the API
2. Updates the admin user's email to 'admin@example.com'

This allows deployment error emails to be sent to a valid address, otherwise 
the send will fail and log an error in the Connect logs making it more 
difficult to debug deployment issues.

Environment Variables:
    CONNECT_API_KEY: API key for Posit Connect authentication
    CONNECT_SERVER: URL of the Posit Connect server

Returns:
    0 on success, 1 on failure
"""

import requests
import os
import sys

try:
    # Get environment variables
    base_url = os.environ["CONNECT_SERVER"]
    api_key = os.environ["CONNECT_API_KEY"]
    headers = {"Authorization": f"Key {api_key}"}
    
    # Get current user (this will be the bootstrap admin since we only use the bootstrap user in these tests)
    user_resp = requests.get(f"{base_url}/__api__/v1/user", headers=headers)
    user_resp.raise_for_status()
    current_user = user_resp.json()
    
    # Get admin GUID from the response
    current_user_guid = current_user["guid"]
    
    # Update admin email
    update_resp = requests.put(
        f"{base_url}/__api__/v1/users/{current_user_guid}", 
        headers=headers, 
        json={"email": "admin@example.com"}
    )
    update_resp.raise_for_status()
    
    print("✅ Admin email set to admin@example.com")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
