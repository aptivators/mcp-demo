"""
Enhanced authentication utilities with detailed group and role information.
This module provides comprehensive user authentication and authorization data.
"""

from typing import Any, Dict, List

import requests
from azure.identity import InteractiveBrowserCredential


def get_user_groups_and_roles(include_transitive: bool = True) -> Dict[str, Any]:
    """
    Get comprehensive group and role information for the authenticated user.

    Args:
        include_transitive: Include groups the user is a transitive member of

    Returns:
        Dictionary containing detailed group and role information
    """
    try:
        credential = InteractiveBrowserCredential()

        # Get the token with appropriate scopes
        token_request = credential.get_token("https://graph.microsoft.com/.default")
        access_token = token_request.token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Get basic user information
        user_response = requests.get(
            "https://graph.microsoft.com/v1.0/me", headers=headers, timeout=10
        )
        user_response.raise_for_status()
        user_data = user_response.json()

        # Get direct group memberships
        groups_url = "https://graph.microsoft.com/v1.0/me/memberOf"
        if include_transitive:
            groups_url = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf"

        groups_response = requests.get(groups_url, headers=headers, timeout=15)
        groups_response.raise_for_status()
        groups_data = groups_response.json()

        # Get directory roles (admin roles)
        roles_response = requests.get(
            "https://graph.microsoft.com/v1.0/me/memberOf/microsoft.graph.directoryRole",
            headers=headers,
            timeout=10,
        )
        roles_response.raise_for_status()
        roles_data = roles_response.json()

        # Process groups
        security_groups = []
        distribution_groups = []
        unified_groups = []  # Microsoft 365 groups
        other_groups = []

        for group in groups_data.get("value", []):
            group_info = {
                "id": group.get("id"),
                "display_name": group.get("displayName"),
                "description": group.get("description"),
                "type": group.get("@odata.type", "").split(".")[-1],
            }

            if group.get("@odata.type") == "#microsoft.graph.group":
                group_types = group.get("groupTypes", [])
                if "Unified" in group_types:
                    unified_groups.append(group_info)
                elif group.get("securityEnabled"):
                    security_groups.append(group_info)
                else:
                    distribution_groups.append(group_info)
            else:
                other_groups.append(group_info)

        # Process directory roles
        directory_roles = []
        for role in roles_data.get("value", []):
            role_info = {
                "id": role.get("id"),
                "display_name": role.get("displayName"),
                "description": role.get("description"),
                "role_template_id": role.get("roleTemplateId"),
            }
            directory_roles.append(role_info)

        # Get app role assignments (application-specific roles)
        app_roles_response = requests.get(
            "https://graph.microsoft.com/v1.0/me/appRoleAssignments",
            headers=headers,
            timeout=10,
        )
        app_roles_response.raise_for_status()
        app_roles_data = app_roles_response.json()

        app_roles = []
        for app_role in app_roles_data.get("value", []):
            app_role_info = {
                "id": app_role.get("id"),
                "app_role_id": app_role.get("appRoleId"),
                "resource_display_name": app_role.get("resourceDisplayName"),
                "resource_id": app_role.get("resourceId"),
                "principal_display_name": app_role.get("principalDisplayName"),
            }
            app_roles.append(app_role_info)

        return {
            "user": {
                "id": user_data.get("id"),
                "display_name": user_data.get("displayName"),
                "user_principal_name": user_data.get("userPrincipalName"),
                "job_title": user_data.get("jobTitle"),
                "department": user_data.get("department"),
                "office_location": user_data.get("officeLocation"),
            },
            "groups": {
                "security_groups": security_groups,
                "distribution_groups": distribution_groups,
                "unified_groups": unified_groups,  # Microsoft 365 groups
                "other_groups": other_groups,
                "total_count": len(groups_data.get("value", [])),
            },
            "roles": {
                "directory_roles": directory_roles,
                "app_roles": app_roles,
                "is_admin": len(directory_roles) > 0,
            },
        }, {
            "authentication": {
                "access_token": access_token,
                "expires_on": token_request.expires_on,
                "status": "success",
            }
        }

    except requests.exceptions.RequestException as e:
        return {}, {
            "authentication": {"error": f"Request error: {str(e)}", "status": "failed"}
        }
    except ImportError as e:
        return {}, {
            "authentication": {
                "error": f"Import error: {str(e)}",
                "status": "failed",
            }
        }
    except AttributeError as e:
        return {}, {
            "authentication": {
                "error": f"Attribute error: {str(e)}",
                "status": "failed",
            }
        }
    except (ValueError, KeyError, TypeError) as e:
        return {}, {
            "authentication": {
                "error": f"Data error: {str(e)}",
                "status": "failed",
            }
        }


def check_user_permissions(
    required_groups: List[str] = None, required_roles: List[str] = None
) -> Dict[str, Any]:
    """
    Check if the authenticated user has specific group memberships or roles.

    Args:
        required_groups: List of group display names to check for
        required_roles: List of role display names to check for

    Returns:
        Dictionary with authorization details
    """
    if required_groups is None:
        required_groups = []
    if required_roles is None:
        required_roles = []

    user_data, auth_data = get_user_groups_and_roles()

    if auth_data["authentication"]["status"] != "success":
        return {
            "authorized": False,
            "error": "Failed to retrieve user information",
            "details": auth_data["authentication"].get("error", "Unknown error"),
        }

    # Check group memberships
    user_groups = []
    for group_type in [
        "security_groups",
        "distribution_groups",
        "unified_groups",
        "other_groups",
    ]:
        for group in user_data["groups"][group_type]:
            user_groups.append(group["display_name"])

    # Check roles
    user_roles = []
    for role in user_data["roles"]["app_roles"]:
        user_roles.append(role["resource_display_name"])

    # Check if user has required groups
    missing_groups = [group for group in required_groups if group not in user_groups]
    has_required_groups = len(missing_groups) == 0

    # Check if user has required roles
    missing_roles = [role for role in required_roles if role not in user_roles]
    has_required_roles = len(missing_roles) == 0

    authorized = has_required_groups and has_required_roles

    return {
        "authorized": authorized,
        "user": user_data["user"]["display_name"],
        "email": user_data["user"]["user_principal_name"],
        "groups": {
            "user_groups": user_groups,
            "required_groups": required_groups,
            "missing_groups": missing_groups,
            "has_required_groups": has_required_groups,
        },
        "roles": {
            "user_roles": user_roles,
            "required_roles": required_roles,
            "missing_roles": missing_roles,
            "has_required_roles": has_required_roles,
            "is_admin": user_data["roles"]["is_admin"],
        },
        "status": "success",
    }


def get_user_admin_roles() -> Dict[str, Any]:
    """
    Get only the administrative roles for the authenticated user.
    Useful for checking admin permissions quickly.
    """
    try:
        credential = InteractiveBrowserCredential()
        token_request = credential.get_token("https://graph.microsoft.com/.default")
        access_token = token_request.token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Get directory roles only
        roles_response = requests.get(
            "https://graph.microsoft.com/v1.0/me/memberOf/microsoft.graph.directoryRole",
            headers=headers,
            timeout=10,
        )
        roles_response.raise_for_status()
        roles_data = roles_response.json()

        admin_roles = []
        for role in roles_data.get("value", []):
            admin_roles.append(
                {
                    "display_name": role.get("displayName"),
                    "description": role.get("description"),
                    "role_template_id": role.get("roleTemplateId"),
                }
            )

        return {
            "admin_roles": admin_roles,
            "is_admin": len(admin_roles) > 0,
            "role_count": len(admin_roles),
            "status": "success",
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}", "status": "failed"}
    except ImportError as e:
        return {"error": f"Import error: {str(e)}", "status": "failed"}
    except AttributeError as e:
        return {"error": f"Attribute error: {str(e)}", "status": "failed"}
    except (ValueError, KeyError, TypeError) as e:
        return {"error": f"Data error: {str(e)}", "status": "failed"}
