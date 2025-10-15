import os
import logging

from utils import (
    mask_credentials,
    detect_storage_backend,
    detect_database_backend,
    setup_aws_rds_connection,
    setup_azure_sql_connection,
    setup_database_event_listeners,
    setup_aws_credentials,
    setup_azure_credentials
)

# Configure logging before anything else
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Set specific loggers to appropriate levels
logging.getLogger("mlflow").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
logging.getLogger("fastapi").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Connect app persistent data directory
base_dir = os.path.join(os.getcwd(), "app-data")
db_path = os.path.join(base_dir, "mlflow.db")
artifact_path = os.path.join(base_dir, "artifacts")
os.makedirs(artifact_path, exist_ok=True)

# Set environment variables for MLflow server before importing the app
# These are used by mlflow.server.handlers to initialize stores.
# Public env vars:
#   MLFLOW_BACKEND_STORE_URI -> _MLFLOW_SERVER_FILE_STORE
#   MLFLOW_DEFAULT_ARTIFACT_ROOT -> _MLFLOW_SERVER_ARTIFACT_ROOT
#   MLFLOW_ARTIFACTS_DESTINATION -> _MLFLOW_SERVER_ARTIFACT_DESTINATION
#   MLFLOW_SERVE_ARTIFACTS -> _MLFLOW_SERVER_SERVE_ARTIFACTS
#   MLFLOW_ARTIFACTS_ONLY -> _MLFLOW_SERVER_ARTIFACTS_ONLY
#   prometheus_multiproc_dir (no public equivalent)

# Backend store URI (tracking/experiment data)
backend_store_uri = os.getenv("MLFLOW_BACKEND_STORE_URI") or os.getenv("_MLFLOW_SERVER_FILE_STORE") or f"sqlite:///{db_path}"
os.environ.setdefault("_MLFLOW_SERVER_FILE_STORE", backend_store_uri)

# Registry store URI (model registry data) - uses same as backend
os.environ.setdefault("_MLFLOW_SERVER_REGISTRY_STORE", backend_store_uri)

# Serve artifacts flag
serve_artifacts = os.getenv("MLFLOW_SERVE_ARTIFACTS") or os.getenv("_MLFLOW_SERVER_SERVE_ARTIFACTS") or "true"
os.environ.setdefault("_MLFLOW_SERVER_SERVE_ARTIFACTS", serve_artifacts)

# Artifact root (default location for new experiments)
artifact_root = os.getenv("MLFLOW_DEFAULT_ARTIFACT_ROOT") or os.getenv("MLFLOW_ARTIFACT_ROOT") or os.getenv("_MLFLOW_SERVER_ARTIFACT_ROOT") or "mlflow-artifacts:/"
os.environ.setdefault("_MLFLOW_SERVER_ARTIFACT_ROOT", artifact_root)

# Artifacts destination (physical storage location)
artifacts_destination = os.getenv("MLFLOW_ARTIFACTS_DESTINATION") or os.getenv("_MLFLOW_SERVER_ARTIFACT_DESTINATION") or artifact_path
os.environ.setdefault("_MLFLOW_SERVER_ARTIFACT_DESTINATION", artifacts_destination)

# Configure SQLAlchemy connection pool recycling for OAuth token refresh
# Set to 1 hour (3600 seconds) to ensure connections are recycled well before
# the 24-hour token expiration, providing fresh tokens regularly
os.environ.setdefault("MLFLOW_SQLALCHEMYSTORE_POOL_RECYCLE", "3600")

# IMPORTANT: Setup database event listeners BEFORE setting connection strings
# This ensures tokens are injected on the very first connection attempt
backend_db_type = detect_database_backend(os.environ.get('_MLFLOW_SERVER_FILE_STORE', f"sqlite:///{db_path}"))
print(f"Detected backend database type: {backend_db_type}")

if backend_db_type in ['aws_rds', 'azure_sql']:
    print("Setting up database event listeners for OAuth token refresh...")
    if not setup_database_event_listeners():
        print("ERROR: Failed to setup database event listeners")

# Detect and setup database connections
if backend_db_type == 'aws_rds':
    print("AWS RDS backend detected, setting up IAM authentication...")
    
    rds_connection_string = setup_aws_rds_connection()
    if rds_connection_string:
        os.environ['_MLFLOW_SERVER_FILE_STORE'] = rds_connection_string
        os.environ['_MLFLOW_SERVER_REGISTRY_STORE'] = rds_connection_string
        print("AWS RDS backend connection configured successfully")
        print("Tokens will be automatically refreshed every hour via connection pool recycling")
    else:
        print("WARNING: Failed to setup AWS RDS connection, using original connection string")
elif backend_db_type == 'azure_sql':
    print("Azure SQL backend detected, setting up Azure AD authentication...")
    azure_connection_string = setup_azure_sql_connection()
    if azure_connection_string:
        os.environ['_MLFLOW_SERVER_FILE_STORE'] = azure_connection_string
        os.environ['_MLFLOW_SERVER_REGISTRY_STORE'] = azure_connection_string
        print("Azure SQL backend connection configured successfully")
        print("Tokens will be automatically refreshed every hour via connection pool recycling")
    else:
        print("WARNING: Failed to setup Azure SQL connection, using original connection string")

# Detect storage backend and setup credentials if needed
storage_backend = detect_storage_backend(os.environ['_MLFLOW_SERVER_ARTIFACT_DESTINATION'])
print(f"Detected storage backend: {storage_backend}")

if storage_backend == 'aws':
    print("AWS storage detected, setting up credentials...")
    if not setup_aws_credentials():
        print("WARNING: Failed to setup AWS credentials, artifacts may not be accessible")
elif storage_backend == 'azure':
    print("Azure storage detected, setting up credentials...")
    if not setup_azure_credentials():
        print("WARNING: Failed to setup Azure credentials, artifacts may not be accessible")
elif storage_backend == 'gcp':
    print("GCP storage detected - assuming default credentials or service account key")
    # GCP typically uses GOOGLE_APPLICATION_CREDENTIALS or default credentials

# By default, MLflow server runs without authentication.
# This is suitable for running behind a proxy that handles authentication.

# The MLflow UI (Flask) needs a secret key for secure cookies.
# Generate a random one if not set.
if "MLFLOW_FLASK_SERVER_SECRET_KEY" not in os.environ:
    os.environ["MLFLOW_FLASK_SERVER_SECRET_KEY"] = os.urandom(24).hex()

# Import the FastAPI app from MLflow.
# This must be done AFTER setting the environment variables.
try:
    print(f"Backend store URI: {mask_credentials(os.environ['_MLFLOW_SERVER_FILE_STORE'])}")
    print(f"Registry store URI: {mask_credentials(os.environ['_MLFLOW_SERVER_REGISTRY_STORE'])}")
    print(f"Artifact root: {os.environ['_MLFLOW_SERVER_ARTIFACT_ROOT']}")
    print(f"Artifacts destination: {os.environ['_MLFLOW_SERVER_ARTIFACT_DESTINATION']}")
    print(f"Serve artifacts: {os.environ['_MLFLOW_SERVER_SERVE_ARTIFACTS']}")
    print(f"Pool recycle: {os.environ['MLFLOW_SQLALCHEMYSTORE_POOL_RECYCLE']}s")

    from mlflow.server.fastapi_app import app
    
    # Add middleware to log all requests
    from fastapi import Request
    import traceback
    import time
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Log request
        print(f"Request: {request.method} {request.url}")

        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            print(f"Response: {response.status_code} - {process_time:.3f}s")
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        except Exception:
            print(f"Request failed: {traceback.format_exc()}")
            raise
    
except ImportError as e:
    print("Failed to import MLflow. Please ensure MLflow is installed (`pip install mlflow`).")
    raise e

if __name__ == "__main__":
    import uvicorn

    # Run the FastAPI app with Uvicorn
    # Use environment variables for host and port to support different deployment scenarios
    host = os.getenv("MLFLOW_HOST", "0.0.0.0")
    port = int(os.getenv("MLFLOW_PORT", "8000"))

    # For remote deployment, configure the server host for artifact URL generation
    if host != "127.0.0.1" and host != "localhost":
        server_host = os.getenv("MLFLOW_SERVER_HOST", f"{host}:{port}")
        os.environ["_MLFLOW_SERVER_HOST"] = server_host

    print(f"Starting MLflow server on {host}:{port}")
    print(f"Artifact serving enabled: {os.getenv('_MLFLOW_SERVER_SERVE_ARTIFACTS')}")
    print(f"Artifacts destination: {os.getenv('_MLFLOW_SERVER_ARTIFACTS_DESTINATION')}")

    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level="debug",
        access_log=True
    )
