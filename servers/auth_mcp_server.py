"""
Example integration of authentication with the MCP server.
This demonstrates how to add user authentication to the Medicare server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from auth_utils import get_user_info_and_token, get_user_token

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

# Create the MCP server (same as your existing code)
mcp = FastMCP("MCP Server with Auth Demo", version="1.0.0")

# Mount FastMCP routes onto FastAPI app
# Assuming FastMCP exposes a router or ASGI app via `mcp.router` or similar
# (Check FastMCP docs for exact attribute)
app.mount("/mcp", mcp)  # or app.include_router(mcp.router)

@mcp.tool()
def authenticate_user() -> dict:
    """
    Authenticate the current user and return their information and access token.
    This token can be used by the agent for further API calls.
    """
    result = get_user_info_and_token()

    if result["status"] == "success":
        # Return user info but truncate the token for security in logs
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
            "full_token": result["access_token"],  # Full token for agent use
        }
    else:
        return {"error": result["error"], "status": "authentication_failed"}


@mcp.tool()
def get_access_token_only() -> dict:
    """
    Get just the access token for API calls.
    Simplified version for when only the token is needed.
    Uses delegated Microsoft Graph scopes by default.
    """
    result = get_user_token()  # Uses default scopes like ['User.Read']

    if result["status"] == "success":
        return {
            "access_token": result["access_token"],
            "expires_on": result["expires_on"],  # ISO formatted datetime string
            "status": "success",
        }
    else:
        return {"error": result["error"], "status": "failed"}


@mcp.tool()
def verify_user_permissions(required_groups: list = None) -> dict:
    """
    Verify if the authenticated user has required permissions.

    Args:
        required_groups: List of group names the user should be a member of
    """
    if required_groups is None:
        required_groups = []

    user_info = get_user_info_and_token()

    if user_info["status"] != "success":
        return {
            "authorized": False,
            "error": "Authentication failed",
            "details": user_info["error"],
        }

    # In a real implementation, you would check actual group memberships
    # For now, we'll just check if user has any groups
    has_groups = user_info["group_count"] > 0

    return {
        "authorized": has_groups,
        "user": user_info["display_name"],
        "email": user_info["email"],
        "group_count": user_info["group_count"],
        "message": (
            "User has group memberships"
            if has_groups
            else "User has no group memberships"
        ),
    }


@mcp.prompt()
def explain_authentication() -> str:
    """Explain how authentication works in this MCP server."""
    return (
        "This MCP server supports user authentication through Microsoft Entra ID. "
        "Use the 'authenticate_user' tool to sign in and get an access token. The"
        "token can be used for subsequent API calls to Microsoft Graph or other Azure "
        "services. Use 'get_access_token_only' for a simplified token-only response, or"
        "'verify_user_permissions' to check if the user has required access."
    )


def main():
    """Start the Medicare MCP server."""
    try:
        mcp.run(host="127.0.0.1", port=8001, transport="streamable-http")
    except Exception as e:
        print(f"Error starting MCP server: {e}")
        raise


if __name__ == "__main__":
    main()
