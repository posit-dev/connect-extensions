# Standard library imports
import json
import os

# Third-party imports
import pytest
import requests
from posit import connect
from unittest.mock import MagicMock, patch

# Import the modules - this must be at the top level
import globals
import content_health_utils


# Constants from content_health_utils
ERROR_PREFIX = content_health_utils.ERROR_PREFIX
STATUS_FAIL = content_health_utils.STATUS_FAIL
STATUS_PASS = content_health_utils.STATUS_PASS

# Functions from content_health_utils
check_server_reachable = content_health_utils.check_server_reachable
extract_error_details = content_health_utils.extract_error_details
format_error_message = content_health_utils.format_error_message
get_content = content_health_utils.get_content
get_env_var = content_health_utils.get_env_var
get_user = content_health_utils.get_user
has_error = content_health_utils.has_error
should_send_email = content_health_utils.should_send_email
validate = content_health_utils.validate



# Define test fixtures and common test data
@pytest.fixture
def mock_client():
    """Create a mock Connect client"""
    client = MagicMock()
    return client

@pytest.fixture
def valid_content_response():
    """Create a valid content response object"""
    content = {
        "guid": "valid-guid-123",
        "title": "Test Content",
        "name": "test_content",
        "dashboard_url": "https://connect.example.com/content/valid-guid-123/",
        "content_url": "https://connect.example.com/content/valid-guid-123/",
        "owner_guid": "owner-guid-456",
        "app_role": "owner"  # can be owner, editor or viewer
    }
    return content

@pytest.fixture
def valid_user_response():
    """Create a valid user response object"""
    user = {
        "guid": "owner-guid-456",
        "email": "owner@example.com",
        "first_name": "Test",
        "last_name": "Owner"
    }
    return user

# Test helper for environment variable management
def clear_env_var(var_name):
    """Clear an environment variable if it exists"""
    os.environ.pop(var_name, None)  # More pythonic way using pop with default

@pytest.fixture(autouse=True)
def reset_module_globals():
    """Reset module globals before each test"""
    globals.show_instructions = False
    globals.instructions = []
    yield  # This makes it run before each test; the test runs at this point
    # If we needed cleanup after each test, it would go here

@pytest.fixture
def env_var():
    """Fixture to manage environment variables for tests"""
    # Save the original environment to restore later
    original_env = os.environ.copy()
    
    # Helper function to set environment variables for tests
    def _set_env(name, value):
        os.environ[name] = value
    
    yield _set_env
    
    # After the test, restore the original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_format_error_message():
    """Create a patch for format_error_message with a specific return value"""
    def _create_patch(error_message):
        # Use patching with module name imported directly for clarity
        return patch('content_health_utils.format_error_message', return_value=error_message)
    return _create_patch

@pytest.fixture
def mock_client_error():
    """Create a mock ClientError with proper setup"""
    def _create_error(error_message, status_code=404, reason="Not Found"):
        client_error = connect.errors.ClientError(error_message, status_code, reason, "{}")
        return client_error
    return _create_error

@pytest.fixture
def connect_test_server():
    """Return common test server URL"""
    return "https://connect.example.com"

@pytest.fixture
def api_test_key():
    """Return common test API key"""
    return "test_api_key"

# Tests for get_env_var function
class TestGetEnvVar:
    
    def test_get_env_var_with_value(self, env_var):
        """Test get_env_var when env var exists"""
        # Setup - use the environment fixture
        var_name = "TEST_ENV_VAR"
        var_value = "test_value"
        env_var(var_name, var_value)
   
        # Execute
        result = get_env_var(var_name)
        
        # Assert
        assert result == var_value
        assert not globals.show_instructions
        assert globals.instructions == []
        
        # No explicit cleanup needed - the fixture handles it
    
    def test_get_env_var_missing_standard(self):
        """Test get_env_var when env var is missing (standard var)"""
        # Setup
        var_name = "MISSING_ENV_VAR"
        clear_env_var(var_name)  # Ensure it doesn't exist

        # Execute
        result = get_env_var(var_name)
        
        # Assert
        assert result == ""
        assert globals.show_instructions
        assert len(globals.instructions) == 1
        assert f"Please set the <code>{var_name}</code> environment variable." in globals.instructions[0]
    
    def test_get_env_var_missing_canary_guid(self):
        """Test get_env_var when MONITORED_CONTENT_GUID is missing"""
        # Setup
        var_name = "MONITORED_CONTENT_GUID"
        clear_env_var(var_name)  # Ensure it doesn't exist

        # Execute
        result = get_env_var(var_name)
        
        # Assert
        assert result == ""
        assert globals.show_instructions
        assert len(globals.instructions) == 1
        assert "Open the <b>Content Settings</b> panel" in globals.instructions[0]
        assert f"<code>{var_name}</code>" in globals.instructions[0]
    
    def test_get_env_var_with_description(self):
        """Test get_env_var when env var is missing and description is provided"""
        # Setup
        var_name = "MISSING_ENV_VAR"
        description = "This is important for testing."
        clear_env_var(var_name)  # Ensure it doesn't exist

        # Execute
        result = get_env_var(var_name, description)
        
        # Assert
        assert result == ""
        assert globals.show_instructions
        assert len(globals.instructions) == 1
        assert f"Please set the <code>{var_name}</code> environment variable." in globals.instructions[0]
        assert description in globals.instructions[0]


# Tests for format_error_message function
class TestFormatErrorMessage:
    
    def test_format_error_message_standard_exception(self):
        """Test format_error_message with a standard exception"""
        # Setup
        exception = Exception("This is a test error")
        
        # Execute
        result = format_error_message(exception)
        
        # Assert
        assert result == "This is a test error"
    
    def test_format_error_message_client_error_with_error_message(self):
        """Test format_error_message with a ClientError containing error_message field"""
        # Setup
        error_data = {"error_message": "Specific client error message"}
        error_json = json.dumps(error_data)
        
        # Create a proper ClientError with mocking
        # This approach creates a real ClientError that will pass isinstance checks
        client_error = connect.errors.ClientError("Error", 404, "Not Found", "{}")
        
        # Use patch to temporarily modify its string representation
        with patch.object(connect.errors.ClientError, '__str__', return_value=error_json):
            # Execute
            result = format_error_message(client_error)
            
            # Assert
            assert result == "Specific client error message"
    
    def test_format_error_message_client_error_with_error(self):
        """Test format_error_message with a ClientError containing error field"""
        # Setup
        error_data = {"error": "General client error"}
        error_json = json.dumps(error_data)
        
        # Create a proper ClientError with mocking
        client_error = connect.errors.ClientError("Error", 403, "Forbidden", "{}")
        
        # Use patch to temporarily modify its string representation
        with patch.object(connect.errors.ClientError, '__str__', return_value=error_json):
            # Execute
            result = format_error_message(client_error)
            
            # Assert
            assert result == "General client error"
    
    def test_format_error_message_client_error_invalid_json(self):
        """Test format_error_message with a ClientError containing invalid JSON"""
        # Setup
        error_text = "This is not valid JSON"
        
        # Create a proper ClientError with mocking
        client_error = connect.errors.ClientError("Error", 500, "Server Error", "{}")
        
        # Use patch to temporarily modify its string representation
        with patch.object(connect.errors.ClientError, '__str__', return_value=error_text):
            # Execute
            result = format_error_message(client_error)
            
            # Assert - Since the JSON is invalid, it should return the original string
            assert result == error_text


# Tests for get_content and get_user functions
class TestContentAndUserFunctions:
    
    def test_get_current_user_full_name_success(self, mock_client):
        """Test get_current_user_full_name when successful"""
        # Setup - Mock current user info
        mock_client.me = {
            "first_name": "Current",
            "last_name": "User",
            "username": "current_user",
            "email": "current@example.com"
        }
        
        # Execute
        result = content_health_utils.get_current_user_full_name(mock_client)
        
        # Assert
        assert result == "Current User"
    
    def test_get_current_user_full_name_no_name(self, mock_client):
        """Test get_current_user_full_name when user has no first/last name"""
        # Setup - Mock current user with empty names
        mock_client.me = {
            "first_name": "",
            "last_name": "",
            "username": "current_user",
            "email": "current@example.com"
        }
        
        # Execute
        result = content_health_utils.get_current_user_full_name(mock_client)
        
        # Assert - Should fall back to username
        assert result == "current_user"
    
    def test_get_content_success(self, mock_client, valid_content_response):
        """Test get_content when successful"""
        # Setup
        mock_client.content.get.return_value = valid_content_response
        guid = valid_content_response["guid"]
        
        # Execute
        result = get_content(mock_client, guid)
        
        # Assert
        assert result == valid_content_response
        mock_client.content.get.assert_called_once_with(guid)
    
    def test_get_content_error(self, mock_client, mock_format_error_message, mock_client_error):
        """Test get_content when there's an error"""
        # Setup
        guid = "invalid-guid"
        error_message = "Content not found"
        
        # Create client error and mock format_error_message
        client_error = mock_client_error(error_message)
        mock_client.content.get.side_effect = client_error
        
        # Use fixture to create format_error_message patch
        with mock_format_error_message(error_message):
            # Execute
            result = get_content(mock_client, guid)
            
            # Assert
            assert "title" in result
            assert result["title"] == f"{ERROR_PREFIX} {error_message}"
            assert result["guid"] == guid
            mock_client.content.get.assert_called_once_with(guid)
    
    def test_get_user_success(self, mock_client, valid_user_response):
        """Test get_user when successful"""
        # Setup
        user_guid = valid_user_response["guid"]
        mock_client.users.get.return_value = valid_user_response
        
        # Execute
        result = get_user(mock_client, user_guid)
        
        # Assert
        assert result == valid_user_response
        mock_client.users.get.assert_called_once_with(user_guid)
    
    def test_get_user_error(self, mock_client, mock_format_error_message, mock_client_error):
        """Test get_user when there's an error"""
        # Setup
        user_guid = "invalid-user-guid"
        error_message = "User not found"
        
        # Create client error and mock format_error_message
        client_error = mock_client_error(error_message)
        mock_client.users.get.side_effect = client_error
        
        # Use fixture to create format_error_message patch
        with mock_format_error_message(error_message):
            # Execute and Assert
            with pytest.raises(RuntimeError) as excinfo:
                get_user(mock_client, user_guid)
            
            assert "Error getting user:" in str(excinfo.value)
            assert error_message in str(excinfo.value)
            mock_client.users.get.assert_called_once_with(user_guid)


# Tests for validate function
class TestValidateFunction:

    @pytest.fixture
    def mock_response(self):
        """Create a mock response for requests.get"""
        response = MagicMock()
        response.status_code = 200
        return response

    def test_validate_success(self, mock_client, valid_content_response, valid_user_response, 
                          mock_response, connect_test_server, api_test_key):
        """Test validate when content exists and is accessible"""
        # Setup - content details
        guid = valid_content_response["guid"]
        mock_client.content.get.return_value = valid_content_response
        
        # Setup - owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request
        # Using fixtures for server and API key
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["name"] == valid_content_response["title"]
            assert result["status"] == STATUS_PASS
            assert result["http_code"] == 200
            assert result["owner_name"] == "Test Owner"
            assert result["owner_email"] == "owner@example.com"
            
            # Verify HTTP request was made correctly
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == valid_content_response["content_url"]
            assert kwargs["headers"]["Authorization"] == f"Key {api_test_key}"
            assert "ContentHealthMonitor" in kwargs["headers"]["User-Agent"]
    
    def test_validate_error_retrieving_content(self, mock_client, mock_format_error_message, 
                                     mock_client_error, connect_test_server, api_test_key):
        """Test validate when content can't be retrieved (e.g., invalid GUID)"""
        # Setup
        guid = "invalid-guid"
        error_message = "Content not found"
        
        # Create client error and mock format_error_message
        client_error = mock_client_error(error_message)
        mock_client.content.get.side_effect = client_error
        
        # Use fixture to create format_error_message patch
        with mock_format_error_message(error_message):
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["name"].startswith(ERROR_PREFIX)
            assert error_message in result["name"]
            assert result["status"] == STATUS_FAIL
            assert result["http_code"] == "Error retrieving content"
    
    def test_validate_http_error(self, mock_client, valid_content_response, valid_user_response, 
                          connect_test_server, api_test_key):
        """Test validate when content exists but HTTP check fails"""
        # Setup - content details
        guid = valid_content_response["guid"]
        mock_client.content.get.return_value = valid_content_response
        
        # Setup - owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request fails with 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('requests.get', return_value=mock_response):
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["name"] == valid_content_response["title"]
            assert result["status"] == STATUS_FAIL
            assert result["http_code"] == 404
    
    def test_validate_http_exception(self, mock_client, valid_content_response, valid_user_response,
                              connect_test_server, api_test_key):
        """Test validate when HTTP request raises an exception"""
        # Setup - content details
        guid = valid_content_response["guid"]
        mock_client.content.get.return_value = valid_content_response
        
        # Setup - owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request raises exception
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection refused")):
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["name"] == valid_content_response["title"]
            assert result["status"] == STATUS_FAIL
            assert "Connection refused" in result["http_code"]
    
    def test_validate_missing_content_url(self, mock_client, valid_content_response, valid_user_response, 
                                 mock_response, connect_test_server, api_test_key):
        """Test validate when content_url is missing"""
        # Setup - content details without content_url
        guid = valid_content_response["guid"]
        content_without_url = valid_content_response.copy()
        del content_without_url["content_url"]
        mock_client.content.get.return_value = content_without_url
        
        # Setup - owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["status"] == STATUS_PASS
            
            # Verify HTTP request was made with constructed URL
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == f"{connect_test_server}/content/{guid}"
    
    def test_validate_no_title_fallback_to_name(self, mock_client, valid_user_response, mock_response,
                                     connect_test_server, api_test_key):
        """Test validate when content has no title but has name"""
        # Setup - content details without title
        guid = "valid-guid-123"
        content_without_title = {
            "guid": guid,
            "name": "test_content_name",  # No title, just name
            "content_url": "https://connect.example.com/content/valid-guid-123/",
            "dashboard_url": "https://connect.example.com/content/valid-guid-123/",
            "owner_guid": "owner-guid-456",
            "app_role": "owner"
        }
        mock_client.content.get.return_value = content_without_title
        
        # Setup - owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request
        with patch('requests.get', return_value=mock_response):
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["name"] == "test_content_name"  # Should fall back to the name field
            assert result["status"] == STATUS_PASS
    
    def test_validate_owner_exception(self, mock_client, valid_content_response, mock_response,
                                connect_test_server, api_test_key):
        """Test validate when getting owner info raises an exception"""
        # Setup - content details
        guid = valid_content_response["guid"]
        mock_client.content.get.return_value = valid_content_response
        
        # Setup - owner details raises exception
        mock_client.users.get.side_effect = Exception("Error fetching owner")
        
        # Setup - HTTP request
        with patch('requests.get', return_value=mock_response):
            # Execute
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert
            assert result["guid"] == guid
            assert result["status"] == STATUS_PASS
            assert result["owner_name"] == ""  # Should be empty due to error
            assert result["owner_email"] == ""  # Should be empty due to error


# Tests for error helper functions
class TestErrorHelperFunctions:
    
    def test_has_error_with_error(self):
        """Test has_error with a result containing an error"""
        # Setup
        result = {
            "name": f"{ERROR_PREFIX} Something went wrong",
            "guid": "test-guid"
        }
        
        # Execute
        has_err = has_error(result)
        
        # Assert
        assert has_err
    
    def test_has_error_without_error(self):
        """Test has_error with a result not containing an error"""
        # Setup
        result = {
            "name": "Normal content",
            "guid": "test-guid"
        }
        
        # Execute
        has_err = has_error(result)
        
        # Assert
        assert not has_err
    
    def test_has_error_with_none(self):
        """Test has_error with None result"""
        # Execute
        has_err = has_error(None)
        
        # Assert
        assert not has_err
    
    def test_has_error_without_name(self):
        """Test has_error with a result missing the name field"""
        # Setup
        result = {
            "guid": "test-guid"
            # No name field
        }
        
        # Execute
        has_err = has_error(result)
        
        # Assert
        assert not has_err
    
    def test_extract_error_details_with_error(self):
        """Test extract_error_details with a result containing an error"""
        # Setup
        error_message = "Something went wrong"
        result = {
            "name": f"{ERROR_PREFIX} {error_message}",
            "guid": "test-guid"
        }
        
        # Execute
        error_details = extract_error_details(result)
        
        # Assert
        assert error_details is not None
        assert error_details["message"] == error_message
        assert error_details["guid"] == "test-guid"
    
    def test_extract_error_details_without_error(self):
        """Test extract_error_details with a result not containing an error"""
        # Setup
        result = {
            "name": "Normal content",
            "guid": "test-guid"
        }
        
        # Execute
        error_details = extract_error_details(result)
        
        # Assert
        assert error_details is None


# Tests for should_send_email function
class TestShouldSendEmailFunction:
    
    def test_should_send_email_with_error(self):
        """Test should_send_email when there's an error"""
        # Setup
        show_error = True
        content_result = None
        
        # Execute
        result = should_send_email(show_error, content_result)
        
        # Assert
        assert result
    
    def test_should_send_email_with_failed_validation(self):
        """Test should_send_email when content validation failed"""
        # Setup
        show_error = False
        content_result = {
            "status": STATUS_FAIL,
            "name": "Test Content",
            "guid": "test-guid"
        }
        
        # Execute
        result = should_send_email(show_error, content_result)
        
        # Assert
        assert result
    
    def test_should_not_send_email_with_passing_validation(self):
        """Test should_send_email when content validation passed"""
        # Setup
        show_error = False
        content_result = {
            "status": STATUS_PASS,
            "name": "Test Content",
            "guid": "test-guid"
        }
        
        # Execute
        result = should_send_email(show_error, content_result)
        
        # Assert
        assert not result
    
    def test_should_not_send_email_with_no_content_result(self):
        """Test should_send_email when no content result is available"""
        # Setup
        show_error = False
        content_result = None
        
        # Execute
        result = should_send_email(show_error, content_result)
        
        # Assert
        assert not result
    
    def test_should_not_send_email_with_invalid_content_result(self):
        """Test should_send_email when content result doesn't have status"""
        # Setup
        show_error = False
        content_result = {
            "name": "Test Content",
            "guid": "test-guid"
            # No status field
        }
        
        # Execute
        result = should_send_email(show_error, content_result)
        
        # Assert
        assert not result


# Scenario tests for all required cases
class TestScenarios:
    
    @patch.dict(os.environ, {}, clear=True)
    def test_scenario_no_canary_guid_env_var(self, mock_client):
        """Test scenario: No CANARY_GUID env var set
        
        Expected: If scheduled, DOES NOT send an email
        """
        # Setup - Reset module globals
        globals.show_instructions = False
        globals.instructions = []
        
        # Clear environment variable if it exists
        clear_env_var("MONITORED_CONTENT_GUID")
        
        # Execute - Try to get the env var
        result = get_env_var("MONITORED_CONTENT_GUID")
        
        # Assert - It should be empty and show instructions
        assert result == ""
        assert globals.show_instructions
        
        # For this scenario, show_instructions=True means the script won't proceed to validation,
        # so should_send_email would get show_error=False and content_result=None
        should_email = should_send_email(False, None)
        assert not should_email
    
    def test_scenario_invalid_guid(self, mock_client, mock_format_error_message, 
                               mock_client_error, connect_test_server, api_test_key):
        """Test scenario: Invalid GUID
        
        Expected: If scheduled, sends an email
        """
        # Setup - Invalid GUID
        guid = "invalid-guid-123"
        error_message = "Content not found"
        
        # Create client error and mock format_error_message
        client_error = mock_client_error(error_message)
        mock_client.content.get.side_effect = client_error
        
        # Use fixture to create format_error_message patch
        with mock_format_error_message(error_message):
            # Execute - Validate with invalid GUID
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert - Should return error in name field, leading to show_error=True
            assert result["name"].startswith(ERROR_PREFIX)
            assert has_error(result)
            
            # Based on content-health-monitor.qmd, if has_error is True, then show_error will be True
            show_error = True
            should_email = should_send_email(show_error, result)
            assert should_email
    
    def test_scenario_valid_guid_as_owner(self, mock_client, valid_content_response, valid_user_response,
                                   connect_test_server, api_test_key):
        """Test scenario: Valid GUID for content you are a owner of
        
        Expected: If content passes validation and scheduled, DOES NOT send an email
        """
        # Setup - Valid GUID with owner role
        guid = valid_content_response["guid"]
        content_with_owner = valid_content_response.copy()
        content_with_owner["app_role"] = "owner"
        mock_client.content.get.return_value = content_with_owner
        
        # Setup - Owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response):
            # Execute - Validate with owner role
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert - Should show success and include logs URL
            assert result["status"] == STATUS_PASS
            assert not has_error(result)
            assert "logs_url" in result and result["logs_url"]  # Should have logs URL for owner
            
            # Based on content-health-monitor.qmd
            show_error = False
            should_email = should_send_email(show_error, result)
            assert not should_email  # PASS status means no email
    
    def test_scenario_valid_guid_as_collaborator(self, mock_client, valid_content_response, valid_user_response,
                                        connect_test_server, api_test_key):
        """Test scenario: Valid GUID for content you are a collaborator of
        
        Expected: If content passes validation and scheduled, DOES NOT send an email
        """
        # Setup - Valid GUID with editor/collaborator role
        guid = valid_content_response["guid"]
        content_with_collab = valid_content_response.copy()
        content_with_collab["app_role"] = "editor"  # Collaborator role
        mock_client.content.get.return_value = content_with_collab
        
        # Setup - Owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response):
            # Execute - Validate with collaborator role
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert - Should show success and include logs URL
            assert result["status"] == STATUS_PASS
            assert not has_error(result)
            assert "logs_url" in result and result["logs_url"]  # Should have logs URL for collaborator
            
            # Based on content-health-monitor.qmd
            show_error = False
            should_email = should_send_email(show_error, result)
            assert not should_email  # PASS status means no email
    
    def test_scenario_valid_guid_as_viewer(self, mock_client, valid_content_response, valid_user_response,
                                    connect_test_server, api_test_key):
        """Test scenario: Valid GUID for content you are a viewer of
        
        Expected: If content passes validation and scheduled, DOES NOT send an email
        """
        # Setup - Valid GUID with viewer role
        guid = valid_content_response["guid"]
        content_with_viewer = valid_content_response.copy()
        content_with_viewer["app_role"] = "viewer"  # Viewer role
        mock_client.content.get.return_value = content_with_viewer
        
        # Setup - Owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response):
            # Execute - Validate with viewer role
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert - Should show success but no logs URL for viewer
            assert result["status"] == STATUS_PASS
            assert not has_error(result)
            assert "logs_url" in result and not result["logs_url"]  # Should NOT have logs URL for viewer
            
            # Based on content-health-monitor.qmd
            show_error = False
            should_email = should_send_email(show_error, result)
            assert not should_email  # PASS status means no email
    
    def test_scenario_valid_guid_no_access(self, mock_client, mock_format_error_message, 
                                     mock_client_error, connect_test_server, api_test_key):
        """Test scenario: Valid GUID for content you do not have access to
        
        Expected: If scheduled, sends an email (fails validation)
        """
        # Setup - Valid GUID but content access denied
        guid = "valid-but-no-access-guid"
        error_message = "Forbidden: User does not have permission to view this content"
        
        # Create client error and mock format_error_message
        client_error = mock_client_error(error_message, status_code=403, reason="Forbidden")
        mock_client.content.get.side_effect = client_error
        
        # Use fixture to create format_error_message patch
        with mock_format_error_message(error_message):
            # Execute - Validate with no access
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert - Should return error in name field, leading to show_error=True
            assert result["name"].startswith(ERROR_PREFIX)
            assert has_error(result)
            
            # Based on content-health-monitor.qmd, if has_error is True, then show_error will be True
            show_error = True
            should_email = should_send_email(show_error, result)
            assert should_email
    
    def test_scenario_valid_guid_fails_validation(self, mock_client, valid_content_response, valid_user_response,
                                          connect_test_server, api_test_key):
        """Test scenario: Valid GUID, content is published but fails validation
        
        Expected: If scheduled, sends an email
        """
        # Setup - Valid GUID
        guid = valid_content_response["guid"]
        mock_client.content.get.return_value = valid_content_response
        
        # Setup - Owner details
        mock_client.users.get.return_value = valid_user_response
        
        # Setup - HTTP request that fails validation with 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500  # Server error
        
        with patch('requests.get', return_value=mock_response):
            # Execute - Validate with failing content
            result = validate(mock_client, guid, connect_test_server, api_test_key)
            
            # Assert - Should show failure due to HTTP error
            assert result["status"] == STATUS_FAIL
            assert not has_error(result)  # Content exists but validation fails
            
            # Based on content-health-monitor.qmd
            show_error = False
            should_email = should_send_email(show_error, result)
            assert should_email  # FAIL status means send email


# Tests for report display HTML generation
class TestReportDisplay:
    
    def test_create_report_display_with_logs_url(self):
        """Test create_report_display when logs URL is available (owner/collaborator)"""
        # Setup - Result with logs_url (owner/collaborator)
        result_data = {
            "guid": "test-guid-123",
            "name": "Test Content",
            "status": STATUS_PASS,
            "http_code": 200,
            "logs_url": "https://connect.example.com/content/test-guid-123/logs",
            "dashboard_url": "https://connect.example.com/content/test-guid-123",
            "owner_name": "Test Owner",
            "owner_email": "owner@example.com"
        }
        check_time = "2023-01-01 12:00:00"
        current_user_name = "Test User"
        
        # Execute
        html_output = content_health_utils.create_report_display(result_data, check_time, current_user_name)
        
        # Assert
        assert html_output is not None
        # Check that the logs URL is included as a clickable link
        assert "View Logs</a>" in html_output
        assert result_data["logs_url"] in html_output
    
    def test_create_report_display_without_logs_url(self):
        """Test create_report_display when logs URL is not available (viewer)"""
        # Setup - Result without logs_url (viewer)
        result_data = {
            "guid": "test-guid-123",
            "name": "Test Content",
            "status": STATUS_PASS,
            "http_code": 200,
            "logs_url": "",  # Empty logs_url for viewer
            "dashboard_url": "https://connect.example.com/content/test-guid-123",
            "owner_name": "Test Owner",
            "owner_email": "owner@example.com"
        }
        check_time = "2023-01-01 12:00:00"
        current_user_name = "Viewer User"
        
        # Execute
        html_output = content_health_utils.create_report_display(result_data, check_time, current_user_name)
        
        # Assert
        assert html_output is not None
        # Check that the "log access restricted" message is shown with the current user's name
        assert f"Log access is restricted for {current_user_name}" in html_output
        assert "only available to the content owner and collaborators" in html_output
        # Ensure there's no logs link
        assert "View Logs</a>" not in html_output

# Test check_server_reachable function
class TestCheckServerReachable:
    
    def test_check_server_reachable_success(self, connect_test_server, api_test_key):
        """Test check_server_reachable when server is reachable"""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Execute
            result = check_server_reachable(connect_test_server, api_test_key)
            
            # Assert
            assert result
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == f"{connect_test_server}/__ping__"
            assert kwargs["headers"]["Authorization"] == f"Key {api_test_key}"
            assert kwargs["timeout"] == 5
    
    def test_check_server_reachable_error(self, connect_test_server, api_test_key):
        """Test check_server_reachable when server is not reachable"""
        # Setup
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Connection refused")) as mock_get:
            # Execute and Assert
            with pytest.raises(RuntimeError) as excinfo:
                check_server_reachable(connect_test_server, api_test_key)
            
            assert "Connect server at" in str(excinfo.value)
            assert "Connection refused" in str(excinfo.value)
            mock_get.assert_called_once()
    
    def test_check_server_reachable_http_error(self, connect_test_server, api_test_key):
        """Test check_server_reachable when server returns error status code"""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Execute and Assert
            with pytest.raises(RuntimeError) as excinfo:
                check_server_reachable(connect_test_server, api_test_key)
            
            assert "Connect server at" in str(excinfo.value)
            assert "500 Server Error" in str(excinfo.value)
            mock_get.assert_called_once()

