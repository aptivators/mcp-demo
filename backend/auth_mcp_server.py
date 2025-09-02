import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastmcp import FastMCP
import requests
from azure.identity import InteractiveBrowserCredential
from dotenv import load_dotenv
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

MS_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"

mcp = FastMCP("MCP Server with Authentication", version="1.0.0")

def get_user_and_sharepoint_token() -> Dict[str, Any]:
    """
    Acquire a delegated access token for SharePoint and Graph, and return user info.

    Returns:
        Dict with sharepoint_access_token, graph_access_token, expires_on, user info, 
        status, and error if any.
    """
    tenant_short_name = os.getenv("SP_COMPANY")
    if not tenant_short_name:
        raise ValueError("SP_COMPANY environment variable must be set.")

    client_id = os.getenv("ENTRA_CLIENT_ID")
    tenant_id = os.getenv("ENTRA_TENANT_ID")

    if not client_id or not tenant_id:
        raise ValueError("ENTRA_CLIENT_ID and ENTRA_TENANT_ID must be set.")

    try:
        credential = InteractiveBrowserCredential(client_id=client_id, tenant_id=tenant_id)

        # 1. Get Graph token for user info
        graph_scopes = ["User.Read"]
        graph_token = credential.get_token(*graph_scopes)
        graph_expires_on_dt = datetime.fromtimestamp(graph_token.expires_on)
        headers = {"Authorization": f"Bearer {graph_token.token}"}
        graph_response = requests.get(MS_GRAPH_ME_URL, headers=headers, timeout=15)
        graph_response.raise_for_status()
        user_info = graph_response.json()

        # 2. Get SharePoint token for SharePoint access
        sp_scopes = [f"https://{tenant_short_name}.sharepoint.com/.default"]
        sp_token = credential.get_token(*sp_scopes)
        sp_expires_on_dt = datetime.fromtimestamp(sp_token.expires_on)

        return {
            "authentication": {
                "sharepoint_access_token": sp_token.token,
                "sharepoint_expires_on": sp_expires_on_dt.isoformat(),
                "graph_access_token": graph_token.token,
                "graph_expires_on": graph_expires_on_dt.isoformat(),
                "status": "authenticated"
            },
            "user": user_info,
            "status": "success"
        }
    except (requests.RequestException, ValueError, RuntimeError) as e:
        logger.error("Error obtaining token or user info: %s", str(e))
        return {
            "authentication": None,
            "user": None,
            "error": str(e),
            "status": "failed"
        }

@mcp.tool()
async def get_service_token() -> dict:
    result = get_user_and_sharepoint_token()
    logger.info("Token result: %s", result)
    if result["status"] == "success":
        authentication = result.get("authentication", {})
        return {
            "user": result.get("user"),
            "authentication": {
                "status": authentication.get("status", "authenticated"),
                "access_token": authentication.get("sharepoint_access_token"),
                "expires_on": authentication.get("sharepoint_expires_on"),
                "graph_access_token": authentication.get("graph_access_token"),
                "graph_expires_on": authentication.get("graph_expires_on"),
            },
            "status": "success",
        }
    return {"error": result.get("error", "Unknown error"), "status": "authentication_failed"}

@mcp.tool()
async def health() -> dict:
    return {
        "status": "ok", 
        "message": "Service is running.", 
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except (ValueError, RuntimeError, requests.RequestException) as exc:
            logger.error("Error handling request: %s", exc)
            return JSONResponse({"error": str(exc)}, status_code=400)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("Incoming request: %s %s", request.method, request.url)
        try:
            body = await request.body()
            logger.info("Request body: %s", body.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            logger.info("Could not read request body")
        response = await call_next(request)
        logger.info("Response status: %s", response.status_code)
        return response

# Define custom middleware
custom_middleware = [
    Middleware(CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id"]
            ),
    Middleware(ErrorLoggingMiddleware),
    Middleware(LoggingMiddleware),

]

def main():
    """Start the Medicare MCP server."""
    try:
        http_app = mcp.http_app(transport="streamable-http",
                                path="/mcp",
                                middleware=custom_middleware
                                )
        uvicorn.run(http_app, host='127.0.0.1', port=8001)
    except Exception as e:
        print(f"Error starting MCP server: {e}")
        raise

if __name__ == "__main__":
    main()
