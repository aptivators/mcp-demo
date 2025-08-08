import functools

try:
    from auth_groups_roles import get_user_admin_roles, check_user_permissions
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


def require_admin(func):
    """
    Decorator that requires the user to have administrative roles in Entra ID.
    This checks actual directory roles, not just a parameter.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not AUTH_AVAILABLE:
            # Fallback to the old behavior if authentication is not available
            if kwargs.get('user_role') != 'admin':
                return {"error": "Admin access required. Authentication system not available."}
            return func(*args, **kwargs)
        
        try:
            # Check if user has admin roles in Entra ID
            admin_result = get_user_admin_roles()
            
            if admin_result.get("status") != "success":
                return {
                    "error": "Authentication failed",
                    "details": admin_result.get("error", "Unable to verify admin status")
                }
            
            if not admin_result.get("is_admin", False):
                return {
                    "error": "Admin access required",
                    "details": "User does not have administrative roles in Entra ID",
                    "user_roles": admin_result.get("admin_roles", [])
                }
            
            # User is verified as admin, proceed with the function
            return func(*args, **kwargs)
            
        except Exception as e:
            return {
                "error": "Admin verification failed",
                "details": str(e)
            }
    
    return wrapper


def require_groups(required_groups):
    """
    Decorator that requires the user to be a member of specific groups in Entra ID.
    
    Args:
        required_groups: String or list of group names that the user must be a member of
    """
    # Ensure required_groups is always a list
    if isinstance(required_groups, str):
        required_groups = [required_groups]
    elif not isinstance(required_groups, list):
        required_groups = list(required_groups)
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not AUTH_AVAILABLE:
                return {"error": f"Group access required: {required_groups}. Authentication system not available."}
            
            try:
                # Check if user has required group memberships
                permission_result = check_user_permissions(required_groups=required_groups)
                
                if permission_result.get("status") != "success":
                    return {
                        "error": "Authentication failed",
                        "details": permission_result.get("error", "Unable to verify group membership")
                    }
                
                if not permission_result.get("authorized", False):
                    return {
                        "error": "Group membership required",
                        "details": f"User must be a member of: {required_groups}",
                        "missing_groups": permission_result.get("groups", {}).get("missing_groups", []),
                        "user_groups": permission_result.get("groups", {}).get("user_groups", [])
                    }
                
                # User has required group memberships, proceed with the function
                return func(*args, **kwargs)
                
            except Exception as e:
                return {
                    "error": "Group verification failed",
                    "details": str(e)
                }
        
        return wrapper
    return decorator


def require_roles(required_roles):
    """
    Decorator that requires the user to have specific directory roles in Entra ID.
    
    Args:
        required_roles: String or list of role names that the user must have
    """
    # Ensure required_roles is always a list
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    elif not isinstance(required_roles, list):
        required_roles = list(required_roles)
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not AUTH_AVAILABLE:
                return {"error": f"Role access required: {required_roles}. Authentication system not available."}
            
            try:
                # Check if user has required roles
                permission_result = check_user_permissions(required_roles=required_roles)
                
                if permission_result.get("status") != "success":
                    return {
                        "error": "Authentication failed",
                        "details": permission_result.get("error", "Unable to verify roles")
                    }
                
                if not permission_result.get("authorized", False):
                    return {
                        "error": "Role access required",
                        "details": f"User must have roles: {required_roles}",
                        "missing_roles": permission_result.get("roles", {}).get("missing_roles", []),
                        "user_roles": permission_result.get("roles", {}).get("user_roles", [])
                    }
                
                # User has required roles, proceed with the function
                return func(*args, **kwargs)
                
            except Exception as e:
                return {
                    "error": "Role verification failed",
                    "details": str(e)
                }
        
        return wrapper
    return decorator