import os
import time
from pathlib import Path
from posit import connect
import requests


class TestExtensionDeployment:
    def setup_method(self):
        """Set up test by creating a content placeholder."""
        self.client = connect.Client()
        self.content = self.client.content.create()

    def teardown_method(self):
        """Clean up any content created during the test."""
        self.content.delete()
        assert self.client.content.count() == 0

    def test_extension_deploys(self):
        """Test that an Extension can be deployed to Posit Connect."""
        # Get required environment variables
        extension_name = os.getenv("EXTENSION_NAME")

        # Get the bundle path using the container mount specified in compose.yaml
        bundle_path = Path("/connect-extensions/integration/bundles") / f"{extension_name}.tar.gz"

        # Create bundle
        bundle = self.content.bundles.create(str(bundle_path))

        # Deploy bundle and log the time it takes
        deploy_start = time.time()
        task = bundle.deploy()
        task.wait_for()
        deploy_time = time.time() - deploy_start
        print(f"Bundle deployment completed after {deploy_time:.1f}s")

        # Verify deployment was successful
        assert task.is_finished is True
        assert task.error_code == 0
        assert task.error_message == ""

        # Get the content after deployment
        self.content = self.client.content.get(self.content["guid"])

        # TODO will this work for every content type?
        # TODO we discussed that all content MUST have fallback for success, so we *should* be able to only check for 200
        # Verify the app executed/rendered successfully by making a request to its dashboard URL (up to 30 seconds)
        max_retries = 6
        retry_delay = 5
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                response = requests.get(self.content["content_url"])
                elapsed = time.time() - start_time
                
                # 500+ errors mean the content isn't running
                if response.status_code >= 500:
                    if attempt == max_retries - 1:
                        raise AssertionError(
                            f"Content failed to start. Server error {response.status_code}: {response.text}"
                        )
                else:
                    print(f"Content validated successfully after {elapsed:.1f}s with status={response.status_code}")
                    break
            except requests.RequestException as e:
                elapsed = time.time() - start_time
                print(f"Attempt {attempt + 1}/{max_retries} after {elapsed:.1f}s: {str(e)}")
                if attempt == max_retries - 1:
                    raise AssertionError(
                        f"Failed to access content after {max_retries} attempts ({elapsed:.1f}s): {e}"
                    )
            time.sleep(retry_delay)
