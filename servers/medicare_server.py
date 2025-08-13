"""
FastMCP quickstart example with debugging.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

import logging
import os
import sys
from urllib.parse import unquote

from fastapi import FastAPI
import requests
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from auth_utils import get_user_info_and_token
from datasets import api, fetch_dataset, iter_document_filenames, read_document
from decorators import require_groups

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI()

# Add CORS middleware to FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify your allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FastMCP server
mcp = FastMCP(name="medicare", version="1.0.0")

# Mount FastMCP routes onto FastAPI app
# Assuming FastMCP exposes a router or ASGI app via `mcp.router` or similar
# (Check FastMCP docs for exact attribute)
app.mount("/mcp", mcp)  # or app.include_router(mcp.router)

API_NAME = "MEDICARE_API"
DOCUMENT_CATEGORY = "va"

load_dotenv()
AUTH_GROUPS = os.getenv("AUTH_GROUPS", "Unauthorized").split(",")


@mcp.resource(
    uri="data://app-status",
    name="ApplicationStatus",
    description="Provides the current status of the application.",
    mime_type="application/json",
    tags={"monitoring", "status"},
)
def get_application_status() -> dict:
    """Internal function description (ignored if description is provided above)."""
    logger.info("get_application_status called")
    return {
        "status": "ok",
        "uptime": 12345,
        "version": "1.0.0",  # Use hardcoded version or mcp.name for server name
        "server_name": mcp.name,
    }


@mcp.resource(
    uri="medicare://nursing-home-dataset",
    name="NursingHomeDataset",
    description="Fetch the nursing home dataset from the Medicare API",
    mime_type="application/json",
    tags={"medicare", "nursing_home", "dataset"},
)
@require_groups(AUTH_GROUPS)
def get_medicare_nursing_home_dataset() -> dict:
    """Fetch datasets from the Medicare API"""
    logger.info("get_medicare_nursing_home_dataset called")
    try:
        result = fetch_dataset(API_NAME, "nursing_home_dataset")
        logger.info("Dataset fetched successfully, type: %s", type(result))
        return result
    except KeyError as e:
        logger.error("Dataset not found: %s", e)
        return {"error": f"Dataset not found: {str(e)}"}
    except TypeError as e:
        logger.error("Invalid dataset type: %s", e)
        return {"error": f"Invalid dataset type: {str(e)}"}
    except (RuntimeError, OSError) as e:
        logger.error("Unexpected error fetching nursing home dataset: %s", e)
        return {"error": f"Unexpected error: {str(e)}"}


@mcp.resource(
    uri="medicare://deficit-reduction-dataset",
    name="DeficitReductionDataset",
    description=(
        "Fetch the Deficit Reduction Act Hospital-Acquired Condition dataset "
        "from the Medicare API"
    ),
    mime_type="application/json",
    tags={"medicare", "deficit_reduction", "dataset"},
)
@require_groups(AUTH_GROUPS)
def get_deficit_reduction_dataset() -> dict:
    """Fetch datasets from the Medicare API."""
    logger.info("get_deficit_reduction_dataset called")
    try:
        result = fetch_dataset(API_NAME, "deficit_reduction_dataset")
        logger.info("Dataset fetched successfully, type: %s", type(result))
        return result
    except KeyError as e:
        logger.error("Dataset not found: %s", e)
        return {"error": f"Dataset not found: {str(e)}"}
    except TypeError as e:
        logger.error("Invalid dataset type: %s", e)
        return {"error": f"Invalid dataset type: {str(e)}"}
    except ValueError as e:
        logger.error("Value error fetching deficit reduction dataset: %s", e)
        return {"error": f"Value error: {str(e)}"}


@mcp.resource(
    uri="medicare://datasets",
    name="MedicareDatasets",
    description="List all available Medicare datasets",
    mime_type="application/json",
    tags={"medicare", "datasets"},
)
def list_medicare_datasets() -> dict:
    """List available Medicare datasets from the datasets module."""
    logger.info("list_medicare_datasets called")
    try:
        result = api[API_NAME]["datasets"]
        logger.info("Datasets listed successfully: %s", list(result.keys()))
        return result
    except KeyError as e:
        logger.error("API or datasets key not found: %s", e)
        return {"error": f"API or datasets key not found: {str(e)}"}
    except TypeError as e:
        logger.error("Type error accessing datasets: %s", e)
        return {"error": f"Type error accessing datasets: {str(e)}"}


@mcp.resource(
    uri="documents://{filename}",
    name="MedicareDocumentResource",
    description="Access Medicare documents as resources",
    mime_type="text/plain",
    tags={"medicare", "documents"},
)
def get_document_resource(filename: str) -> str:
    """Expose Medicare documents as resources."""
    logger.info("get_document_resource called with filename: %s", filename)
    try:
        result = read_document("documents", DOCUMENT_CATEGORY, filename)
        logger.info("Document read successfully, length: %d", len(result))
        return result
    except (FileNotFoundError, IOError, OSError) as e:
        logger.error("Error reading document %s: %s", filename, e)
        return f"Error reading document: {str(e)}"


@mcp.tool()
def health() -> str:
    """Check the health of the Medicare server."""
    logger.info("health tool called")
    return "Medicare server is running and healthy."


@mcp.tool()
def get_medicare_dataset_row_count(dataset_name: str) -> int:
    """Return the number of rows in a Medicare dataset by dataset name."""
    logger.info("get_medicare_dataset_row_count called with dataset: %s", dataset_name)
    try:
        data = fetch_dataset(API_NAME, dataset_name)
        count = len(data) if isinstance(data, list) else 0
        logger.info("Dataset row count: %d", count)
        return count
    except (KeyError, TypeError, ValueError) as e:
        logger.error("Error getting row count for %s: %s", dataset_name, e)
        return 0


@mcp.tool()
def list_medicare_documents() -> list:
    """List all Medicare documents available."""
    logger.info("list_medicare_documents called")
    try:
        result = list(iter_document_filenames("documents", DOCUMENT_CATEGORY))
        logger.info("Documents listed: %s", result)
        return result
    except (FileNotFoundError, IOError, OSError) as e:
        logger.error("Error listing documents: %s", e)
        return []


@mcp.tool()
def get_medicare_document(filename: str) -> str:
    """Return the contents of a Medicare document from the documents/medicare folder."""
    logger.info("get_medicare_document called with filename: %s", filename)
    try:
        result = read_document("documents", DOCUMENT_CATEGORY, filename)
        logger.info("Document content length: %d", len(result))
        return result
    except (FileNotFoundError, IOError, OSError) as e:
        logger.error("Error getting document %s: %s", filename, e)
        return f"Error reading document: {str(e)}"


@mcp.tool()
def get_medicare_dataset_columns(dataset_name: str) -> list:
    """Return the column names/fields for a given Medicare dataset (if available)."""
    logger.info("get_medicare_dataset_columns called with dataset: %s", dataset_name)
    try:
        data = fetch_dataset(API_NAME, dataset_name)
        if isinstance(data, list) and data:
            columns = list(data[0].keys())
            logger.info("Dataset columns: %s", columns)
            return columns
        logger.info("No columns found or data is not a list")
        return []
    except (KeyError, TypeError, ValueError) as e:
        logger.error("Error getting columns for %s: %s", dataset_name, e)
        return []


@mcp.tool()
def get_medicare_dataset_rows(
    dataset_name: str, limit: int = 10, offset: int = 0
) -> list:
    """Return a list of rows from a Medicare dataset by dataset name, with optional
    limit and offset."""
    logger.info(
        "get_medicare_dataset_rows called with dataset: %s, limit: %d, offset: %d",
        dataset_name,
        limit,
        offset,
    )
    try:
        data = fetch_dataset(API_NAME, dataset_name)
        if isinstance(data, list):
            # Apply offset and limit
            rows = data[offset : offset + limit]
            logger.info("Returning %d rows from dataset %s", len(rows), dataset_name)
            return rows
        logger.warning("Dataset %s is not a list or is empty.", dataset_name)
        return []
    except (FileNotFoundError, IOError, OSError, KeyError, TypeError, ValueError) as e:
        logger.error("Error getting rows for %s: %s", dataset_name, e)
        return []


# Add all your other tools with similar logging...
@mcp.tool()
def authenticate_user() -> dict:
    """Authenticate the current user and return their information and access token."""
    logger.info("authenticate_user called")

    try:
        result = get_user_info_and_token()
        logger.info("Authentication result status: %s", result["status"])

        if result["status"] == "success":
            return {
                "user": {
                    "name": result["display_name"],
                    "email": result["email"],
                    "job_title": result["job_title"],
                    "group_count": result["group_count"],
                },
                "authentication": {
                    "status": "authenticated",
                    "token_preview": result["access_token"][:20] + "...",
                    "expires_on": result["token_expires_on"],
                },
            }
        else:
            return {"error": result["error"], "status": "authentication_failed"}
    except (KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
        logger.error("Error in authenticate_user: %s", e)
        return {"error": str(e), "status": "error"}


@mcp.tool()
def get_sharepoint_files(sharepoint_url: str, access_token: str) -> dict:
    """Query a SharePoint URL using a provided access token and return the
    list of objects."""

    sharepoint_url = unquote(sharepoint_url)
    logger.info("query_sharepoint called for URL: %s", sharepoint_url)

    try:
        headers = {
            "Authorization": f"Bearer {unquote(access_token)}",
            "Accept": "application/json;odata=verbose",
        }
        response = requests.get(sharepoint_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        # Try to extract list of objects from common SharePoint response keys
        if "d" in data and "results" in data["d"]:
            objects = data["d"]["results"]
        elif "value" in data:
            objects = data["value"]
        else:
            objects = data
        logger.info(
            "SharePoint query returned %s objects.",
            len(objects) if isinstance(objects, list) else "unknown",
        )
        return {"objects": objects, "status": "success"}
    except (FileNotFoundError, IOError, OSError, KeyError, TypeError, ValueError) as e:
        logger.error("Error querying SharePoint: %s", e)
        return {"error": str(e), "status": "failed"}


# Add your prompts
@mcp.prompt()
def explain_available_tools() -> str:
    """Summarize what tools are available and what they do."""
    logger.info("explain_available_tools prompt called")
    base_tools = (
        "Available tools include: get_medicare_dataset_row_count )"
        "(count rows in a dataset), "
        "get_medicare_document (read a document), list_medicare_documents "
        "(list all documents), "
        "get_medicare_dataset_columns (list dataset columns), and health "
        "(check server health)."
    )

    auth_tools = " Authentication tools: authenticate_user (get user info and token)."
    return base_tools + auth_tools


def main():
    """Start the Medicare MCP server."""
    logger.info("Starting Medicare MCP server...")
    try:
        mcp.run(host="127.0.0.1", port=8000, transport="streamable-http")
    except (FileNotFoundError, IOError, OSError, KeyError, TypeError, ValueError) as e:
        logger.error("Error starting server: %s", e)
        raise


if __name__ == "__main__":
    main()
