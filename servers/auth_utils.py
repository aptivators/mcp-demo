"""
Authentication utilities for getting user tokens from Entra ID.
This module can be imported by other parts of the application.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from azure.identity import InteractiveBrowserCredential
from dotenv import load_dotenv

load_dotenv()
MS_ME_URL = "https://graph.microsoft.com/v1.0/me"


def get_user_token(scopes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Synchronously get an access token for Microsoft Graph or SharePoint using
    interactive login.

    Args:
        scopes: List of delegated scopes to request. Defaults to ['Sites.Read.All']
                for SharePoint access.
        client_id: Your Azure AD app's client ID. Required to avoid AADSTS65002 error.

    Returns:
        Dictionary with access token, expiration, status, and error info if any.
    """
    if scopes is None:
        scopes = ["Sites.Read.All"]  # Delegated scope for SharePoint access

    client_id = os.getenv("ENTRA_CLIENT_ID")
    if client_id is None:
        raise ValueError(
            "Entra Client ID must be provided for enterprise authentication."
        )

    try:
        credential = InteractiveBrowserCredential(client_id=client_id)
        token_request = credential.get_token(*scopes)

        expires_on_dt = datetime.fromtimestamp(token_request.expires_on)

        return {
            "access_token": token_request.token,
            "expires_on": expires_on_dt.isoformat(),
            "status": "success",
            "scopes": scopes,
        }
    except (
        ImportError,
        ValueError,
        requests.exceptions.RequestException,
        RuntimeError,
    ) as e:
        error_type = (
            type(e).__name__.replace("Exception", "").replace("Error", "").lower()
        )
        return {
            "access_token": None,
            "error": f"{error_type} error: {str(e)}",
            "status": "failed",
            "scopes": scopes,
        }


def get_user_info_and_token() -> Dict[str, Any]:
    """
    Get user information and access token using direct REST API calls.
    Uses get_user_token() for authentication and requests for HTTP calls.
    """
    # Use delegated scopes for user info and group membership
    scopes = ["User.Read", "GroupMember.Read.All"]
    token_result = get_user_token(scopes=scopes)

    if token_result["status"] != "success":
        return {
            "access_token": None,
            "error": token_result.get("error", "Unknown error"),
            "status": "failed",
        }

    access_token = token_result["access_token"]
    expires_on = token_result["expires_on"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:

        # Get user information
        user_response = requests.get(MS_ME_URL, headers=headers, timeout=10)
        user_response.raise_for_status()
        user_data = user_response.json()

        # Get group memberships
        groups_response = requests.get(
            f"{MS_ME_URL}/memberOf", headers=headers, timeout=10
        )
        groups_response.raise_for_status()
        groups_data = groups_response.json()

        return {
            "display_name": user_data.get("displayName"),
            "email": user_data.get("userPrincipalName"),
            "job_title": user_data.get("jobTitle"),
            "user_id": user_data.get("id"),
            "access_token": access_token,
            "token_expires_on": expires_on,
            "group_count": len(groups_data.get("value", [])),
            "status": "success",
        }

    except requests.exceptions.RequestException as e:
        return {
            "access_token": access_token,
            "error": f"HTTP error: {str(e)}",
            "status": "failed",
        }
    except KeyError as e:
        return {
            "access_token": access_token,
            "error": f"Missing key: {str(e)}",
            "status": "failed",
        }
