import os
import sys
import importlib
import unittest
import globals

class IntegrationTests(unittest.TestCase):
    """
    Integration tests for content_health_utils module.
    
    These tests verify the module behaves correctly when imported and used
    in different environments, without any special setup or mocking.
    """
    
    def setUp(self):
        """Prepare for each test by clearing any cached modules and environment variables"""
        # Remove the module from sys.modules if it's there to ensure fresh import
        if 'content_health_utils' in sys.modules:
            del sys.modules['content_health_utils']
        
        # Reset globals module state
        globals.show_instructions = False
        globals.instructions = []
        
        # Save original environment
        self.original_env = os.environ.copy()
        
        # Create a clean environment with only essential variables
        os.environ.clear()
        # Re-add only PATH and essential system variables if needed
        if 'PATH' in self.original_env:
            os.environ['PATH'] = self.original_env['PATH']
        if 'PYTHONPATH' in self.original_env:
            os.environ['PYTHONPATH'] = self.original_env['PYTHONPATH']
            
        # Explicitly ensure these variables are not set
        for var in ['MONITORED_CONTENT_GUID', 'VAR1', 'VAR2', 'TEST_VAR']:
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Clean up after each test"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_direct_import_without_setup(self):
        """
        Test that the module can be imported without any setup.
        This simulates how the module is loaded in Connect.
        """
        # This should not raise any exceptions
        import content_health_utils
        
        # Verify globals are initialized with default values
        self.assertFalse(globals.show_instructions)
        self.assertEqual(globals.instructions, [])
    
    def test_get_env_var_missing_variable(self):
        """
        Test that get_env_var behaves correctly when environment variable is missing.
        This simulates the case that was causing errors in Connect.
        """
        # Make sure the variable is not in environment
        if 'MONITORED_CONTENT_GUID' in os.environ:
            del os.environ['MONITORED_CONTENT_GUID']
        
        # Import the module
        import content_health_utils
        
        # Call the function that was failing
        value = content_health_utils.get_env_var('MONITORED_CONTENT_GUID')
        
        # Verify function behavior
        self.assertEqual(value, "")
        self.assertTrue(globals.show_instructions)
        self.assertEqual(len(globals.instructions), 1)
        self.assertIn("Content Settings", globals.instructions[0])
        self.assertIn("<code>MONITORED_CONTENT_GUID</code>", globals.instructions[0])
    
    def test_multiple_env_var_checks(self):
        """
        Test that checking multiple environment variables behaves correctly.
        This simulates the scenario in the Quarto document where multiple env vars are checked.
        """
        # Import the module
        import content_health_utils
        
        # Check several variables
        var1 = content_health_utils.get_env_var('VAR1')
        var2 = content_health_utils.get_env_var('VAR2')
        var3 = content_health_utils.get_env_var('MONITORED_CONTENT_GUID')
        
        # Verify function behavior
        self.assertEqual(var1, "")
        self.assertEqual(var2, "")
        self.assertEqual(var3, "")
        self.assertTrue(globals.show_instructions)
        self.assertEqual(len(globals.instructions), 3)
    
    def test_reimport_behavior(self):
        """
        Test that reimporting the module preserves global state.
        This simulates how modules behave in Python's import system.
        """
        # First import
        import content_health_utils
        
        # Modify global state
        globals.show_instructions = True
        globals.instructions = ["Test instruction"]
        
        # Reimport using importlib
        importlib.reload(content_health_utils)
        
        # Verify global state is preserved (Python caches modules)
        self.assertTrue(globals.show_instructions)
        self.assertEqual(globals.instructions, ["Test instruction"])
    
    def test_env_var_exists(self):
        """
        Test that get_env_var behaves correctly when environment variable exists.
        """
        # Set environment variable
        os.environ['TEST_VAR'] = 'test_value'
        
        # Import the module
        import content_health_utils
        
        # Call the function
        value = content_health_utils.get_env_var('TEST_VAR')
        
        # Verify function behavior
        self.assertEqual(value, "test_value")
        self.assertFalse(globals.show_instructions)
        self.assertEqual(globals.instructions, [])


if __name__ == '__main__':
    unittest.main()
