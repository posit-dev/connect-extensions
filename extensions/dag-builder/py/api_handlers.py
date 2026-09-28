"""
REST API Handlers

This module contains all REST API endpoint handlers for DAG CRUD operations.
Backend-agnostic request handling and response formatting.
"""

from typing import Optional
import json
import logging
import tempfile
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse

from dag_storage import (
    save_artifact, load_user_artifacts, load_artifact_metadata,
    delete_artifact, create_artifact_zip, artifact_exists
)
from dag_validation import (
    validate_dag, topological_sort_in_batches, convert_api_nodes_to_reactflow,
    validate_api_dag_input
)
from connect_client import get_user_guid_from_api_key, deploy_to_connect
from quarto_generator import generate_quarto_document, create_deployment_files

logger = logging.getLogger(__name__)


def extract_api_key(request: Request) -> Optional[str]:
    """Extract API key from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Key "):
        return auth_header[4:]  # Remove "Key " prefix
    return None


async def create_dag_handler(request: Request):
    """Create a DAG programmatically via API."""
    try:
        # Extract and validate API key
        api_key = extract_api_key(request)
        if not api_key:
            return JSONResponse({
                "error": "Missing or invalid Authorization header. Use 'Authorization: Key <api_key>'"
            }, status_code=401)

        user_guid = get_user_guid_from_api_key(api_key)
        if not user_guid:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        # Parse request body
        body = await request.json()

        # Validate input
        is_valid, errors = validate_api_dag_input(body)
        if not is_valid:
            return JSONResponse({
                "error": "Invalid request body",
                "validation_errors": errors
            }, status_code=400)

        title = body.get("title", "")
        nodes_data = body.get("nodes", [])
        edges_data = body.get("edges", [])

        # Convert nodes to ReactFlow format with auto-layout
        positioned_nodes, reactflow_edges = convert_api_nodes_to_reactflow(nodes_data, edges_data)

        # Validate DAG structure
        validation = validate_dag(positioned_nodes, reactflow_edges)
        if not validation["isValid"]:
            return JSONResponse({
                "error": "Invalid DAG structure",
                "validation_errors": validation["errors"]
            }, status_code=400)

        # Generate batches and Quarto content
        dag_batches = topological_sort_in_batches(positioned_nodes, reactflow_edges)
        quarto_content = generate_quarto_document(positioned_nodes, reactflow_edges, dag_batches)

        # Save artifact
        artifact_metadata = save_artifact(
            quarto_content, positioned_nodes, reactflow_edges, dag_batches, title, user_guid
        )

        return JSONResponse({
            "message": "DAG created successfully",
            "dag_id": artifact_metadata["id"],
            "metadata": {
                "id": artifact_metadata["id"],
                "title": artifact_metadata["title"],
                "timestamp": artifact_metadata["timestamp"],
                "nodes_count": artifact_metadata["nodes_count"],
                "edges_count": artifact_metadata["edges_count"],
                "batches_count": artifact_metadata["batches_count"]
            }
        }, status_code=201)

    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON in request body"}, status_code=400)
    except ValueError as e:
        return JSONResponse({"error": f"Validation error: {str(e)}"}, status_code=400)
    except Exception as e:
        logger.error(f"Error creating DAG: {e}")
        return JSONResponse({"error": f"Failed to create DAG: {str(e)}"}, status_code=500)


async def list_dags_handler(request: Request):
    """List all DAGs for the authenticated user."""
    try:
        # Extract and validate API key
        api_key = extract_api_key(request)
        if not api_key:
            return JSONResponse({
                "error": "Missing or invalid Authorization header. Use 'Authorization: Key <api_key>'"
            }, status_code=401)

        user_guid = get_user_guid_from_api_key(api_key)
        if not user_guid:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        # Load user artifacts
        artifacts = load_user_artifacts(user_guid)

        # Return simplified metadata
        dags = [
            {
                "id": artifact["id"],
                "title": artifact["title"],
                "timestamp": artifact["timestamp"],
                "nodes_count": artifact["nodes_count"],
                "edges_count": artifact["edges_count"],
                "batches_count": artifact["batches_count"]
            }
            for artifact in artifacts
        ]

        return JSONResponse({"dags": dags})

    except Exception as e:
        logger.error(f"Error listing DAGs: {e}")
        return JSONResponse({"error": f"Failed to list DAGs: {str(e)}"}, status_code=500)


async def get_dag_handler(request: Request):
    """Get metadata for a specific DAG."""
    try:
        # Extract and validate API key
        api_key = extract_api_key(request)
        if not api_key:
            return JSONResponse({
                "error": "Missing or invalid Authorization header. Use 'Authorization: Key <api_key>'"
            }, status_code=401)

        user_guid = get_user_guid_from_api_key(api_key)
        if not user_guid:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        dag_id = request.path_params['dag_id']

        # Load artifact metadata
        metadata = load_artifact_metadata(user_guid, dag_id)
        if not metadata:
            return JSONResponse({"error": "DAG not found"}, status_code=404)

        return JSONResponse({"dag": metadata})

    except Exception as e:
        logger.error(f"Error getting DAG: {e}")
        return JSONResponse({"error": f"Failed to get DAG: {str(e)}"}, status_code=500)


async def delete_dag_handler(request: Request):
    """Delete a specific DAG."""
    try:
        # Extract and validate API key
        api_key = extract_api_key(request)
        if not api_key:
            return JSONResponse({
                "error": "Missing or invalid Authorization header. Use 'Authorization: Key <api_key>'"
            }, status_code=401)

        user_guid = get_user_guid_from_api_key(api_key)
        if not user_guid:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        dag_id = request.path_params['dag_id']

        # Check if DAG exists and delete it
        if not artifact_exists(user_guid, dag_id):
            return JSONResponse({"error": "DAG not found"}, status_code=404)

        success = delete_artifact(user_guid, dag_id)
        if not success:
            return JSONResponse({"error": "Failed to delete DAG"}, status_code=500)

        return JSONResponse({"message": "DAG deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting DAG: {e}")
        return JSONResponse({"error": f"Failed to delete DAG: {str(e)}"}, status_code=500)


async def publish_dag_handler(request: Request):
    """Publish a specific DAG to Posit Connect."""
    try:
        # Extract and validate API key
        api_key = extract_api_key(request)
        if not api_key:
            return JSONResponse({
                "error": "Missing or invalid Authorization header. Use 'Authorization: Key <api_key>'"
            }, status_code=401)

        user_guid = get_user_guid_from_api_key(api_key)
        if not user_guid:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        dag_id = request.path_params['dag_id']

        # Load artifact metadata
        metadata = load_artifact_metadata(user_guid, dag_id)
        if not metadata:
            return JSONResponse({"error": "DAG not found"}, status_code=404)

        # Get nodes, edges, and title from metadata
        nodes = metadata.get("nodes", [])
        edges = metadata.get("edges", [])
        title = metadata.get("title", metadata.get("name", ""))

        if not nodes:
            return JSONResponse({"error": "DAG has no nodes to publish"}, status_code=400)

        # Validate DAG before publishing
        validation = validate_dag(nodes, edges)
        if not validation["isValid"]:
            return JSONResponse({
                "error": "Cannot publish invalid DAG",
                "validation_errors": validation["errors"]
            }, status_code=400)

        # Generate batches and Quarto content
        dag_batches = topological_sort_in_batches(nodes, edges)
        quarto_content = generate_quarto_document(nodes, edges, dag_batches)

        # Create temporary directory for deployment files
        with tempfile.TemporaryDirectory() as temp_dir:
            create_deployment_files(quarto_content, temp_dir)

            # Deploy to Connect
            deploy_title = title if title.strip() else f"dag-execution-{dag_id}"
            result = deploy_to_connect(temp_dir, deploy_title)

            if result["success"]:
                logger.info(f"DAG '{deploy_title}' deployed successfully to Posit Connect via API")
                return JSONResponse({
                    "message": f"DAG '{deploy_title}' published successfully to Posit Connect",
                    "dag_id": dag_id,
                    "deployment_title": deploy_title
                })
            else:
                return JSONResponse({
                    "error": result["message"]
                }, status_code=500)

    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid metadata format"}, status_code=400)
    except Exception as e:
        logger.error(f"Error publishing DAG: {e}")
        return JSONResponse({"error": f"Failed to publish DAG: {str(e)}"}, status_code=500)


async def download_artifact_handler(request: Request):
    """Serve artifact zip files for download."""
    try:
        user_guid = request.path_params['user_guid']
        artifact_id = request.path_params['artifact_id']

        if not artifact_exists(user_guid, artifact_id):
            return JSONResponse({"error": "Artifact not found"}, status_code=404)

        # Create or get existing zip file
        try:
            zip_path = create_artifact_zip(artifact_id, user_guid)
            logger.info(f"Created zip file at: {zip_path}")
        except FileNotFoundError as e:
            logger.error(f"Artifact not found: {e}")
            return JSONResponse({"error": "Artifact not found"}, status_code=404)

        # Verify the zip file exists and has content
        if zip_path.exists():
            file_size = zip_path.stat().st_size
            logger.info(f"Zip file exists with size: {file_size} bytes")

            if file_size == 0:
                logger.warning(f"Zip file is empty: {zip_path}")
                return JSONResponse({"error": "Artifact zip file is empty"}, status_code=500)

            # Ensure path is absolute
            absolute_path = zip_path.resolve()
            logger.info(f"Serving file from: {absolute_path}")

            return FileResponse(
                path=str(absolute_path),
                filename=f"dag_execution_{artifact_id}.zip",
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=dag_execution_{artifact_id}.zip",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            logger.error(f"Zip file does not exist: {zip_path}")
            return JSONResponse({"error": "Failed to create artifact zip"}, status_code=500)

    except Exception as e:
        logger.error(f"Error serving artifact download: {e}")
        return JSONResponse({"error": "Failed to serve artifact"}, status_code=500)


async def api_docs_handler(request: Request):
    """Serve OpenAPI documentation."""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "DAG Builder API",
            "version": "1.0.0",
            "description": "REST API for managing Directed Acyclic Graphs (DAGs) in the DAG Builder application"
        },
        "servers": [
            {
                "url": "/api",
                "description": "API Server"
            }
        ],
        "security": [
            {
                "ApiKeyAuth": []
            }
        ],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "API key authentication. Use 'Bearer YOUR_API_KEY'"
                }
            },
            "schemas": {
                "DAGNode": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "type": {"type": "string", "enum": ["content", "custom"]},
                        "data": {"type": "object"}
                    },
                    "required": ["id", "label", "type"]
                },
                "DAGEdge": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "source": {"type": "string"},
                        "target": {"type": "string"}
                    },
                    "required": ["id", "source", "target"]
                },
                "DAGInput": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "nodes": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/DAGNode"}
                        },
                        "edges": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/DAGEdge"}
                        }
                    },
                    "required": ["title", "nodes", "edges"]
                },
                "DAGMetadata": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "nodes_count": {"type": "integer"},
                        "edges_count": {"type": "integer"},
                        "batches_count": {"type": "integer"}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"}
                    }
                }
            }
        },
        "paths": {
            "/dags": {
                "post": {
                    "summary": "Create a new DAG",
                    "description": "Create and save a new DAG with the provided nodes and edges",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DAGInput"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "DAG created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "dag_id": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid DAG data",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                },
                "get": {
                    "summary": "List all DAGs",
                    "description": "Retrieve all DAGs for the authenticated user",
                    "responses": {
                        "200": {
                            "description": "List of DAGs",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/DAGMetadata"}
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                }
            },
            "/dags/{dag_id}": {
                "get": {
                    "summary": "Get a specific DAG",
                    "description": "Retrieve details of a specific DAG by ID",
                    "parameters": [
                        {
                            "name": "dag_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "The ID of the DAG to retrieve"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "DAG details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/DAGMetadata"}
                                }
                            }
                        },
                        "404": {
                            "description": "DAG not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                },
                "delete": {
                    "summary": "Delete a DAG",
                    "description": "Delete a specific DAG by ID",
                    "parameters": [
                        {
                            "name": "dag_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "The ID of the DAG to delete"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "DAG deleted successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "DAG not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                }
            },
            "/dags/{dag_id}/publish": {
                "post": {
                    "summary": "Publish a DAG to Posit Connect",
                    "description": "Deploy a DAG to Posit Connect for execution",
                    "parameters": [
                        {
                            "name": "dag_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "The ID of the DAG to publish"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "DAG published successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "dag_id": {"type": "string"},
                                            "deployment_title": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid DAG or validation failed",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "404": {
                            "description": "DAG not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    # Return JSON OpenAPI spec
    return JSONResponse(openapi_spec)


async def swagger_ui_handler(request: Request):
    """Serve Swagger UI for interactive API documentation."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DAG Builder API Documentation</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
        <style>
            html {{
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }}
            *, *:before, *:after {{
                box-sizing: inherit;
            }}
            body {{
                margin:0;
                background: #fafafa;
            }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {{
                const ui = SwaggerUIBundle({{
                    url: '/api/docs/openapi.json',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout"
                }});
            }};
        </script>
    </body>
    </html>
    """
    from starlette.responses import HTMLResponse
    return HTMLResponse(html_content)
