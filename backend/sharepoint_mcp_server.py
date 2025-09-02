from datetime import datetime, timezone
import os
import logging
from contextvars import ContextVar
import requests

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware
from dotenv import load_dotenv
from jose import jwt
import uvicorn

load_dotenv()

current_token = ContextVar("current_token")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("SharePoint MCP Server", version="1.0.0")

@mcp.tool()
async def get_sharepoint_files() -> dict:
    """Query a SharePoint URL using a provided access token and return the
    list of objects."""
    token = context.data["token"]
    tenant_name = os.getenv("SP_COMPANY", "")
    site_path = os.getenv("SP_SITEPATH", "")
    folder_rel_url = os.getenv("SP_FOLDER", "")
    sharepoint_api_url = (
        f"https://{tenant_name}.sharepoint.com{site_path}"
        f"/_api/web/GetFolderByServerRelativeUrl('{folder_rel_url}')/Files"
    )
    print(f"SharePoint API URL: {sharepoint_api_url}")
    logger.info("query_sharepoint called for URL: %s", sharepoint_api_url)

    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;odata=verbose",
        }
        response = requests.get(sharepoint_api_url, headers=headers, timeout=15)
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

@mcp.tool()
async def health() -> dict:
    return {
        "status": "ok", 
        "message": "Service is running.", 
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

@mcp.prompt()
async def list_sharepoint_files_prompt() -> str:
    return (
        "You are an AI assistant with access to SharePoint files. "
        "Use the get_sharepoint_files tool to list files in the configured SharePoint folder. "
        "Provide the user with a summary of the files available."
    )

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
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

class AzureTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401)
        token = auth_header.split(" ")[1]
        context["token"] = token
        # Optionally decode for logging/claims, but do not verify signature
        try:
            claims = jwt.get_unverified_claims(token)
            logger.info("Token claims: %s", claims)
            request.state.user = claims
            request.state.token = token
            current_token.set(token)
        except jwt.JWTError as e:
            logger.warning("Could not decode JWT claims: %s", e)
        return await call_next(request)

custom_middleware = [
    Middleware(CORSMiddleware,
               allow_origins=["*"],
               allow_methods=["*"],
               allow_headers=["*"],
               expose_headers=["mcp-session-id"]),
    Middleware(RawContextMiddleware),
    Middleware(ErrorLoggingMiddleware),
    Middleware(LoggingMiddleware),
    Middleware(AzureTokenMiddleware),
]

def main():
    http_app = mcp.http_app(
        transport="streamable-http",
        path="/mcp",
        middleware=custom_middleware
    )

    uvicorn.run(http_app, host='127.0.0.1', port=8002)

if __name__ == "__main__":
    main()
