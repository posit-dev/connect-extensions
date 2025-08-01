import os
import pytest

import content_health_utils
from content_health_utils import MonitorState

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
    for var in ['MONITORED_CONTENT_GUID', 'VAR1', 'VAR2', 'TEST_VAR']:
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
    if 'MONITORED_CONTENT_GUID' in os.environ:
        del os.environ['MONITORED_CONTENT_GUID']
    
    # Call the function that was failing
    value = content_health_utils.get_env_var('MONITORED_CONTENT_GUID', state)
    
    # Verify function behavior
    assert value == ""
    assert state.show_instructions is True
    assert len(state.instructions) == 1
    assert "Content Settings" in state.instructions[0]
    assert "<code>MONITORED_CONTENT_GUID</code>" in state.instructions[0]

def test_multiple_env_var_checks(clean_environment, state):
    """
    Test that checking multiple environment variables behaves correctly.
    This simulates the scenario in the Quarto document where multiple env vars are checked.
    """
    # Check several variables
    var1 = content_health_utils.get_env_var('VAR1', state)
    var2 = content_health_utils.get_env_var('VAR2', state)
    var3 = content_health_utils.get_env_var('MONITORED_CONTENT_GUID', state)
    
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
