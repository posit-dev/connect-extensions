import os
import pytest
import posit.connect
from unittest.mock import MagicMock, patch

import content_health_utils
from content_health_utils import MonitorState, DEFAULT_USER_NAME

# Define fixtures to prepare the test environment

@pytest.fixture
def clean_environment():
    """Set up a clean environment for tests and restore after test completes"""
    # Save original environment
    original_env = os.environ.copy()
    
    # Create a clean environment with only essential variables
    os.environ.clear()
    # Re-add only PATH and essential system variables if needed
    if 'PATH' in original_env:
        os.environ['PATH'] = original_env['PATH']
    if 'PYTHONPATH' in original_env:
        os.environ['PYTHONPATH'] = original_env['PYTHONPATH']
        
    # Explicitly ensure these variables are not set
    for var in ['MONITORED_CONTENT', 'VAR1', 'VAR2', 'TEST_VAR']:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment after the test
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def state():
    """Create a state object for testing"""
    return MonitorState()

# Integration tests
def test_state_initialization():
    """
    Test that the MonitorState class initializes with correct default values.
    This simulates how state is created in the Quarto document.
    """
    # Create a state object and verify default values
    state = MonitorState()
    assert state.show_instructions is False
    assert state.instructions == []

def test_get_env_var_missing_variable(clean_environment, state):
    """
    Test that get_env_var behaves correctly when environment variable is missing.
    This simulates the case that was causing errors in Connect.
    """
    # Make sure the variable is not in environment
    if 'MONITORED_CONTENT' in os.environ:
        del os.environ['MONITORED_CONTENT']
    
    # Call the function that was failing
    value = content_health_utils.get_env_var('MONITORED_CONTENT', state)
    
    # Verify function behavior
    assert value == ""
    assert state.show_instructions is True
    assert len(state.instructions) == 1
    assert "Content Settings" in state.instructions[0]
    assert "<code>MONITORED_CONTENT</code>" in state.instructions[0]

def test_multiple_env_var_checks(clean_environment, state):
    """
    Test that checking multiple environment variables behaves correctly.
    This simulates the scenario in the Quarto document where multiple env vars are checked.
    """
    # Check several variables
    var1 = content_health_utils.get_env_var('VAR1', state)
    var2 = content_health_utils.get_env_var('VAR2', state)
    var3 = content_health_utils.get_env_var('MONITORED_CONTENT', state)
    
    # Verify function behavior
    assert var1 == ""
    assert var2 == ""
    assert var3 == ""
    assert state.show_instructions is True
    assert len(state.instructions) == 3

def test_env_var_exists(clean_environment, state):
    """
    Test that get_env_var behaves correctly when environment variable exists.
    """
    # Set environment variable
    os.environ['TEST_VAR'] = 'test_value'
    
    # Call the function
    value = content_health_utils.get_env_var('TEST_VAR', state)
    
    # Verify function behavior
    assert value == "test_value"
    assert state.show_instructions is False
    assert state.instructions == []

def test_user_name_with_instructions(clean_environment, state):
    """
    Test that the user's name is retrieved even when show_instructions is True.
    This test verifies the fix for the issue where publisher's name wasn't 
    showing in the About box when setup instructions were displayed.
    """
    # Set state to show instructions
    state.show_instructions = True
    
    # Create a mock client
    mock_client = MagicMock()
    mock_client.me = {
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser"
    }
    
    # Get the user name
    user_name = content_health_utils.get_current_user_full_name(mock_client)
    
    # Verify user name is retrieved correctly
    assert user_name == "Test User"
    # Instructions state should still be True
    assert state.show_instructions is True

def test_client_initialization_with_env_vars(clean_environment):
    """
    Test the scenario where environment variables are present and client can be initialized.
    This tests our fix that attempts to get the user name when env vars are available,
    even if showing instructions for other reasons.
    """
    # Set required environment variables
    os.environ['CONNECT_SERVER'] = 'https://connect.example.com'
    os.environ['CONNECT_API_KEY'] = 'test_api_key'
    
    # Create state and other required variables
    state = MonitorState()
    state.show_instructions = True  # Set to True for other reasons (e.g., missing MONITORED_CONTENT_GUID)
    current_user_name = DEFAULT_USER_NAME  # Default
    
    # Mock the client and get_current_user_full_name function
    mock_client = MagicMock()
    
    with patch('posit.connect.Client', return_value=mock_client):
        with patch('content_health_utils.get_current_user_full_name', return_value="Test User"):
            # This simulates the client initialization code in content-health-monitor.qmd
            client = None
            has_connect_env_vars = os.environ.get('CONNECT_SERVER') and os.environ.get('CONNECT_API_KEY')
            
            if has_connect_env_vars:
                try:
                    # Instantiate client
                    client = posit.connect.Client()
                    
                    # Try to get user name
                    try:
                        user_name = content_health_utils.get_current_user_full_name(client)
                        if user_name:
                            current_user_name = user_name
                    except Exception:
                        pass
                except ValueError:
                    pass
            
            # Assert that client was created and user name was updated
            assert client is not None
            assert current_user_name == "Test User"
            # Instructions state should still be True
            assert state.show_instructions is True

def test_client_initialization_without_env_vars(clean_environment):
    """
    Test the scenario where environment variables are missing and client cannot be initialized.
    This verifies that we don't attempt to create the client in this case,
    and the default publisher name is preserved.
    """
    # Make sure environment variables are not set
    if 'CONNECT_SERVER' in os.environ:
        del os.environ['CONNECT_SERVER']
    if 'CONNECT_API_KEY' in os.environ:
        del os.environ['CONNECT_API_KEY']
    
    # Create state and other required variables
    state = MonitorState()
    state.show_instructions = True
    current_user_name = DEFAULT_USER_NAME  # Default
    
    # Mock client creation to ensure it's never called
    mock_client_init = MagicMock(side_effect=ValueError("Should not be called"))
    
    with patch('posit.connect.Client', mock_client_init):
        # This simulates the client initialization code in content-health-monitor.qmd
        client = None
        connect_server = os.environ.get('CONNECT_SERVER', '')
        api_key = os.environ.get('CONNECT_API_KEY', '')
        has_connect_env_vars = connect_server and api_key
        
        if has_connect_env_vars:
            try:
                # Instantiate client
                client = posit.connect.Client()
                
                # Try to get user name
                try:
                    user_name = content_health_utils.get_current_user_full_name(client)
                    if user_name:
                        current_user_name = user_name
                except Exception:
                    pass
            except ValueError:
                pass
        
        # Assert that client was not created and default name is preserved
        assert client is None
        assert current_user_name == DEFAULT_USER_NAME
        assert not has_connect_env_vars  # Verify that we correctly detected missing env vars (empty string is falsy)
        
        # Verify that Client constructor was never called
        mock_client_init.assert_not_called()

def test_connection_error_handling(clean_environment):
    """
    Test that connection errors are properly handled and don't show up at the top of the report.
    The get_current_user_full_name function should handle errors internally and return "Unknown".
    """
    # Set required environment variables
    os.environ['CONNECT_SERVER'] = 'http://localhost:3939'
    os.environ['CONNECT_API_KEY'] = 'test_api_key'
    
    # Create state and other required variables
    state = MonitorState()
    
    # Create a test scenario where get_current_user_full_name will return "Unknown" for connection issues
    with patch('content_health_utils.get_current_user_full_name', return_value="Unknown"):
        # Mock the client
        mock_client = MagicMock()
        
        with patch('posit.connect.Client', return_value=mock_client):
            # This simulates the code in content-health-monitor.qmd
            client = None
            current_user_name = DEFAULT_USER_NAME  # Default
            connect_server = os.environ.get('CONNECT_SERVER', '')
            api_key = os.environ.get('CONNECT_API_KEY', '')
            has_connect_env_vars = connect_server and api_key
            
            if has_connect_env_vars:
                try:
                    # Instantiate client
                    client = posit.connect.Client()
                    
                    # Get current user's full name - function handles errors internally
                    user_name = content_health_utils.get_current_user_full_name(client)
                    if user_name != "Unknown":  # Only update if we got a valid name
                        current_user_name = user_name
                        
                except ValueError as e:
                    if not state.show_instructions:
                        state.show_instructions = True
                        state.instructions.append(f"<b>Error initializing Connect client:</b> {str(e)}")
            
            # Assert that client was created but user name was not updated due to error
            assert client is not None  # Client creation succeeds
            assert current_user_name == DEFAULT_USER_NAME  # Name should remain the default since user_name is "Unknown"
