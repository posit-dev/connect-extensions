"""
DAG Storage Management

This module handles artifact storage, user directories, and DAG metadata management.
Backend-agnostic storage operations for DAG builder.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import zipfile
import logging

logger = logging.getLogger(__name__)

# Global configuration
APP_DATA_DIR = Path("app-data")
APP_DATA_DIR.mkdir(exist_ok=True)


def get_user_artifacts_dir(user_guid: str) -> Path:
    """Get the artifacts directory for a specific user."""
    user_dir = APP_DATA_DIR / user_guid
    user_dir.mkdir(exist_ok=True)
    return user_dir


def find_dag_by_title(user_guid: str, title: str) -> Optional[str]:
    """Find existing DAG ID by title for a user."""
    if not user_guid or not title.strip():
        return None

    try:
        user_artifacts = load_user_artifacts(user_guid)
        for artifact in user_artifacts:
            if artifact.get("title", "").strip().lower() == title.strip().lower():
                return artifact.get("id")
        return None
    except Exception as e:
        logger.error(f"Error finding DAG by title: {e}")
        return None


def save_artifact(
    quarto_content: str,
    nodes: List[Dict],
    edges: List[Dict],
    dag_batches: List[List[Dict]],
    title: str = "",
    user_guid: str = None,
    update_existing: bool = False,
    artifact_id: str = None
) -> Dict[str, Any]:
    """Save published DAG as an artifact for historical tracking."""
    if not user_guid:
        raise ValueError("User GUID is required to save artifacts")

    if not title.strip():
        raise ValueError("DAG title is required")

    display_title = title.strip()

    # If artifact_id is provided, we're updating that specific artifact
    if artifact_id:
        # Verify the artifact exists for this user
        existing_metadata = load_artifact_metadata(user_guid, artifact_id)
        if not existing_metadata:
            raise ValueError(f"Cannot update: Artifact {artifact_id} not found")

        # Use the provided artifact_id for update
        timestamp = datetime.now()
        artifact_name = f"dag_execution_{artifact_id}"
    else:
        # Check for existing DAG with same title when creating new
        existing_dag_id = find_dag_by_title(user_guid, display_title)

        if existing_dag_id:
            raise ValueError(f"A DAG with title '{display_title}' already exists. Load the existing DAG to update it.")

        # Create new artifact
        timestamp = datetime.now()
        artifact_id = timestamp.strftime('%Y%m%d_%H%M%S')
        artifact_name = f"dag_execution_{artifact_id}"

    # Create user-specific artifact directory
    user_artifacts_dir = get_user_artifacts_dir(user_guid)
    artifact_dir = user_artifacts_dir / artifact_id
    artifact_dir.mkdir(exist_ok=True)

    # Import here to avoid circular dependency
    from quarto_generator import create_deployment_files

    # Save all files
    create_deployment_files(quarto_content, str(artifact_dir))

    # Save DAG metadata
    metadata = {
        "id": artifact_id,
        "name": artifact_name,
        "title": display_title,
        "timestamp": timestamp.isoformat(),
        "user_guid": user_guid,
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "batches_count": len(dag_batches),
        "nodes": nodes,
        "edges": edges,
        "batches": [[node['id'] for node in batch] for batch in dag_batches]
    }

    metadata_path = artifact_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def load_user_artifacts(user_guid: str) -> List[Dict[str, Any]]:
    """Load all saved artifacts for a specific user."""
    if not user_guid:
        return []

    try:
        user_artifacts_dir = get_user_artifacts_dir(user_guid)
        artifacts = []

        # Scan user's directory for artifact folders
        for artifact_dir in user_artifacts_dir.iterdir():
            if artifact_dir.is_dir():
                metadata_path = artifact_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        artifacts.append(metadata)
                    except Exception as e:
                        logger.error(f"Error loading artifact metadata from {metadata_path}: {e}")

        # Sort by timestamp, most recent first
        artifacts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        logger.info(f"Loaded {len(artifacts)} artifacts for user {user_guid}")
        return artifacts

    except Exception as e:
        logger.error(f"Error loading user artifacts: {e}")
        return []


def load_artifact_metadata(user_guid: str, artifact_id: str) -> Optional[Dict[str, Any]]:
    """Load metadata for a specific artifact."""
    if not user_guid or not artifact_id:
        return None

    try:
        user_artifacts_dir = get_user_artifacts_dir(user_guid)
        metadata_path = user_artifacts_dir / artifact_id / "metadata.json"

        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r') as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"Error loading artifact metadata: {e}")
        return None


def delete_artifact(user_guid: str, artifact_id: str) -> bool:
    """Delete an artifact and its associated files."""
    if not user_guid or not artifact_id:
        return False

    try:
        user_artifacts_dir = get_user_artifacts_dir(user_guid)
        artifact_dir = user_artifacts_dir / artifact_id

        if not artifact_dir.exists():
            return False

        # Delete the entire artifact directory
        import shutil
        shutil.rmtree(artifact_dir)

        # Also delete zip file if it exists
        zip_path = user_artifacts_dir / f"{artifact_id}.zip"
        if zip_path.exists():
            zip_path.unlink()

        return True

    except Exception as e:
        logger.error(f"Error deleting artifact {artifact_id}: {e}")
        return False


def create_artifact_zip(artifact_id: str, user_guid: str) -> Path:
    """Create a zip file of the artifact."""
    user_artifacts_dir = get_user_artifacts_dir(user_guid)
    artifact_dir = user_artifacts_dir / artifact_id
    zip_path = user_artifacts_dir / f"{artifact_id}.zip"

    if not artifact_dir.exists():
        logger.error(f"Artifact directory not found: {artifact_dir}")
        raise FileNotFoundError(f"Artifact {artifact_id} not found for user {user_guid}")

    # Remove existing zip file if it exists
    if zip_path.exists():
        zip_path.unlink()

    try:
        files_added = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in artifact_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(artifact_dir)
                    zipf.write(file_path, arcname)
                    files_added += 1
                    logger.debug(f"Added to zip: {arcname}")

        logger.info(f"Created zip file with {files_added} files: {zip_path}")

        # Verify zip file was created with content
        if not zip_path.exists():
            raise RuntimeError(f"Zip file was not created: {zip_path}")

        if zip_path.stat().st_size == 0:
            raise RuntimeError(f"Zip file is empty: {zip_path}")

        return zip_path

    except Exception as e:
        logger.error(f"Error creating zip file: {e}")
        if zip_path.exists():
            zip_path.unlink()  # Clean up partial file
        raise


def artifact_exists(user_guid: str, artifact_id: str) -> bool:
    """Check if an artifact exists for a user."""
    if not user_guid or not artifact_id:
        return False

    user_artifacts_dir = get_user_artifacts_dir(user_guid)
    artifact_dir = user_artifacts_dir / artifact_id
    metadata_path = artifact_dir / "metadata.json"

    return artifact_dir.exists() and metadata_path.exists()
