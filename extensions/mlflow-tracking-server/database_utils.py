import os
import logging
import re

logger = logging.getLogger(__name__)


# ====================================================================
# UTILITY FUNCTIONS
# ====================================================================

def mask_credentials(uri):
    """Mask sensitive credentials in URIs for logging."""
    if not uri:
        return uri
    # Mask database passwords in URIs like postgresql://user:password@host:port/db
    masked = re.sub(r'(://[^:]+:)[^@]+(@)', r'\1****\2', uri)
    return masked


def detect_database_backend(db_uri: str) -> str:
    """Detect the database backend type from the connection URI.

    Parameters
    ----------
    db_uri : str
        The database URI

    Returns
    -------
    str
        One of: 'local', 'aws_rds', 'azure_sql', 'standard'
    """

    # Only detect AWS RDS if the RDS_ENDPOINT environment variable is set
    # This prevents overwriting standard connection strings that happen to use RDS
    if os.getenv('RDS_ENDPOINT'):
        return 'aws_rds'

    # Only detect Azure SQL if the AZURE_SQL_SERVER environment variable is set
    # This prevents overwriting standard connection strings that happen to use Azure SQL
    if os.getenv('AZURE_SQL_SERVER'):
        return 'azure_sql'

    if not db_uri or db_uri.startswith('sqlite://'):
        return 'local'

    # Standard connection string with username:password
    return 'standard'


# ====================================================================
# OAUTH INTEGRATION CHECKS
# ====================================================================

def check_aws_rds_oauth_integration():
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


def check_azure_sql_oauth_integration():
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
# DATABASE CONNECTION SETUP
# ====================================================================

def setup_aws_rds_connection():
    """Setup AWS RDS connection using IAM authentication.

    Returns
    -------
    str | None
        Connection string without token, or None if setup failed
    """
    try:
        from posit.connect import Client
        from posit.connect.external.aws import get_content_credentials

        print("Setting up AWS RDS connection with IAM authentication")

        # Get required environment variables
        rds_endpoint = os.getenv("RDS_ENDPOINT")
        rds_port = int(os.getenv("RDS_PORT", "5432"))
        rds_database = os.getenv("RDS_DATABASE", "mlflow")
        rds_username = os.getenv("RDS_USERNAME", "postgres")
        db_type = os.getenv("RDS_DB_TYPE", "postgresql")

        if not all([rds_endpoint, rds_database, rds_username]):
            print("ERROR: Missing required RDS environment variables")
            return None

        # Verify we can get credentials
        client = Client()
        aws_credentials = get_content_credentials(client)

        if not aws_credentials:
            print("ERROR: Failed to get AWS credentials from Connect")
            return None

        print("AWS RDS credentials verified")

        # Build connection string without password but with SSL mode required
        # Token will be injected by SQLAlchemy event listener
        # For RDS IAM auth, we MUST use SSL
        connection_string = f"{db_type}://{rds_username}@{rds_endpoint}:{rds_port}/{rds_database}?sslmode=require"

        return connection_string

    except ImportError:
        print("ERROR: posit-sdk or boto3 not available, cannot setup AWS RDS connection")
        return None
    except Exception as e:
        print(f"ERROR: Failed to setup AWS RDS connection: {e}")
        return None


def setup_azure_sql_connection():
    """Setup Azure SQL connection using Azure AD authentication.

    Returns
    -------
    str | None
        Connection string without token, or None if setup failed
    """
    try:
        from posit.connect import Client

        print("Setting up Azure database connection with Azure AD authentication")

        # Get required environment variables
        sql_server = os.getenv("AZURE_SQL_SERVER")
        sql_database = os.getenv("AZURE_SQL_DATABASE", "mlflow")

        if not all([sql_server, sql_database]):
            print("ERROR: Missing required Azure SQL environment variables")
            return None

        # Detect database type
        is_postgres = 'postgres.database.azure.com' in sql_server.lower()
        db_type = 'PostgreSQL' if is_postgres else 'SQL Server'
        print(f"Detected Azure {db_type}")

        # Verify Azure integration exists
        client = Client()
        content = client.content.get()

        association = content.oauth.associations.find_by(
            integration_type="azure",
            auth_type="Service Account"
        )

        if not association:
            print("WARNING: No Azure Service Account integration found")
            return None

        print(f"Azure {db_type} integration verified")

        # Build connection string without password
        # Token will be injected by SQLAlchemy event listener
        if is_postgres:
            username = os.getenv("AZURE_SQL_USERNAME", "postgres")
            connection_string = f"postgresql://{username}@{sql_server}:5432/{sql_database}?sslmode=require"
        else:
            # Azure SQL Server connection string
            connection_string = f"mssql+pyodbc://@{sql_server}/{sql_database}?driver=ODBC+Driver+17+for+SQL+Server"

        return connection_string

    except ImportError:
        print("ERROR: posit-sdk not available, cannot setup Azure SQL connection")
        return None
    except Exception as e:
        print(f"ERROR: Failed to setup Azure SQL connection: {e}")
        return None


# ====================================================================
# TOKEN REFRESH FUNCTIONS
# ====================================================================

def get_fresh_aws_rds_token():
    """Fetch a fresh AWS RDS IAM authentication token.

    Returns
    -------
    str | None
        Fresh RDS auth token, or None if fetch failed
    """
    try:
        from posit.connect import Client
        from posit.connect.external.aws import get_content_credentials
        import boto3

        # Get required environment variables
        rds_endpoint = os.getenv("RDS_ENDPOINT")
        rds_port = int(os.getenv("RDS_PORT", "5432"))
        rds_username = os.getenv("RDS_USERNAME", "postgres")
        aws_region = os.getenv("AWS_REGION", "us-east-2")

        if not all([rds_endpoint, rds_username]):
            print("ERROR: Missing required RDS environment variables for token refresh")
            return None

        # Get AWS credentials from Connect
        client = Client()
        aws_credentials = get_content_credentials(client)

        # Create RDS client with credentials
        rds_client = boto3.client(
            'rds',
            region_name=aws_region,
            aws_access_key_id=aws_credentials["aws_access_key_id"],
            aws_secret_access_key=aws_credentials["aws_secret_access_key"],
            aws_session_token=aws_credentials["aws_session_token"],
        )

        # Generate authentication token
        token = rds_client.generate_db_auth_token(
            DBHostname=rds_endpoint,
            Port=rds_port,
            DBUsername=rds_username,
            Region=aws_region,
        )

        return token

    except Exception as e:
        print(f"ERROR: Failed to get fresh AWS RDS token: {e}")
        return None


def get_fresh_azure_token():
    """Fetch a fresh Azure access token from Posit Connect.

    Returns
    -------
    str | None
        Fresh access token, or None if fetch failed
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

        if not association:
            print("ERROR: No Azure Service Account integration found")
            return None

        # Get Azure credentials with ossrdbms-aad scope
        credentials = client.oauth.get_content_credentials(
            audience=association['oauth_integration_guid']
        )

        access_token = credentials.get('access_token')
        if not access_token:
            print("ERROR: No access token received from Azure integration")
            return None

        return access_token

    except Exception as e:
        print(f"ERROR: Failed to get fresh Azure token: {e}")
        return None


# ====================================================================
# EVENT LISTENERS
# ====================================================================

def setup_database_event_listeners():
    """Setup SQLAlchemy event listeners for automatic database token injection.

    Handles both AWS RDS IAM authentication and Azure AD authentication.
    This must be called BEFORE MLflow creates its engine.
    """
    try:
        from sqlalchemy import event, Engine

        print("Setting up SQLAlchemy event listeners for database token refresh")

        @event.listens_for(Engine, "do_connect")
        def receive_do_connect(_dialect, _conn_rec, _cargs, cparams):
            """
            Intercept connection attempts and inject fresh tokens.
            Called every time a new connection is established.
            """
            host = cparams.get('host', '')

            # Determine which database type based on environment variables
            rds_endpoint = os.getenv('RDS_ENDPOINT', '').lower()
            azure_sql_server = os.getenv('AZURE_SQL_SERVER', '').lower()

            # AWS RDS - check if RDS_ENDPOINT is set and matches the host
            if rds_endpoint and (rds_endpoint in host.lower() or host.lower() in rds_endpoint):
                print("Refreshing AWS RDS IAM token...")
                fresh_token = get_fresh_aws_rds_token()

                if fresh_token:
                    cparams['password'] = fresh_token
                    # Ensure SSL is enabled (required for IAM auth)
                    if 'sslmode' not in cparams:
                        cparams['sslmode'] = 'require'
                    print("AWS RDS token refreshed successfully")
                else:
                    print("ERROR: Failed to refresh AWS RDS token")

            # Azure PostgreSQL or SQL Server
            elif azure_sql_server and (azure_sql_server in host.lower() or host.lower() in azure_sql_server):
                print("Refreshing Azure SQL token...")
                fresh_token = get_fresh_azure_token()

                if fresh_token:
                    cparams['password'] = fresh_token
                    print("Azure SQL token refreshed successfully")
                else:
                    print("ERROR: Failed to refresh Azure SQL token")

        print("Database event listeners configured successfully")
        return True

    except ImportError:
        print("ERROR: SQLAlchemy not available, cannot setup event listeners")
        return False
    except Exception as e:
        print(f"ERROR: Failed to setup database event listeners: {e}")
        import traceback
        print(traceback.format_exc())
        return False
