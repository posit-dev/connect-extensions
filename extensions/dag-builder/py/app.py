"""
DAG Builder Main Application - FastAPI Backend

Refactored application using FastAPI for REST API and WebSocket communication.
This file replaces the Shiny-based architecture with a standard Python web framework.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pathlib import Path
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
import tempfile
from datetime import datetime

# Import our modular components
from dag_storage import (
    save_artifact, load_user_artifacts, create_artifact_zip,
    load_artifact_metadata, get_user_artifacts_dir, find_dag_by_title,
    delete_artifact
)
from dag_validation import validate_dag, topological_sort_in_batches
from connect_client import get_current_user_guid, search_posit_connect, deploy_to_connect_async
from quarto_generator import generate_quarto_document, create_deployment_files
from api_handlers import (
    create_dag_handler, list_dags_handler, get_dag_handler,
    delete_dag_handler, publish_dag_handler,
    api_docs_handler, swagger_ui_handler
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DAG Builder API",
    description="Visual DAG builder and builder for Posit Connect content",
    version="1.0.0"
)

# Global state for connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, websocket: WebSocket, message_type: str, data: Dict[str, Any]):
        await websocket.send_json({"type": message_type, "data": data})

    async def broadcast(self, message_type: str, data: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": message_type, "data": data})
            except:
                pass

manager = ConnectionManager()

# In-memory storage for user sessions (replace with Redis or database in production)
user_sessions: Dict[str, Dict[str, Any]] = {}


async def publish_dag_background(nodes: List[Dict], edges: List[Dict], title: str, websocket: Optional[WebSocket]):
    """Background task for publishing DAG using the modular architecture."""

    async def send_status(message: str, msg_type: str):
        """Send status message to either specific websocket or broadcast to all."""
        status_data = {"message": message, "type": msg_type}
        if websocket:
            await manager.send_message(websocket, "logEvent", status_data)
        else:
            await manager.broadcast("logEvent", status_data)

    try:
        await send_status("Starting DAG publishing process in background...", "info")

        # Generate batches for parallel execution
        dag_batches = topological_sort_in_batches(nodes, edges)

        logger.info(f"DAG has {len(nodes)} nodes and {len(edges)} edges, organized into {len(dag_batches)} execution batches")

        # Generate Quarto document
        quarto_content = generate_quarto_document(nodes, edges, dag_batches)

        # Create temporary directory for deployment files
        with tempfile.TemporaryDirectory() as temp_dir:
            create_deployment_files(quarto_content, temp_dir)

            # Create message callback for deployment progress
            async def message_callback(message: str, msg_type: str):
                await send_status(message, msg_type)

            # Deploy to Connect
            result = await deploy_to_connect_async(temp_dir, title, message_callback)

            if result["success"]:
                # Save artifact for historical tracking
                try:
                    user_guid = get_current_user_guid()
                    if user_guid:
                        artifact_metadata = save_artifact(quarto_content, nodes, edges, dag_batches, title, user_guid)

                        # Broadcast updated artifacts list to all connected clients
                        user_artifacts = load_user_artifacts(user_guid)
                        await manager.broadcast("artifacts_list", user_artifacts)

                        await send_status(
                            f"DAG '{title or artifact_metadata['name']}' published successfully!",
                            "success"
                        )

                        logger.info(f"Saved artifact: {artifact_metadata['id']}")
                    else:
                        await send_status(f"DAG '{title}' published successfully!", "success")
                except Exception as e:
                    logger.error(f"Failed to save artifact: {e}")
                    await send_status(
                        f"DAG published but failed to save artifact: {str(e)}",
                        "warning"
                    )
            else:
                await send_status(f"Publishing failed: {result['message']}", "error")

    except ValueError as e:
        # Handle cycle detection
        await send_status(f"DAG validation failed: {str(e)}", "error")
    except Exception as e:
        logger.error(f"Publishing error: {e}")
        await send_status(f"Publishing failed: {str(e)}", "error")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional communication.

    Now focused on real-time updates only:
    - DAG validation (real-time as user edits)
    - Search results (real-time as user types)
    - Status messages (logEvent broadcasts from background tasks)
    - Artifact list updates (broadcasts when DAGs are saved/deleted)

    CRUD operations have been moved to REST endpoints.
    """
    await manager.connect(websocket)

    # Send initial user GUID and artifacts
    user_guid = get_current_user_guid()
    if user_guid:
        await manager.send_message(websocket, "user_guid", {"guid": user_guid})
        user_artifacts = load_user_artifacts(user_guid)
        await manager.send_message(websocket, "artifacts_list", user_artifacts)
    else:
        logger.warning("Could not retrieve user GUID")

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            payload = data.get("data", {})

            logger.info(f"Received WebSocket message: {message_type}")

            if message_type == "dag_data":
                # Real-time DAG validation as user edits
                nodes = payload.get("nodes", [])
                edges = payload.get("edges", [])

                if nodes:
                    validation = validate_dag(nodes, edges)
                    await manager.send_message(websocket, "dag_validation", validation)

            elif message_type == "search_query":
                # Real-time search as user types
                query = payload.get("query", "")
                if query and len(query.strip()) >= 2:
                    try:
                        results = search_posit_connect(query.strip())
                        await manager.send_message(websocket, "search_results", results)
                    except Exception as e:
                        logger.error(f"Search error: {e}")
                        await manager.send_message(websocket, "search_results", [])
                else:
                    await manager.send_message(websocket, "search_results", [])

            else:
                # Unknown message type
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                await manager.send_message(websocket, "logEvent", {
                    "message": f"Unknown message type: {message_type}. Use REST API for CRUD operations.",
                    "type": "warning"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")


# REST API routes

@app.get("/download-artifact/{user_guid}/{artifact_id}")
async def download_artifact(user_guid: str, artifact_id: str):
    """Download artifact as zip file."""
    from pathlib import Path
    import re

    def to_kebab_case(text: str) -> str:
        """Convert text to kebab-case."""
        # Replace spaces and underscores with hyphens
        text = re.sub(r'[\s_]+', '-', text)
        # Remove special characters except hyphens
        text = re.sub(r'[^a-zA-Z0-9\-]', '', text)
        # Convert to lowercase
        text = text.lower()
        # Remove consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading/trailing hyphens
        text = text.strip('-')
        return text

    try:
        # Load metadata to get the title
        metadata = load_artifact_metadata(user_guid, artifact_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Artifact not found")

        # Get title and convert to kebab-case
        title = metadata.get("title", metadata.get("name", "dag"))
        kebab_title = to_kebab_case(title)

        # Create or get existing zip file
        zip_path = create_artifact_zip(artifact_id, user_guid)

        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")

        # Create filename with kebab-case title and artifact ID
        filename = f"{kebab_title}-{artifact_id}.zip"

        # Return file for download
        return FileResponse(
            path=str(zip_path),
            filename=filename,
            media_type="application/zip"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Artifact not found")
    except Exception as e:
        logger.error(f"Error serving artifact download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to prepare download: {str(e)}")


@app.post("/api/dags/save")
async def save_dag_endpoint(request: Dict[str, Any]):
    """Save a DAG (create or update)."""
    nodes = request.get("nodes", [])
    edges = request.get("edges", [])
    title = request.get("title", "")
    loaded_dag_id = request.get("loaded_dag_id")

    if not nodes:
        raise HTTPException(status_code=400, detail="Cannot save empty DAG")

    if not title.strip():
        raise HTTPException(status_code=400, detail="DAG title is required")

    # Validate DAG
    validation = validate_dag(nodes, edges)
    if not validation["isValid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot save invalid DAG: {', '.join(validation['errors'])}"
        )

    user_guid = get_current_user_guid()
    if not user_guid:
        raise HTTPException(status_code=401, detail="User not authenticated")

    is_updating = loaded_dag_id is not None

    # If not updating, check for title uniqueness
    if not is_updating:
        existing_dag_id = find_dag_by_title(user_guid, title)
        if existing_dag_id:
            raise HTTPException(
                status_code=409,
                detail=f"A DAG with title '{title}' already exists. Load the existing DAG to update it."
            )

    try:
        # Generate batches and save
        dag_batches = topological_sort_in_batches(nodes, edges)
        quarto_content = generate_quarto_document(nodes, edges, dag_batches)

        artifact_metadata = save_artifact(
            quarto_content, nodes, edges, dag_batches, title, user_guid,
            update_existing=is_updating,
            artifact_id=loaded_dag_id  # Pass the specific artifact ID when updating
        )

        # Broadcast updated artifacts list to all connected clients
        user_artifacts = load_user_artifacts(user_guid)
        await manager.broadcast("artifacts_list", user_artifacts)
        await manager.broadcast("loaded_dag_id", {"id": artifact_metadata['id']})

        return JSONResponse({
            "success": True,
            "message": f"DAG '{title}' {'updated' if is_updating else 'saved'} successfully!",
            "artifact_id": artifact_metadata['id'],
            "artifact": artifact_metadata
        })
    except Exception as e:
        logger.error(f"Save error: {e}")
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")


@app.get("/api/dags/{artifact_id}")
async def load_dag_endpoint(artifact_id: str):
    """Load a specific DAG by ID."""
    user_guid = get_current_user_guid()
    if not user_guid:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        metadata = load_artifact_metadata(user_guid, artifact_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"DAG {artifact_id} not found")

        return JSONResponse({
            "success": True,
            "dag": {
                "nodes": metadata.get("nodes", []),
                "edges": metadata.get("edges", []),
                "title": metadata.get("title", metadata.get("name", ""))
            },
            "artifact_id": artifact_id
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading DAG: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load DAG: {str(e)}")


@app.delete("/api/dags/{artifact_id}")
async def delete_dag_endpoint(artifact_id: str):
    """Delete a specific DAG."""
    user_guid = get_current_user_guid()
    if not user_guid:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        success = delete_artifact(user_guid, artifact_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to delete artifact {artifact_id}")

        # Broadcast updated artifacts list
        user_artifacts = load_user_artifacts(user_guid)
        await manager.broadcast("artifacts_list", user_artifacts)

        return JSONResponse({
            "success": True,
            "message": f"DAG {artifact_id} deleted successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting artifact: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete artifact: {str(e)}")


@app.post("/api/dags/{artifact_id}/clone")
async def clone_dag_endpoint(artifact_id: str):
    """Clone an existing DAG with a new title."""
    user_guid = get_current_user_guid()
    if not user_guid:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        # Load the original DAG
        metadata = load_artifact_metadata(user_guid, artifact_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

        # Get original title
        original_title = metadata.get("title", metadata.get("name", "DAG"))

        # Find the next available copy number
        user_artifacts = load_user_artifacts(user_guid)
        copy_number = 1
        while True:
            new_title = f"{original_title} - copy {copy_number}"
            # Check if this title exists
            title_exists = any(
                artifact.get("title", "").lower() == new_title.lower()
                for artifact in user_artifacts
            )
            if not title_exists:
                break
            copy_number += 1

        # Get nodes and edges from metadata
        nodes = metadata.get("nodes", [])
        edges = metadata.get("edges", [])

        # Validate and generate new artifact
        validation = validate_dag(nodes, edges)
        if not validation["isValid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Source DAG is invalid: {', '.join(validation['errors'])}"
            )

        # Generate batches and save as new artifact
        dag_batches = topological_sort_in_batches(nodes, edges)
        quarto_content = generate_quarto_document(nodes, edges, dag_batches)

        new_artifact_metadata = save_artifact(
            quarto_content, nodes, edges, dag_batches, new_title, user_guid,
            update_existing=False,
            artifact_id=None  # Create new artifact
        )

        # Broadcast updated artifacts list
        user_artifacts = load_user_artifacts(user_guid)
        await manager.broadcast("artifacts_list", user_artifacts)

        return JSONResponse({
            "success": True,
            "message": f"DAG cloned as '{new_title}'",
            "artifact_id": new_artifact_metadata['id'],
            "artifact": new_artifact_metadata
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning artifact: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clone DAG: {str(e)}")


@app.get("/api/dags")
async def list_dags_endpoint():
    """List all DAGs for the current user."""
    user_guid = get_current_user_guid()
    if not user_guid:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        artifacts = load_user_artifacts(user_guid)
        return JSONResponse({
            "success": True,
            "artifacts": artifacts
        })
    except Exception as e:
        logger.error(f"Error listing DAGs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list DAGs: {str(e)}")


@app.post("/api/dags/publish")
async def publish_dag_endpoint(request: Dict[str, Any]):
    """Publish a DAG to Posit Connect (starts background task)."""
    nodes = request.get("nodes", [])
    edges = request.get("edges", [])
    title = request.get("title", "")

    if not nodes:
        raise HTTPException(status_code=400, detail="Cannot publish empty DAG")

    # Validate DAG
    validation = validate_dag(nodes, edges)
    if not validation["isValid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish invalid DAG: {', '.join(validation['errors'])}"
        )

    # Start publishing as background task
    # Status updates will be sent via WebSocket
    asyncio.create_task(publish_dag_background(nodes, edges, title, None))

    return JSONResponse({
        "success": True,
        "message": "Publishing started. Check status messages for progress."
    })


@app.post("/api/dags/{artifact_id}/publish")
async def publish_saved_dag_endpoint(artifact_id: str):
    """Publish a saved DAG to Posit Connect (starts background task)."""
    user_guid = get_current_user_guid()
    if not user_guid:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        metadata = load_artifact_metadata(user_guid, artifact_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

        nodes = metadata.get("nodes", [])
        edges = metadata.get("edges", [])
        title = metadata.get("title", metadata.get("name", ""))

        # Start publishing as background task
        # Status updates will be sent via WebSocket
        asyncio.create_task(publish_dag_background(nodes, edges, title, None))

        return JSONResponse({
            "success": True,
            "message": f"Publishing '{title}' started. Check status messages for progress."
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in direct publish: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start publish: {str(e)}")


@app.get("/api/docs")
async def api_docs():
    """Get OpenAPI documentation."""
    return await swagger_ui_handler()


@app.get("/api/docs/openapi.json")
async def openapi_json():
    """Get OpenAPI JSON schema."""
    return await api_docs_handler()


# Serve static files (React build output)
www_path = Path(__file__).parent / "www"
app.mount("/assets", StaticFiles(directory=www_path), name="assets")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DAG Builder</title>
    <link rel="stylesheet" href="./assets/main.css">
</head>
<body>
    <div id="root"></div>
    <script type="module" src="./assets/main.js"></script>
</body>
</html>
""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
