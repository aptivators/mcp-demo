"""
FastMCP quickstart example with debugging.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

from fastmcp import FastMCP
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import your modules with error handling
try:
    from decorators import require_groups
    logger.info("Successfully imported decorators")
except ImportError as e:
    logger.error(f"Failed to import decorators: {e}")
    # Create a dummy decorator
    def require_groups(groups):
        def decorator(func):
            return func
        return decorator

try:
    from datasets import fetch_dataset, api, read_document, iter_document_filenames
    logger.info("Successfully imported datasets")
except ImportError as e:
    logger.error(f"Failed to import datasets: {e}")
    # Create dummy functions
    def fetch_dataset(api_name, dataset_name):
        return {"error": "datasets module not available", "api": api_name, "dataset": dataset_name}
    
    api = {
        "MEDICARE_API": {
            "datasets": {
                "nursing_home_dataset": {"description": "Mock nursing home data"},
                "deficit_reduction_dataset": {"description": "Mock deficit reduction data"}
            }
        }
    }
    
    def read_document(category, filename):
        return f"Mock document content for {filename} in category {category}"
    
    def iter_document_filenames(category):
        return ["example1.txt", "example2.txt"]

import re
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware

# Import authentication utilities
try:
    from auth_utils import get_user_info_and_token
    AUTH_AVAILABLE = True
    logger.info("Authentication utilities available")
except ImportError as e:
    logger.warning(f"Authentication not available: {e}")
    AUTH_AVAILABLE = False

# Initialize FastMCP server
mcp = FastMCP(name="medicare", version="1.0.0")

# Add CORS middleware to the FastMCP app if possible
try:
    mcp.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware enabled for all origins on Medicare MCP server.")
except Exception as e:
    logger.warning(f"Could not enable CORS middleware: {e}")

API_NAME = "MEDICARE_API"
DOCUMENT_CATEGORY = "va"

load_dotenv()
AUTH_GROUPS = os.getenv("AUTH_GROUPS", "Unauthorized").split(",")
logger.info(f"Auth groups configured: {AUTH_GROUPS}")

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
        "server_name": mcp.name
    }

@mcp.resource(
    uri="medicare://nursing-home-dataset",
    name="NursingHomeDataset",
    description="Fetch the nursing home dataset from the Medicare API",
    mime_type="application/json",
    tags={"medicare", "nursing_home", "dataset"})
@require_groups(AUTH_GROUPS)
def get_medicare_nursing_home_dataset() -> dict:
    """Fetch datasets from the Medicare API"""
    logger.info("get_medicare_nursing_home_dataset called")
    try:
        result = fetch_dataset(API_NAME, "nursing_home_dataset")
        logger.info(f"Dataset fetched successfully, type: {type(result)}")
        return result
    except Exception as e:
        logger.error(f"Error fetching nursing home dataset: {e}")
        return {"error": str(e)}

@mcp.resource(
    uri="medicare://deficit-reduction-dataset",
    name="DeficitReductionDataset",
    description="Fetch the Deficit Reduction Act Hospital-Acquired Condition dataset from the Medicare API",
    mime_type="application/json",
    tags={"medicare", "deficit_reduction", "dataset"})
@require_groups(AUTH_GROUPS)
def get_deficit_reduction_dataset() -> dict:
    """Fetch datasets from the Medicare API."""
    logger.info("get_deficit_reduction_dataset called")
    try:
        result = fetch_dataset(API_NAME, "deficit_reduction_dataset")
        logger.info(f"Dataset fetched successfully, type: {type(result)}")
        return result
    except Exception as e:
        logger.error(f"Error fetching deficit reduction dataset: {e}")
        return {"error": str(e)}

@mcp.resource(
    uri="medicare://datasets",
    name="MedicareDatasets",
    description="List all available Medicare datasets",
    mime_type="application/json",
    tags={"medicare", "datasets"})
def list_medicare_datasets() -> dict:
    """List available Medicare datasets from the datasets module."""
    logger.info("list_medicare_datasets called")
    try:
        result = api[API_NAME]["datasets"]
        logger.info(f"Datasets listed successfully: {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        return {"error": str(e)}

@mcp.resource(
    uri="documents://{filename}",
    name="MedicareDocumentResource",
    description="Access Medicare documents as resources",
    mime_type="text/plain",
    tags={"medicare", "documents"})
def get_document_resource(filename: str) -> str:
    """Expose Medicare documents as resources."""
    logger.info(f"get_document_resource called with filename: {filename}")
    try:
        result = read_document(DOCUMENT_CATEGORY, filename)
        logger.info(f"Document read successfully, length: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error reading document {filename}: {e}")
        return f"Error reading document: {str(e)}"

@mcp.tool()
def health() -> str:
    """Check the health of the Medicare server."""
    logger.info("health tool called")
    return "Medicare server is running and healthy."

@mcp.tool()
def get_medicare_dataset_row_count(dataset_name: str) -> int:
    """Return the number of rows in a Medicare dataset by dataset name."""
    logger.info(f"get_medicare_dataset_row_count called with dataset: {dataset_name}")
    try:
        data = fetch_dataset(API_NAME, dataset_name)
        count = len(data) if isinstance(data, list) else 0
        logger.info(f"Dataset row count: {count}")
        return count
    except Exception as e:
        logger.error(f"Error getting row count for {dataset_name}: {e}")
        return 0

@mcp.tool()
def list_medicare_documents() -> list:
    """List all Medicare documents available."""
    logger.info("list_medicare_documents called")
    try:
        result = list(iter_document_filenames(DOCUMENT_CATEGORY))
        logger.info(f"Documents listed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []

@mcp.tool()
def get_medicare_document(filename: str) -> str:
    """Return the contents of a Medicare document from the documents/medicare folder."""
    logger.info(f"get_medicare_document called with filename: {filename}")
    try:
        result = read_document(DOCUMENT_CATEGORY, filename)
        logger.info(f"Document content length: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error getting document {filename}: {e}")
        return f"Error reading document: {str(e)}"

@mcp.tool()
def get_medicare_dataset_columns(dataset_name: str) -> list:
    """Return the column names/fields for a given Medicare dataset (if available)."""
    logger.info(f"get_medicare_dataset_columns called with dataset: {dataset_name}")
    try:
        data = fetch_dataset(API_NAME, dataset_name)
        if isinstance(data, list) and data:
            columns = list(data[0].keys())
            logger.info(f"Dataset columns: {columns}")
            return columns
        logger.info("No columns found or data is not a list")
        return []
    except Exception as e:
        logger.error(f"Error getting columns for {dataset_name}: {e}")
        return []

@mcp.tool()
def get_medicare_dataset_rows(dataset_name: str, limit: int = 10, offset: int = 0) -> list:
    """Return a list of rows from a Medicare dataset by dataset name, with optional limit and offset."""
    logger.info(f"get_medicare_dataset_rows called with dataset: {dataset_name}, limit: {limit}, offset: {offset}")
    try:
        data = fetch_dataset(API_NAME, dataset_name)
        if isinstance(data, list):
            # Apply offset and limit
            rows = data[offset:offset+limit]
            logger.info(f"Returning {len(rows)} rows from dataset {dataset_name}")
            return rows
        logger.warning(f"Dataset {dataset_name} is not a list or is empty.")
        return []
    except Exception as e:
        logger.error(f"Error getting rows for {dataset_name}: {e}")
        return []

# Add all your other tools with similar logging...
@mcp.tool()
def authenticate_user() -> dict:
    """Authenticate the current user and return their information and access token."""
    logger.info("authenticate_user called")
    if not AUTH_AVAILABLE:
        logger.warning("Authentication not available")
        return {
            "error": "Authentication not available. Install azure-identity and msgraph-sdk packages.",
            "status": "unavailable"
        }
    
    try:
        result = get_user_info_and_token()
        logger.info(f"Authentication result status: {result['status']}")
        
        if result["status"] == "success":
            return {
                "user": {
                    "name": result["display_name"],
                    "email": result["email"],
                    "job_title": result["job_title"],
                    "group_count": result["group_count"]
                },
                "authentication": {
                    "status": "authenticated",
                    "token_preview": result["access_token"][:20] + "...",
                    "expires_on": result["token_expires_on"]
                }
            }
        else:
            return {
                "error": result["error"],
                "status": "authentication_failed"
            }
    except Exception as e:
        logger.error(f"Error in authenticate_user: {e}")
        return {"error": str(e), "status": "error"}

@mcp.tool()
def query_sharepoint(sharepoint_url: str, access_token: str) -> dict:
    """Query a SharePoint URL using a provided access token and return the list of objects."""
    from urllib.parse import unquote

    sharepoint_url = unquote(sharepoint_url)
    logger.info(f"query_sharepoint called for URL: {sharepoint_url}")
    import requests
    try:
        headers = {
            'Authorization': f'Bearer {unquote(access_token)}',
            'Accept': 'application/json;odata=verbose'
        }
        response = requests.get(sharepoint_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        # Try to extract list of objects from common SharePoint response keys
        if 'd' in data and 'results' in data['d']:
            objects = data['d']['results']
        elif 'value' in data:
            objects = data['value']
        else:
            objects = data
        logger.info(f"SharePoint query returned {len(objects) if isinstance(objects, list) else 'unknown'} objects.")
        return {
            "objects": objects,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error querying SharePoint: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }
        
# Add your prompts
@mcp.prompt()
def explain_available_tools() -> str:
    """Summarize what tools are available and what they do."""
    logger.info("explain_available_tools prompt called")
    base_tools = (
        "Available tools include: get_medicare_dataset_row_count (count rows in a dataset), "
        "get_medicare_document (read a document), list_medicare_documents (list all documents), "
        "get_medicare_dataset_columns (list dataset columns), and health (check server health)."
    )
    
    if AUTH_AVAILABLE:
        auth_tools = (
            " Authentication tools: authenticate_user (get user info and token)."
        )
        return base_tools + auth_tools
    else:
        return base_tools + " Authentication tools are not currently available."

def main():
    """Start the Medicare MCP server."""
    logger.info("Starting Medicare MCP server...")
    try:
        mcp.run(
            host="127.0.0.1",
            port=8000,
            transport="streamable-http"
        )
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise

if __name__ == "__main__":
    main()