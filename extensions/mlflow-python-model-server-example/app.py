"""
MLflow Model API Server

This module provides a FastAPI application that serves MLflow models with automatic
OpenAPI documentation generation.

Usage:
    Set the MODEL_URI environment variable to your MLflow model location:
    
    export MODEL_URI="models:/my-model/production"
    python app.py
    
    Or with a local model:
    
    export MODEL_URI="./my-model"
    python app.py

Environment Variables:
    MODEL_URI (required): The MLflow model URI to load
        Examples: 
        - "models:/my-model/production"
        - "runs:/abc123/model"
        - "./local-model-path"
    
    CONNECT_SERVER (optional): Posit Connect server URL
    MLFLOW_TRACKING_URI (optional): MLflow tracking server URI
    MLFLOW_TRACKING_TOKEN (optional): Authentication token for MLflow
    HOST (optional): Server host (default: "0.0.0.0")
    PORT (optional): Server port (default: 8000)

Endpoints:
    GET  /ping         - Health check endpoint
    GET  /health       - Detailed health status
    GET  /version      - Model version information
    POST /invocations  - Model prediction endpoint
"""

import os
import logging
import mlflow
from mlflow.pyfunc.scoring_server import load_model, init
from openapi_schema import (
    extract_model_signature,
    configure_openapi_metadata,
    generate_openapi_schema
)


# Configure logging for production use
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure MLflow tracking connection
CONNECT_SERVER = os.getenv('CONNECT_SERVER')
if CONNECT_SERVER:
    # Default to Connect server's MLflow endpoint and API key if available
    MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', f"{CONNECT_SERVER}/mlflow")
    os.environ["MLFLOW_TRACKING_TOKEN"] = os.getenv(
        'MLFLOW_TRACKING_TOKEN',
        os.getenv('CONNECT_API_KEY', "")
    )
else:
    MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', "")
    
if MLFLOW_TRACKING_URI:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    logger.info(f"MLflow tracking URI set to: {MLFLOW_TRACKING_URI}")


def get_model_uri() -> str:
    """
    Retrieve the model URI from environment variables.
    
    Returns:
        str: The MLflow model URI
        
    Raises:
        ValueError: If MODEL_URI environment variable is not set
    """
    model_uri = os.environ.get("MODEL_URI")
    if not model_uri:
        raise ValueError(
            "MODEL_URI environment variable must be set. "
            "Example: export MODEL_URI='models:/my-model/production'"
        )
    return model_uri


def create_app():
    """
    Create and configure the FastAPI application.

    This function:
    1. Loads the MLflow model from the specified URI
    2. Extracts model signature for API documentation
    3. Initializes FastAPI with standard MLflow endpoints
    4. Configures OpenAPI schema with model-specific metadata

    Returns:
        FastAPI: Configured FastAPI application instance
        
    Raises:
        ValueError: If MODEL_URI is not set
        Exception: If model loading fails
    """
    try:
        model_uri = get_model_uri()
        logger.info(f"Initializing API with model URI: {model_uri}")

        # Load the MLflow model
        logger.info("Loading MLflow model...")
        pyfunc_model = load_model(model_uri)
        logger.info("Model loaded successfully")

        # Extract model signature for OpenAPI documentation
        model_signature_info, example_input, example_output = extract_model_signature(
            pyfunc_model
        )

        # Initialize the FastAPI app with MLflow's standard endpoints
        app = init(pyfunc_model)

        # Enhance OpenAPI documentation with model-specific metadata
        configure_openapi_metadata(
            app,
            model_uri,
            MLFLOW_TRACKING_URI,
            model_signature_info
        )

        # Log available endpoints for debugging
        logger.info("API endpoints registered:")
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                logger.info(f"  {', '.join(route.methods):6s} {route.path}")

        # Generate custom OpenAPI schema with model signature information
        # Note: MLflow uses @app.route() which doesn't integrate with FastAPI's
        # automatic OpenAPI generation, so we build the schema manually
        app.openapi = generate_openapi_schema(
            app,
            model_uri,
            MLFLOW_TRACKING_URI,
            model_signature_info,
            example_input,
            example_output
        )

        logger.info("FastAPI application initialized successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise


# Create the FastAPI application instance
# This is the ASGI application entry point for servers like uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Get server configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    logger.info(f"Starting MLflow Model API server on {host}:{port}")
    logger.info(f"API documentation available at http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port)
