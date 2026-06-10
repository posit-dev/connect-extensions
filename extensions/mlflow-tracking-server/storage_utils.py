import logging

logger = logging.getLogger(__name__)


def detect_storage_backend(artifacts_destination: str) -> str:
    """Detect the storage backend type from the artifacts destination.

    Parameters
    ----------
    artifacts_destination : str
        The artifacts destination URI

    Returns
    -------
    str
        One of: 'local', 'aws', 'azure', 'gcp'
    """
    artifacts_destination = artifacts_destination.lower()

    if artifacts_destination.startswith('s3://') or artifacts_destination.startswith('s3a://'):
        return 'aws'
    elif (artifacts_destination.startswith('wasbs://') or
          artifacts_destination.startswith('abfss://') or
          'blob.core.windows.net' in artifacts_destination or
          'dfs.core.windows.net' in artifacts_destination):
        return 'azure'
    elif artifacts_destination.startswith('gs://'):
        return 'gcp'
    else:
        return 'local'


# ====================================================================
# ARTIFACT STORAGE OAUTH INTEGRATION
# ====================================================================

def get_azure_storage_token():
    """Fetch a fresh Azure storage access token from Posit Connect.

    Returns
    -------
    tuple[str, int] | None
        Tuple of (access_token, expires_on_timestamp), or None if fetch failed
    """
    try:
        from posit.connect import Client
        import time

        print("Fetching Azure storage token from Posit Connect...")
        client = Client()
        content = client.content.get()

        # Find Azure service account integration
        association = content.oauth.associations.find_by(
            integration_type="azure",
            auth_type="Service Account"
        )

        if not association:
            print("ERROR: No Azure Service Account integration found")
            return None

        # Get Azure credentials for storage
        # Use storage scope: https://storage.azure.com/.default
        credentials = client.oauth.get_content_credentials(
            audience=association['oauth_integration_guid']
        )

        access_token = credentials.get('access_token')
        if not access_token:
            print("ERROR: No access token received from Azure integration")
            return None

        # Calculate expiration time (tokens typically expire in 1 hour)
        # If expires_in is provided, use it; otherwise default to 3600 seconds
        expires_in = credentials.get('expires_in', 3600)
        expires_on = int(time.time()) + expires_in

        print(f"Azure storage token fetched successfully, expires at {expires_on}")
        return (access_token, expires_on)

    except Exception as e:
        print(f"ERROR: Failed to get Azure storage token: {e}")
        return None


def get_aws_storage_credentials():
    """Fetch fresh AWS storage credentials from Posit Connect.

    Returns
    -------
    dict | None
        Dictionary with aws_access_key_id, aws_secret_access_key, aws_session_token,
        or None if fetch failed
    """
    try:
        from posit.connect import Client
        from posit.connect.external.aws import get_content_credentials

        print("Fetching AWS storage credentials from Posit Connect...")
        client = Client()
        credentials = get_content_credentials(client)

        if not credentials:
            print("ERROR: Failed to get AWS credentials")
            return None

        print(f"AWS storage credentials fetched successfully, expires at {credentials.get('expiration', 'unknown')}")
        return credentials

    except Exception as e:
        print(f"ERROR: Failed to get AWS storage credentials: {e}")
        return None


# ====================================================================
# AZURE BLOB STORAGE CUSTOM ARTIFACT REPOSITORY
# ====================================================================

try:
    import time
    import threading
    from urllib.parse import urlparse
    from azure.core.credentials import AccessToken
    from azure.storage.blob import BlobServiceClient
    from mlflow.store.artifact.azure_blob_artifact_repo import AzureBlobArtifactRepository

    class RefreshingTokenCredential:
        """A thread-safe credential that auto-refreshes an OAuth2 token for Azure."""

        def __init__(self, refresh_function):
            """Initialize with a function that returns (token, expires_on)."""
            self._refresh_function = refresh_function
            self._access_token = None
            self._expires_on = 0
            self._lock = threading.Lock()

        def get_token(self, *scopes, **kwargs) -> AccessToken:
            """Get a valid access token, refreshing if necessary."""
            with self._lock:
                # Refresh token 5 minutes before expiration
                buffer_seconds = 300
                if not self._access_token or time.time() > (self._expires_on - buffer_seconds):
                    result = self._refresh_function()
                    if result:
                        new_token, new_expires_on = result
                        self._access_token = new_token
                        self._expires_on = new_expires_on
                    else:
                        print("ERROR: Failed to refresh Azure storage token")

                return AccessToken(self._access_token, self._expires_on)


    class TokenAuthAzureBlobRepo(AzureBlobArtifactRepository):
        """Custom Azure Blob Storage repository that uses OAuth token authentication.

        For wasbs:// URIs (Azure Blob Storage).
        """

        def __init__(self, artifact_uri: str, tracking_uri: str = None, registry_uri: str = None):
            """Initialize with auto-refreshing OAuth token credential."""
            print(f"Initializing TokenAuthAzureBlobRepo for {artifact_uri}")

            # Create auto-refreshing credential
            credential = RefreshingTokenCredential(refresh_function=get_azure_storage_token)

            # Parse the artifact URI to get the account URL
            parsed_uri = urlparse(artifact_uri)
            account_url = f"https://{parsed_uri.hostname}"

            # Create custom BlobServiceClient with OAuth token
            custom_client = BlobServiceClient(account_url=account_url, credential=credential)

            # Initialize parent class with custom client
            super().__init__(
                artifact_uri=artifact_uri,
                client=custom_client,
                tracking_uri=tracking_uri,
                registry_uri=registry_uri,
            )

            print(f"TokenAuthAzureBlobRepo initialized successfully for {account_url}")

    # Export the class for registration
    AZURE_BLOB_REPO_CLASS = TokenAuthAzureBlobRepo

except ImportError as e:
    print(f"WARNING: Could not import Azure Blob Storage dependencies: {e}")
    AZURE_BLOB_REPO_CLASS = None


# ====================================================================
# AZURE DATA LAKE STORAGE GEN2 CUSTOM ARTIFACT REPOSITORY
# ====================================================================

try:
    from mlflow.store.artifact.azure_data_lake_artifact_repo import AzureDataLakeArtifactRepository

    class TokenAuthAzureDataLakeRepo(AzureDataLakeArtifactRepository):
        """Custom Azure Data Lake Storage Gen2 repository that uses OAuth token authentication.

        For abfss:// URIs (Azure Data Lake Storage Gen2).
        Uses credential_refresh_def to periodically refresh OAuth tokens.
        """

        def __init__(self, artifact_uri: str, tracking_uri: str = None, registry_uri: str = None):
            """Initialize with auto-refreshing OAuth token credential."""
            print(f"Initializing TokenAuthAzureDataLakeRepo for {artifact_uri}")

            # Create auto-refreshing credential
            credential = RefreshingTokenCredential(refresh_function=get_azure_storage_token)

            # Define credential refresh function for the parent class
            def credential_refresh_def():
                """Return new credentials in the format expected by AzureDataLakeArtifactRepository."""
                # Create a new credential instance with the refreshing function
                return {"credential": RefreshingTokenCredential(refresh_function=get_azure_storage_token)}

            # Initialize parent class with credential and refresh function
            super().__init__(
                artifact_uri=artifact_uri,
                credential=credential,
                credential_refresh_def=credential_refresh_def,
                tracking_uri=tracking_uri,
            )

            print("TokenAuthAzureDataLakeRepo initialized successfully")

    # Export the class for registration
    AZURE_DATA_LAKE_REPO_CLASS = TokenAuthAzureDataLakeRepo

except ImportError as e:
    print(f"WARNING: Could not import Azure Data Lake Storage dependencies: {e}")
    AZURE_DATA_LAKE_REPO_CLASS = None


# ====================================================================
# S3 CUSTOM ARTIFACT REPOSITORY
# ====================================================================

try:
    from mlflow.store.artifact.s3_artifact_repo import S3ArtifactRepository
    import boto3

    class RefreshingS3ArtifactRepository(S3ArtifactRepository):
        """Custom S3 artifact repository that refreshes OAuth credentials every hour.

        Overrides _get_s3_client() to fetch fresh temporary credentials from Posit Connect
        OAuth integration on each S3 operation, with automatic refresh every hour.
        This ensures credentials remain valid even when repository instances are cached.
        """

        def __init__(self, artifact_uri: str, tracking_uri: str = None, registry_uri: str = None):
            """Initialize with OAuth-based credential management.

            Does not fetch credentials at initialization - instead, credentials are fetched
            on-demand when S3 operations are performed via _get_s3_client().
            """
            print(f"Initializing RefreshingS3ArtifactRepository for {artifact_uri}")

            # Store timestamp for credential refresh tracking
            self._credentials_fetched_at = 0
            self._credential_refresh_interval = 3600  # Refresh every hour
            self._cached_s3_client = None

            # Initialize parent without credentials - we'll override get_s3_client
            super().__init__(
                artifact_uri=artifact_uri,
                tracking_uri=tracking_uri,
            )

            print("RefreshingS3ArtifactRepository initialized successfully")

        def _get_s3_client(self):
            """Override to fetch fresh credentials from OAuth integration.

            This method is called by MLflow whenever S3 operations are performed,
            ensuring credentials are refreshed as needed.
            """
            import time

            # Check if we need to refresh credentials (every hour or if no client cached)
            current_time = time.time()
            if (self._cached_s3_client is None or
                current_time - self._credentials_fetched_at > self._credential_refresh_interval):
                print("Fetching fresh AWS credentials for S3 access...")
                temp_creds = get_aws_storage_credentials()

                if temp_creds:
                    # Create S3 client with fresh temporary credentials
                    self._cached_s3_client = boto3.client(
                        's3',
                        aws_access_key_id=temp_creds["aws_access_key_id"],
                        aws_secret_access_key=temp_creds["aws_secret_access_key"],
                        aws_session_token=temp_creds["aws_session_token"],
                    )
                    self._credentials_fetched_at = current_time
                    print("S3 client created with fresh OAuth credentials")
                else:
                    print("ERROR: Failed to fetch AWS credentials from OAuth integration")
                    print("Falling back to default credentials (this may fail if no valid credentials available)")
                    # Only fall back to parent if we have no cached client
                    if self._cached_s3_client is None:
                        return super()._get_s3_client()

            # Return the cached client with OAuth credentials
            return self._cached_s3_client

    # Export the class for registration
    S3_REPO_CLASS = RefreshingS3ArtifactRepository

except ImportError as e:
    print(f"WARNING: Could not import S3 dependencies: {e}")
    S3_REPO_CLASS = None


# ====================================================================
# OAUTH INTEGRATION CHECKS
# ====================================================================

def check_aws_oauth_integration():
    """Check if AWS OAuth integration is available for this content.

    Returns
    -------
    bool
        True if AWS OAuth integration is available, False otherwise
    """
    try:
        from posit.connect import Client
        from posit.connect.external.aws import get_content_credentials

        client = Client()
        credentials = get_content_credentials(client)
        return credentials is not None

    except ImportError:
        return False
    except Exception:
        return False


def check_azure_oauth_integration():
    """Check if Azure OAuth integration is available for this content.

    Returns
    -------
    bool
        True if Azure OAuth integration is available, False otherwise
    """
    try:
        from posit.connect import Client

        client = Client()
        content = client.content.get()

        # Find Azure service account integration
        association = content.oauth.associations.find_by(
            integration_type="azure",
            auth_type="Service Account"
        )

        return association is not None

    except ImportError:
        return False
    except Exception:
        return False


# ====================================================================
# ARTIFACT REPOSITORY REGISTRATION
# ====================================================================

def register_custom_artifact_repositories(storage_backend: str):
    """Register custom artifact repositories with MLflow's registry if OAuth integration exists.

    This function checks for OAuth integration availability and only registers custom repositories
    if an integration is found. Otherwise, MLflow will use default credentials (env vars, IAM roles, etc.)

    Parameters
    ----------
    storage_backend : str
        The storage backend type ('aws', 'azure', 'gcp', or 'local')

    Returns
    -------
    bool
        True if custom repos were registered, False if no OAuth integration or registration failed
    """
    try:
        from mlflow.store.artifact.artifact_repository_registry import _artifact_repository_registry

        registered = False

        # Check for AWS OAuth integration
        if storage_backend == 'aws':
            if not check_aws_oauth_integration():
                print("No AWS OAuth integration found - using default credentials (env vars, IAM role, etc.)")
                return False

            if S3_REPO_CLASS:
                print("AWS OAuth integration detected - registering custom S3 artifact repository...")
                _artifact_repository_registry.register("s3", S3_REPO_CLASS)
                print("Custom S3 artifact repository registered successfully")
                registered = True
            else:
                print("WARNING: S3 artifact repository class not available")
                return False

        # Check for Azure OAuth integration
        elif storage_backend == 'azure':
            if not check_azure_oauth_integration():
                print("No Azure OAuth integration found - using default credentials (env vars, managed identity, etc.)")
                return False

            print("Azure OAuth integration detected - registering custom Azure artifact repositories...")

            # Register Azure Blob Storage repository (wasbs://)
            if AZURE_BLOB_REPO_CLASS:
                _artifact_repository_registry.register("wasbs", AZURE_BLOB_REPO_CLASS)
                print("  - Registered Azure Blob Storage repository (wasbs://)")
                registered = True
            else:
                print("  WARNING: Azure Blob Storage repository class not available")

            # Register Azure Data Lake Gen2 repository (abfss://)
            if AZURE_DATA_LAKE_REPO_CLASS:
                _artifact_repository_registry.register("abfss", AZURE_DATA_LAKE_REPO_CLASS)
                print("  - Registered Azure Data Lake Storage Gen2 repository (abfss://)")
                registered = True
            else:
                print("  WARNING: Azure Data Lake Storage Gen2 repository class not available")

            if not registered:
                print("ERROR: No Azure artifact repository classes available")
                return False

            print("Custom Azure artifact repositories registered successfully")

        return registered

    except ImportError:
        print("ERROR: MLflow not available, cannot register artifact repositories")
        return False
    except Exception as e:
        print(f"ERROR: Failed to register custom artifact repositories: {e}")
        import traceback
        print(traceback.format_exc())
        return False
