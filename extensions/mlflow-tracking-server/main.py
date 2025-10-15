import os
import logging

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
#   MLFLOW_REGISTRY_STORE_URI -> _MLFLOW_SERVER_REGISTRY_STORE
#   MLFLOW_DEFAULT_ARTIFACT_ROOT -> _MLFLOW_SERVER_ARTIFACT_ROOT
#   MLFLOW_ARTIFACTS_DESTINATION -> _MLFLOW_SERVER_ARTIFACT_DESTINATION
#   MLFLOW_SERVE_ARTIFACTS -> _MLFLOW_SERVER_SERVE_ARTIFACTS
#   MLFLOW_ARTIFACTS_ONLY -> _MLFLOW_SERVER_ARTIFACTS_ONLY
#   prometheus_multiproc_dir (no public equivalent)

# Backend store URI (tracking/experiment data)
backend_store_uri = os.getenv("MLFLOW_BACKEND_STORE_URI") or os.getenv("_MLFLOW_SERVER_FILE_STORE") or f"sqlite:///{db_path}"
os.environ.setdefault("_MLFLOW_SERVER_FILE_STORE", backend_store_uri)

# Registry store URI (model registry data)
registry_store_uri = os.getenv("MLFLOW_REGISTRY_STORE_URI") or os.getenv("_MLFLOW_SERVER_REGISTRY_STORE") or backend_store_uri
os.environ.setdefault("_MLFLOW_SERVER_REGISTRY_STORE", registry_store_uri)

# Serve artifacts flag
serve_artifacts = os.getenv("MLFLOW_SERVE_ARTIFACTS") or os.getenv("_MLFLOW_SERVER_SERVE_ARTIFACTS") or "true"
os.environ.setdefault("_MLFLOW_SERVER_SERVE_ARTIFACTS", serve_artifacts)

# Artifact root (default location for new experiments)
artifact_root = os.getenv("MLFLOW_DEFAULT_ARTIFACT_ROOT") or os.getenv("MLFLOW_ARTIFACT_ROOT") or os.getenv("_MLFLOW_SERVER_ARTIFACT_ROOT") or "mlflow-artifacts:/"
os.environ.setdefault("_MLFLOW_SERVER_ARTIFACT_ROOT", artifact_root)

# Artifacts destination (physical storage location)
artifacts_destination = os.getenv("MLFLOW_ARTIFACTS_DESTINATION") or os.getenv("_MLFLOW_SERVER_ARTIFACT_DESTINATION") or artifact_path
os.environ.setdefault("_MLFLOW_SERVER_ARTIFACT_DESTINATION", artifacts_destination)

def mask_credentials(uri):
    """Mask sensitive credentials in URIs for logging."""
    if not uri:
        return uri
    # Mask database passwords in URIs like postgresql://user:password@host:port/db
    import re
    masked = re.sub(r'(://[^:]+:)[^@]+(@)', r'\1****\2', uri)
    return masked

print(f"Backend store URI: {mask_credentials(os.environ['_MLFLOW_SERVER_FILE_STORE'])}")
print(f"Registry store URI: {mask_credentials(os.environ['_MLFLOW_SERVER_REGISTRY_STORE'])}")
print(f"Artifact root: {os.environ['_MLFLOW_SERVER_ARTIFACT_ROOT']}")
print(f"Artifacts destination: {os.environ['_MLFLOW_SERVER_ARTIFACT_DESTINATION']}")
print(f"Serve artifacts: {os.environ['_MLFLOW_SERVER_SERVE_ARTIFACTS']}")

# Get current working directory
current_dir = os.getcwd()
print(f"Current working directory: {current_dir}")

# Print list of files recursively
print("Files in current directory (recursive):")
for root, dirs, files in os.walk(current_dir):
    for file in files:
        file_path = os.path.join(root, file)
        print(f"  {file_path}")

# By default, MLflow server runs without authentication.
# This is suitable for running behind a proxy that handles authentication.

# The MLflow UI (Flask) needs a secret key for secure cookies.
# Generate a random one if not set.
if "MLFLOW_FLASK_SERVER_SECRET_KEY" not in os.environ:
    os.environ["MLFLOW_FLASK_SERVER_SECRET_KEY"] = os.urandom(24).hex()

# Import the FastAPI app from MLflow.
# This must be done AFTER setting the environment variables.
try:
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
        print(f"Headers: {dict(request.headers)}")

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
    print(f"Logging level: DEBUG")

    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level="debug",
        access_log=True
    )
