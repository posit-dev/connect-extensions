import os
import time
from pathlib import Path
from urllib.parse import urlparse
from posit import connect
import requests

# Configuration constants - could be moved to environment variables
MAX_RETRIES = 6
RETRY_DELAY = 5
BUNDLE_BASE_PATH = "/connect-extensions/integration/bundles"

class TestExtensionDeployment:
    def setup_method(self):
        """Set up test by creating a content placeholder and validating environment."""
        # Get and validate required environment variables
        self.extension_name = os.getenv("EXTENSION_NAME")
        self.api_key = os.getenv('CONNECT_API_KEY')
        
        if not self.extension_name:
            raise ValueError("EXTENSION_NAME environment variable must be set")
        if not self.api_key:
            raise ValueError("CONNECT_API_KEY environment variable must be set")

        # Initialize Connect client and create placeholder content
        self.client = connect.Client()
        self.content = self.client.content.create()
        
        # Parse URL and reconstruct base for API calls
        parsed = urlparse(self.content["content_url"])
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Store initial content GUID for verification in teardown
        self.content_guid = self.content["guid"]

    def teardown_method(self):
        """Clean up any content created during the test."""
        self.content.delete()
        assert self.client.content.count() == 0, "Content not deleted after test"

    def test_extension_deploys(self):
        """Test that an Extension can be deployed and started successfully in Posit Connect."""
        # Get the bundle path using the container mount path
        bundle_path = Path(BUNDLE_BASE_PATH) / f"{self.extension_name}.tar.gz"
        if not bundle_path.exists():
            raise FileNotFoundError(f"Extension bundle not found at {bundle_path}")

        # Create bundle and deploy
        bundle = self.content.bundles.create(str(bundle_path))
        
        # Deploy bundle and track timing
        deploy_start = time.time()
        task = bundle.deploy()
        task.wait_for()
        deploy_time = time.time() - deploy_start
        print(f"Bundle deployment completed after {deploy_time:.1f}s")

        # Verify deployment succeeded
        assert task.is_finished is True, "Deployment task didn't finish"
        assert task.error_code == 0, f"Deployment failed with code {task.error_code}: {task.error_message}"
        
        # Refresh content after deployment
        self.content = self.client.content.get(self.content["guid"])

        # Start validation loop - ensure app starts and returns HTTP 200
        self._validate_content_starts()

    def _validate_content_starts(self):
        """Verify the content starts correctly with retries."""
        start_time = time.time()
        headers = {"Authorization": f"Key {self.api_key}"}
        
        for attempt in range(MAX_RETRIES):
            try:
                # Request the content URL
                response = requests.get(self.content["content_url"], headers=headers)
                elapsed = time.time() - start_time
                
                # Success case
                if response.status_code == 200:
                    print(f"Content validated successfully after {elapsed:.1f}s")
                    return
                
                # If not the last attempt, log status and retry
                if attempt < MAX_RETRIES - 1:
                    print(f"Attempt {attempt+1}/{MAX_RETRIES}: Status {response.status_code}, retrying...")
                    time.sleep(RETRY_DELAY)
                    continue
                
                # Final attempt failed - fetch logs and raise error
                self._fetch_and_print_job_logs()
                
                # Include response text in error message
                raise AssertionError(
                    f"Content failed to start after {elapsed:.1f}s. Got status {response.status_code} but expected 200. See the job logs for detail."
                )
                
            except requests.RequestException as e:
                elapsed = time.time() - start_time
                raise AssertionError(f"Failed to access content after {elapsed:.1f}s: {e}")
    
    def _fetch_and_print_job_logs(self):
        """Helper to fetch and print job logs for debugging."""
        try:
            # Get the most recent job
            jobs_response = requests.get(
                f"{self.base_url}/__api__/v1/content/{self.content['guid']}/jobs",
                headers={"Authorization": f"Key {self.api_key}"}
            )
            jobs = jobs_response.json()
            
            if not jobs:
                print("No jobs found for content")
                return
                
            job_key = jobs[0]["key"]
            
            # Get the job logs
            log_response = requests.get(
                f"{self.base_url}/__api__/v1/content/{self.content['guid']}/jobs/{job_key}/log",
                headers={"Authorization": f"Key {self.api_key}"}
            )
            logs = log_response.json()
            
            print(f"Job logs for job {job_key}:")
            if "entries" in logs and logs["entries"]:
                for entry in logs["entries"]:
                    timestamp = entry.get("timestamp", "")
                    message = entry.get("data", "")
                    print(f"    {timestamp} - {message}")
            else:
                print("No log entries found")
                
        except Exception as e:
            print(f"Error fetching job logs: {e}")
