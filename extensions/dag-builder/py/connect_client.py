"""
Posit Connect Client Operations

This module handles all Posit Connect API interactions including user authentication,
content search, and deployment operations. Backend-agnostic Connect integration.
"""

from typing import List, Dict, Any, Optional
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)

try:
    from posit.connect import Client
    POSIT_CONNECT_AVAILABLE = True
except ImportError:
    POSIT_CONNECT_AVAILABLE = False
    logger.warning("posit-sdk not available. Search functionality will be mocked.")


def get_current_user_guid() -> Optional[str]:
    """Get the current user's GUID from Posit Connect."""
    if not POSIT_CONNECT_AVAILABLE:
        # Mock GUID for development
        return "mock-user-guid-dev"

    try:
        # Initialize Posit Connect client
        client = Client()

        # Get current user information
        response = client.get("/v1/user")
        user_data = response.json()

        user_guid = user_data.get("guid")
        username = user_data.get("username", "unknown")

        logger.info(f"Retrieved user GUID: {user_guid} for username: {username}")
        return user_guid

    except Exception as e:
        logger.error(f"Error getting user GUID: {e}")
        return None


def get_user_guid_from_api_key(api_key: str) -> Optional[str]:
    """Get user GUID from API key using Posit Connect API."""
    if not POSIT_CONNECT_AVAILABLE:
        # Mock GUID for development
        return "mock-user-guid-dev"

    try:
        # Initialize Posit Connect client with provided API key
        original_key = os.getenv('CONNECT_API_KEY')
        os.environ['CONNECT_API_KEY'] = api_key

        client = Client()
        response = client.get("/v1/user")
        user_data = response.json()

        # Restore original key
        if original_key:
            os.environ['CONNECT_API_KEY'] = original_key

        user_guid = user_data.get("guid")
        logger.info(f"API key resolved to user GUID: {user_guid}")
        return user_guid

    except Exception as e:
        logger.error(f"Error resolving API key to user GUID: {e}")
        return None


def search_posit_connect(query: str) -> List[Dict[str, Any]]:
    """Search Posit Connect for content matching the query."""
    if not POSIT_CONNECT_AVAILABLE:
        # Mock data for development
        mock_results = [
            {
                "guid": f"mock-guid-{i}",
                "name": f"Sample Content {i}: {query}",
                "content_type": "notebook" if i % 2 == 0 else "report",
                "url": f"https://connect.example.com/content/mock-guid-{i}/",
                "description": f"This is a sample {('notebook' if i % 2 == 0 else 'report')} that demonstrates {query} functionality.",
                "created_time": "2024-01-15T10:30:00Z",
                "last_deployed_time": "2024-01-20T14:45:00Z",
                "author": f"user{i}"
            }
            for i in range(1, 6)
        ]
        return mock_results

    try:
        # Initialize Posit Connect client
        client = Client()

        # Use the search endpoint directly for fuzzy search
        search_params = {
            "q": query,  # Search terms will match name, title, or description
            "page_size": 10,  # Limit to 10 results
            "sort": "name",  # Sort by name
            "order": "desc",  # Descending order
            "include": "owner"  # Include owner details
        }

        # Make the search request using the client's get method
        response = client.get("/v1/search/content", params=search_params)
        search_data = response.json()

        logger.info(f"Search query: '{query}' - Found {len(search_data.get('results', []))} items")

        results = []
        for content in search_data.get("results", [])[:10]:  # Limit to 10 results
            # Format dates
            created_time = content.get("created_time", "")
            last_deployed_time = content.get("last_deployed_time", "")

            # Get owner information
            owner_info = content.get("owner", {})
            author = owner_info.get("username", "Unknown") if owner_info else "Unknown"

            results.append({
                "guid": content.get("guid"),
                "name": content.get("name") or content.get("title", "Unknown"),
                "content_type": content.get("app_mode", "unknown"),
                "url": content.get("content_url", ""),
                "description": content.get("description", "")[:100] + "..." if content.get("description") and len(content.get("description", "")) > 100 else content.get("description", ""),
                "created_time": created_time,
                "last_deployed_time": last_deployed_time,
                "author": author
            })

        return results
    except Exception as e:
        logger.error(f"Error searching Posit Connect: {e}")
        return []


def deploy_to_connect(temp_dir: str, title: str = "") -> Dict[str, Any]:
    """Deploy the generated content to Posit Connect."""
    deploy_title = title if title.strip() else f"dag-execution-{os.path.basename(temp_dir)}"

    try:
        logger.info(f"Starting deployment of '{deploy_title}' to Posit Connect...")

        # Try using rsconnect-python for deployment
        cmd = [
            "rsconnect", "deploy", "quarto",
            "--title", deploy_title,
            "--no-verify",
            str(temp_dir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info(f"DAG '{deploy_title}' deployed successfully to Posit Connect")
            return {"success": True, "message": "Deployment successful"}
        else:
            error_msg = result.stderr + result.stdout
            logger.error(f"Deployment failed: {error_msg}")
            return {"success": False, "message": f"Deployment failed: {error_msg}"}

    except subprocess.TimeoutExpired:
        error_msg = "Deployment timed out"
        logger.error(error_msg)
        return {"success": False, "message": error_msg}
    except FileNotFoundError:
        error_msg = "rsconnect-python not found. Please install rsconnect-python package."
        logger.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"Deployment error: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg}


async def deploy_to_connect_async(temp_dir: str, title: str = "", message_callback=None) -> Dict[str, Any]:
    """
    Async version of deploy_to_connect with optional message callback.
    Message callback should be a coroutine that accepts (message: str, type: str).
    """
    deploy_title = title if title.strip() else f"dag-execution-{os.path.basename(temp_dir)}"

    if message_callback:
        await message_callback(f"Starting deployment of '{deploy_title}' to Posit Connect...", "info")

    try:
        # Try using rsconnect-python for deployment
        cmd = [
            "rsconnect", "deploy", "quarto",
            "--title", deploy_title,
            "--no-verify",
            str(temp_dir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            if message_callback:
                await message_callback(f"DAG '{deploy_title}' deployed successfully to Posit Connect", "success")
            return {"success": True, "message": "Deployment successful"}
        else:
            error_msg = result.stderr + result.stdout
            logger.error(f"Deployment failed: {error_msg}")
            if message_callback:
                await message_callback(f"Deployment failed: {error_msg}", "error")
            return {"success": False, "message": f"Deployment failed: {error_msg}"}

    except subprocess.TimeoutExpired:
        error_msg = "Deployment timed out"
        if message_callback:
            await message_callback(error_msg, "error")
        return {"success": False, "message": error_msg}
    except FileNotFoundError:
        error_msg = "rsconnect-python not found. Please install rsconnect-python package."
        if message_callback:
            await message_callback(error_msg, "error")
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"Deployment error: {str(e)}"
        if message_callback:
            await message_callback(error_msg, "error")
        return {"success": False, "message": error_msg}