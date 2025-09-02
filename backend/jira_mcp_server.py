from datetime import datetime, timezone
import os
import webbrowser
import logging
import threading
import asyncio
import requests

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
import uvicorn

load_dotenv()

CLIENT_ID = os.getenv("ATLASSIAN_CLIENT_ID")
CLIENT_SECRET = os.getenv("ATLASSIAN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ATLASSIAN_REDIRECT_URI")
AUTH_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
API_BASE_URL = "https://api.atlassian.com"
SCOPES = "read:jira-work"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Jira MCP Server", version="1.0.0")
# An asyncio.Future to hold the OAuth code once received
oauth_code_future = asyncio.Future()

async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    if code:
        if not oauth_code_future.done():
            oauth_code_future.set_result(code)
        content = "<h1>Authentication successful. You may close this window.</h1>"
    else:
        content = "<h1>Authentication failed. No code received.</h1>"
    return HTMLResponse(content)

routes = [
    Route("/callback", oauth_callback),
]

app = Starlette(routes=routes)

def run_oauth_server():
    # Run the Starlette app with Uvicorn in a separate thread or process
    uvicorn.run(app, host="127.0.0.1", port=8765)

@mcp.tool()
async def get_jira_consent_interactive() -> dict:
    # Start the OAuth redirect server in a background thread
    server_thread = threading.Thread(target=run_oauth_server, daemon=True)
    server_thread.start()

    # Build the consent URL
    auth_url = (
        f"{AUTH_URL}"
        f"?audience=api.atlassian.com"
        f"&client_id={CLIENT_ID}"
        f"&scope={SCOPES}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&prompt=consent"
    )

    # Open the user's default browser to the consent URL
    webbrowser.open(auth_url)

    # Wait asynchronously for the OAuth code to be set by the Starlette server
    code = await oauth_code_future

    # Exchange code for access token
    token_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    token_resp = requests.post(TOKEN_URL, json=token_data, timeout=15)
    token_resp.raise_for_status()
    tokens = token_resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        return {"error": "Failed to obtain access token."}

    # Get accessible Jira cloudid(s)
    resources_resp = requests.get(
        f"{API_BASE_URL}/oauth/token/accessible-resources",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resources_resp.raise_for_status()
    resources = resources_resp.json()
    if not resources:
        return {"error": "No accessible Jira resources found for this user."}

    cloudid = resources[0]["id"]

    return {
        "access_token": access_token,
        "cloudid": cloudid,
        "message": "Authentication successful. You can now query Jira.",
    }

@mcp.tool()
async def get_my_requests(
    access_token: str, cloudid: str, jql: str = "ORDER BY created DESC") -> dict:
    """
    Query Jira issues using the provided access token and cloudid.
    """
    search_url = f"https://api.atlassian.com/ex/jira/{cloudid}/rest/api/3/search"
    params = {"jql": jql, "maxResults": 5}
    issues_resp = requests.get(
        search_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        params=params,
        timeout=15,
    )
    issues_resp.raise_for_status()
    issues = issues_resp.json().get("issues", [])

    results = []
    for issue in issues:
        results.append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
        })

    return {"issues": results}

@mcp.tool()
async def custom_board_query() -> dict:
    # TODO: Talk to Hubert to implement this
    return {"message": "Not implemented yet."}

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
    http_app = mcp.http_app(
        transport="streamable-http",
        path="/mcp",
        middleware=custom_middleware
    )

    uvicorn.run(http_app, host='127.0.0.1', port=8003)

if __name__ == "__main__":
    main()
