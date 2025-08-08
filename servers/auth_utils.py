"""
Authentication utilities for getting user tokens from Entra ID.
This module can be imported by other parts of the application.
"""

from azure.identity import InteractiveBrowserCredential
import asyncio
from typing import Optional, Dict, Any
import requests
from msgraph import GraphServiceClient
import concurrent.futures

def get_user_token(scopes: Optional[list] = None) -> Dict[str, Any]:
    """
    Synchronous function to get user access token.
    
    Args:
        scopes: List of scopes to request. Defaults to Microsoft Graph.
        
    Returns:
        Dictionary containing token info or error details.
    """
    if scopes is None:
        scopes = ["https://graph.microsoft.com/.default"]
    
    try:
        credential = InteractiveBrowserCredential()
        token_request = credential.get_token(*scopes)
        
        return {
            "access_token": token_request.token,
            "expires_on": token_request.expires_on,
            "status": "success",
            "scopes": scopes
        }
    except Exception as e:
        return {
            "access_token": None,
            "error": str(e),
            "status": "failed",
            "scopes": scopes
        }

async def get_user_token_async(scopes: Optional[list] = None) -> Dict[str, Any]:
    """
    Async version of get_user_token for use in async contexts.
    """
    return get_user_token(scopes)

def get_user_info_and_token() -> Dict[str, Any]:
    """
    Get both user information and access token.
    Returns comprehensive user data for agent interface.
    """
    try:
        credential = InteractiveBrowserCredential()
        client = GraphServiceClient(credential)
        
        # Handle existing event loop gracefully
        try:
            # Try to get the current running loop
            current_loop = asyncio.get_running_loop()
            # If we're in an existing loop, we need to run in a thread           
            
            def run_async_in_thread():
                # Create a new event loop in this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    user = new_loop.run_until_complete(client.me.get())
                    groups = new_loop.run_until_complete(client.me.member_of.get())
                    return user, groups
                finally:
                    new_loop.close()
            
            # Run the async operations in a separate thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                user, groups = future.result(timeout=30)  # 30 second timeout
                
        except RuntimeError:
            # No event loop running, we can create our own
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                user = loop.run_until_complete(client.me.get())
                groups = loop.run_until_complete(client.me.member_of.get())
            finally:
                loop.close()
        
        # Get the token
        token_request = credential.get_token("https://graph.microsoft.com/.default")
        
        return {
            "display_name": user.display_name,
            "email": user.user_principal_name,
            "job_title": user.job_title,
            "user_id": user.id,
            "access_token": token_request.token,
            "token_expires_on": token_request.expires_on,
            "group_count": len(groups.value) if groups and groups.value else 0,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "access_token": None,
            "error": str(e),
            "status": "failed"
        }

def get_user_info_and_token_simple() -> Dict[str, Any]:
    """
    Get user information and access token using direct REST API calls.
    This avoids async/event loop issues by using the requests library.
    """
    try:
        credential = InteractiveBrowserCredential()
        
        # Get the token first
        token_request = credential.get_token("https://graph.microsoft.com/.default")
        access_token = token_request.token
        
        # Use the token to make direct REST API calls
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get user information
        user_response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers,
            timeout=10
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # Get group memberships
        groups_response = requests.get(
            'https://graph.microsoft.com/v1.0/me/memberOf',
            headers=headers,
            timeout=10
        )
        groups_response.raise_for_status()
        groups_data = groups_response.json()
        
        return {
            "display_name": user_data.get("displayName"),
            "email": user_data.get("userPrincipalName"),
            "job_title": user_data.get("jobTitle"),
            "user_id": user_data.get("id"),
            "access_token": access_token,
            "token_expires_on": token_request.expires_on,
            "group_count": len(groups_data.get("value", [])),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "access_token": None,
            "error": str(e),
            "status": "failed"
        }
