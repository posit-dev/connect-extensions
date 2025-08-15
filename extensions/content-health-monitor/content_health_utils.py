import json
import os
import re
import requests
from posit import connect

class MonitorState:
    """State container for content health monitor"""
    
    def __init__(self):
        """Initialize with default values"""
        # Flag to indicate if setup instructions should be displayed
        self.show_instructions = False
        # List to store setup instructions for the user
        self.instructions = []

# Define status constants
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
ERROR_PREFIX = "ERROR:"

# Define CSS styling constants
CSS_COLORS = {
    "neutral": {
        "border": "#ccc",
        "background": "#f8f9fa",
        "text": "#000"
    },
    "error": {
        "border": "#cc0000",
        "background": "#fff8f8",
        "text": "#cc0000"
    },
    "warning": {
        "border": "#f0ad4e",
        "background": "#fcf8e3",
        "text": "#cc0000"
    },
    "success": {
        "border": "#4caf50",
        "background": "#e8f5e9",
        "text": "#28a745"
    },
    "fail": {
        "border": "#f44336",
        "background": "#ffebee",
        "text": "#dc3545"
    }
}

CSS_BOX_STYLE = "border: 1px solid {border}; border-radius: 8px; padding: 10px; margin-bottom: 15px; background-color: {background};"
CSS_HEADER_STYLE = "margin-top: 0; padding-bottom: 8px; border-bottom: 1px solid #eaecef; font-weight: bold; font-size: 1.2em;"
CSS_CONTENT_STYLE = "padding: 5px 0;"
CSS_FOOTER_STYLE = "padding-top: 8px; font-size: 0.9em; border-top: 1px solid #eaecef;"
CSS_GRID_STYLE = "display: grid; grid-template-columns: 150px auto; grid-gap: 8px; padding: 10px 0;"

# Helper function to read environment variables and add instructions if missing
def get_env_var(var_name, state, description=""):
    """Get environment variable and add instruction if missing"""
    value = os.environ.get(var_name, "")
    if not value:
        state.show_instructions = True
        
        # Generic instruction for most variables
        if var_name != "MONITORED_CONTENT_GUID":
            instruction = f"Please set the <code>{var_name}</code> environment variable."
        # Detailed instructions for MONITORED_CONTENT_GUID
        else:
            one_tab = "&nbsp;&nbsp;&nbsp;&nbsp;"  # For indentation in HTML
            two_tabs = f"{one_tab}{one_tab}"  # For deeper indentation
            instruction = (
                f"To monitor a piece of content you must configure the <code>{var_name}</code> environment variable.<br><br>"
                
                f"<b>Step 1:</b> Locate the content you want to monitor in a new browser tab or window<br>"
                f"{one_tab}<b>Option A:</b> Copy the GUID from the Content Settings panel<br>"
                f"{two_tabs}• Click the <b>gear icon</b> in the top right toolbar to open <b>Content Settings</b><br>"
                f'{two_tabs}<img src="images/settings-gear-icon.png" alt="Settings gear icon location" '
                f'style="max-width: 80%; margin: 10px 0; border: 1px solid #ddd;"><br>'
                f"{two_tabs}• Select the <b>Info</b> tab<br>"
                f"{two_tabs}• Scroll to the bottom and click the <b>copy</b> button next to the GUID<br>"
                f"{one_tab}<b>Option B:</b> Copy the full URL from your browser<br>"
                f"{two_tabs}• If the address bar contains a GUID (ex: 1d97c1ff-e56c-4074-906f-cb3557685b75), "
                f"you can simply copy the entire URL<br><br>"

                f"<b>Step 2:</b> Return to this report to set the environment variable<br>"
                f"{one_tab}• Click the <b>gear icon</b> to open <b>Content Settings</b><br>"
                f"{one_tab}• Select the <b>Vars</b> tab<br>"
                f"{one_tab}• Add a new variable named <code>{var_name}</code><br>"
                f"{one_tab}• Paste the GUID you copied into the value field<br>"
                f"{one_tab}• Click <b>Add Variable</b> and then <b>Save</b> to save it<br><br>"

                f"<b>Step 3:</b> Click <b>Refresh Report</b> in the top right to to run a health check against the content specified in the new variable<br>"
                f'<img src="images/refresh-report.png" alt="Refresh report button" style="max-width: 80%; margin: 10px 0; border: 1px solid #ddd;"><br><br>'

            )
        
        if description:
            instruction += f" {description}"
        state.instructions.append(instruction)
    return value

# Helper function to extract error messages from exceptions
def format_error_message(exception):
    """Extract a clean error message from various exception types"""
    error_message = str(exception)
    
    # posit-sdk will return a ClientError if there is a problem getting the guid, parse the error message
    if isinstance(exception, connect.errors.ClientError):
        try:
            # ClientError from posit-connect SDK stores error as string that contains JSON
            # Convert the string representation to a dict
            error_data = json.loads(str(exception))
            if isinstance(error_data, dict):
                # Extract the specific error message
                if "error_message" in error_data:
                    error_message = error_data["error_message"]
                elif "error" in error_data:
                    error_message = error_data["error"]
        except json.JSONDecodeError:
            # If parsing fails, keep the original error message
            pass
    
    return error_message

# Function to extract GUID string or URL
def extract_guid(input_string):
    """
    Extract GUID from a string or URL.
    
    Args:
        input_string: String that may contain a GUID
        
    Returns:
        tuple: (extracted_guid, error_message)
            - extracted_guid: The extracted GUID or original string if no GUID found
            - error_message: Error message if the input doesn't contain a valid GUID, None otherwise
    """
    # Match UUIDs in various formats that might appear in URLs
    guid_pattern = re.compile(r'[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}')
    
    match = guid_pattern.search(input_string)
    if match:
        return match.group(0), None
    
    # Check if the input looks like a URL but doesn't contain a GUID
    url_pattern = re.compile(r'^https?://', re.IGNORECASE)
    if url_pattern.match(input_string):
        error_message = (
            f"The URL provided in <code>MONITORED_CONTENT_GUID</code> does not contain a valid GUID. "
            f"The URL should contain a GUID like: <code>1d97c1ff-e56c-4074-906f-cb3557685b75</code><br><br>"
            f"The URL provided is: <a href=\"{input_string}\" target=\"_blank\" rel=\"noopener noreferrer\">{input_string}</a><br><br>"
            f"Please update your environment variable with a valid GUID or a URL containing a GUID."
        )
        return input_string, error_message
    
    # Handle non-URL strings that don't match GUID format
    error_message = (
        f"The value provided in <code>MONITORED_CONTENT_GUID</code> is not a valid GUID. "
        f"A valid GUID looks like: <code>1d97c1ff-e56c-4074-906f-cb3557685b75</code><br><br>"
        f"The provided value was: <code>{input_string}</code><br><br>"
        f"Please update your environment variable with a valid GUID or a URL containing a GUID."
    )
    return input_string, error_message

# Function to get content details from Connect API
def get_content(client, guid):
    try:
        # Get content details from Connect API
        content = client.content.get(guid)
        return content
    except Exception as e:
        # Extract error message and return error object
        error_message = format_error_message(e)
        
        # Return content with error in title
        return {
            "title": f"{ERROR_PREFIX} {error_message}", 
            "guid": guid
        }

def get_user(client, user_guid):
    try:
        user = client.users.get(user_guid)
        return user
    except Exception as e:
        error_message = format_error_message(e)
        raise RuntimeError(f"Error getting user: {error_message}")

def get_current_user_full_name(client):
    """
    Get the full name of the current user from the Connect API
    
    Args:
        client: The Connect client instance
        
    Returns:
        str: The full name of the current user or "Unknown" if not available
    """
    try:
        # Get the current user information
        current_user = client.me
        
        # Extract first and last name
        first_name = current_user.get("first_name", "")
        last_name = current_user.get("last_name", "")
        
        # Combine into full name
        full_name = f"{first_name} {last_name}".strip()
        
        # Return username if full name is empty
        if not full_name:
            return current_user.get("username", "Unknown")
            
        return full_name
    except Exception as e:
        # Handle any errors gracefully
        error_message = format_error_message(e)
        print(f"Warning: Could not retrieve current user: {error_message}")
        return "Unknown"

# Function to validate content health (simple HTTP 200 check)
def validate(client, guid, connect_server, api_key):
    # Get content details
    content = get_content(client, guid)

    content_name = content.get("title", "")
    # Title is optional, if not set use name
    if not content_name:
        content_name = content.get("name", "")
    
    # Check if get_content returned an error (no permission, invalid GUID) and return early if it did
    if str(content_name).startswith(ERROR_PREFIX):
        return {
            "guid": guid,
            "name": content_name,
            "status": "FAIL",
            "http_code": "Error retrieving content"
        }
    
    # Get the content URLs
    dashboard_url = content.get("dashboard_url", "")
    content_url = content.get("content_url", "")

    # Initialize default owner information
    owner_email = ""
    owner_full_name = ""
    
    # Headers for Connect API
    headers = {
        "Authorization": f"Key {api_key}",
        # Set a custom user agent to enable filtering of activity in Connect instrumentation data
        "User-Agent": "ContentHealthMonitor/1.0",
    }
    
    # Get content owner details
    try:
        owner_guid = content.get("owner_guid")
        if owner_guid:
            # Get owner details
            owner = get_user(client, owner_guid)
            owner_email = owner.get("email", "")
            owner_first_name = owner.get("first_name", "")
            owner_last_name = owner.get("last_name", "")
            owner_full_name = f"{owner_first_name} {owner_last_name}".strip()
            if not owner_full_name:  # Handle case where both names are empty
                owner_full_name = "Unknown"
    except Exception as e:
        # If there's an error getting the owner, keep the defaults
        print(f"Warning: Could not retrieve owner for {guid}: {str(e)}")
    
    # Compose URL to logs if we have a dashboard URL, only owner/editor have access
    if dashboard_url and content.get("app_role") != "viewer":
        logs_url = f"{dashboard_url}/logs"
    else:
        logs_url = ""

    # Validate content health
    try:
        # Use the content_url if available
        if not content_url:
            base_url = connect_server.rstrip('/')
            content_url = f"{base_url}/content/{guid}"
            
        content_response = requests.get(
            content_url, 
            headers=headers,
            timeout=60, # Max time to wait for a response from the content
            allow_redirects=True  # Enabled by default in Python requests, included for clarity
        )
        
        # EXTENSION POINT: You can add additional validation beyond HTTP status
        
        # Example: Check if response body contains expected text from environment variable
        # expected_text = os.environ.get("EXPECTED_CONTENT_TEXT")
        # contains_expected_text = True  # Default to True if no expected text is configured
        # if expected_text:  # Only perform the check if expected text is configured
        #     contains_expected_text = expected_text in content_response.text

        # Determine status based on validation conditions
        http_status_valid = content_response.status_code >= 200 and content_response.status_code < 300
        
        # Combine all validation conditions, you can add more as needed
        status = "PASS" if (http_status_valid) else "FAIL"
        
        return {
            # Content details
            "guid": guid,
            "name": content_name,
            "dashboard_url": dashboard_url,
            "logs_url": logs_url,
            # Owner details
            "owner_name": owner_full_name,
            "owner_email": owner_email,
            # Monitoring status
            "status": status,
            "http_code": content_response.status_code
        }

    except Exception as e:
        return {
            # Content details
            "guid": guid,
            "name": content_name,
            "dashboard_url": dashboard_url,
            "logs_url": logs_url,
            # Owner details
            "owner_name": owner_full_name,
            "owner_email": owner_email,
            # Monitoring status
            "status": "FAIL",
            "http_code": str(e)
        }

# Helper function to check if a result has an error
def has_error(result):
    """Check if a result contains an error message in the name field"""
    return result["name"].startswith(ERROR_PREFIX) if result and "name" in result else False

# Helper function to extract error details from a result
def extract_error_details(result):
    """Extract error message and GUID from a result"""
    if has_error(result):
        return {
            "message": result["name"].replace(f"{ERROR_PREFIX} ", ""),
            "guid": result.get("guid", "")
        }
    return None

# Define helper functions for generating HTML components
def create_about_box(about_content):
    """Creates the About callout box HTML"""
    neutral = CSS_COLORS["neutral"]
    return f"""
    <div style="{CSS_BOX_STYLE.format(border=neutral['border'], background=neutral['background'])}"> 
        <div style="{CSS_HEADER_STYLE}">ℹ️ About</div>
        <div style="{CSS_CONTENT_STYLE}">{about_content}</div>
    </div>
    """

def create_error_box(guid, error_msg):
    """Creates the Error callout box HTML"""
    error = CSS_COLORS["error"]
    guid = guid or "Unknown"
    error_msg = error_msg or "Unknown error"
    return f"""
    <div style="{CSS_BOX_STYLE.format(border=error['border'], background=error['background'])}"> 
        <div style="{CSS_HEADER_STYLE}; color: {error['text']}">⚠️ Error Monitoring Content</div>
        
        <div style="{CSS_GRID_STYLE}; margin-top: 10px; padding-bottom: 8px; border-bottom: 1px solid #eaecef;">
            <div style="font-weight: bold;">Content GUID:</div>
            <div>{guid}</div>
            
            <div style="font-weight: bold;">Error:</div>
            <div style="color: {error['text']};">{error_msg}</div>
        </div>
        
        <div style="{CSS_FOOTER_STYLE}">
            Please check that your <code>MONITORED_CONTENT_GUID</code> environment variable contains a valid content identifier.
        </div>
    </div>
    """

def create_no_results_box():
    """Creates the No Results callout box HTML"""
    warning = CSS_COLORS["warning"]
    error_text = CSS_COLORS["error"]["text"]
    return f"""
    <div style="{CSS_BOX_STYLE.format(border=warning['border'], background=warning['background'])}"> 
        <div style="{CSS_HEADER_STYLE}; color: {error_text};">⚠️ No results available</div>
        <div style="{CSS_CONTENT_STYLE}">
            No monitoring results were found. This could be because:
            <ul>
                <li>No valid GUID was provided</li>
                <li>There was an issue connecting to the specified content</li>
                <li>The environment is properly configured but there was an error that caused no data to be returned</li>
            </ul>
            <p>Please check your MONITORED_CONTENT_GUID environment variable and ensure it contains a valid content identifier.</p>
        </div>
    </div>
    """

def create_instructions_box(instructions_html_content):
    """Creates the Setup Instructions callout box HTML"""
    neutral = CSS_COLORS["neutral"]
    warning = CSS_COLORS["warning"]  # For the header to make it stand out
    return f"""
    <div style="{CSS_BOX_STYLE.format(border=warning['border'], background=neutral['background'])}"> 
        <div style="{CSS_HEADER_STYLE}; color: #f0ad4e;">⚙️ Setup Required</div>
        {instructions_html_content}
        <div style="{CSS_FOOTER_STYLE}">
            See Posit Connect documentation for <a href='https://docs.posit.co/connect/user/content-settings/#content-vars' target='_blank'>Vars (environment variables)</a>
        </div>
    </div>
    """

# Function to create the report display for a result
def create_report_display(result_data, check_time_value, current_user_name):
    if result_data is None:
        return None
        
    # Format content name with link if dashboard_url is available
    content_name = result_data.get('name', 'Unknown')
    dashboard_url = result_data.get('dashboard_url', '')
    if dashboard_url:
        content_name_display = f"<a href='{dashboard_url}' target='_blank' style='text-decoration:none;'>{content_name}</a>"
    else:
        content_name_display = content_name
    
    # Get GUID
    content_guid = result_data.get('guid', '')
    
    # Format status with appropriate color
    status = result_data.get('status', '')
    
    if status == STATUS_PASS:
        status_colors = CSS_COLORS["success"]
        status_icon = "✅"  # Checkmark
    else:
        status_colors = CSS_COLORS["fail"]
        status_icon = "❌"  # X mark
    
    # Format logs link if available
    logs_url = result_data.get('logs_url', '')
    if logs_url:
        logs_display = f"<a href='{logs_url}' target='_blank' style='text-decoration:none;'>📋 View Logs</a>"
    else:
        logs_display = f"Log access is restricted for {current_user_name}. Logs are only available to the content owner and collaborators."
    
    # Format owner information
    owner_name = result_data.get('owner_name', 'Unknown')
    owner_email = result_data.get('owner_email', '')
    if owner_email:
        owner_display = f"<a href='mailto:{owner_email}' style='text-decoration:none;'>✉️ {owner_name}</a>"
    else:
        owner_display = owner_name
    
    # Create last check time display
    check_time_display = f"Last checked: {check_time_value}"
    
    html_output = f"""
    <div style="{CSS_BOX_STYLE.format(border=status_colors['border'], background=status_colors['background'])}">
        <div style="{CSS_HEADER_STYLE}">
            <span style="color: {status_colors['text']};">{status_icon} {status}</span>
        </div>
        
        <div style="{CSS_GRID_STYLE}">
            <div style="font-weight: bold;">Name:</div>
            <div>{content_name_display}</div>
            
            <div style="font-weight: bold;">Content GUID:</div>
            <div>{content_guid}</div>
            
            <div style="font-weight: bold;">Logs:</div>
            <div>{logs_display}</div>
            
            <div style="font-weight: bold;">Owner:</div>
            <div>{owner_display}</div>
        </div>
        
        <div style="text-align: right; font-size: 0.8em; color: #666; {CSS_FOOTER_STYLE}">
            {check_time_display}
        </div>
    </div>
    """
    
    return html_output

# Function to check if the Connect server is reachable
def check_server_reachable(connect_server, api_key):
    """Check if Connect server is reachable and responding"""
    # Headers for Connect API
    headers = {
        "Authorization": f"Key {api_key}",
        # Set a custom user agent to enable filtering of activity in Connect instrumentation data
        "User-Agent": "ContentHealthMonitor/1.0",
    }

    try:
        server_check = requests.get(
            f"{connect_server}/__ping__", 
            headers=headers, 
            timeout=5
        )
        server_check.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Connect server at {connect_server} is unavailable: {str(e)}")

# Helper function to determine if we should send an email
def should_send_email(show_error, content_result):
    """Determine if we should send an email notification"""
    # Send email if we have an API error
    if show_error:
        return True
    
    # Send email if the monitored content has a failure status
    if content_result and 'status' in content_result:
        return content_result['status'] == STATUS_FAIL
    
    return False
