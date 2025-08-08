# Authentication Integration for MCP Demo

This document describes the authentication capabilities added to the MCP demo project for integrating with Microsoft Entra ID (formerly Azure AD).

## Files Added

### 1. `auth-user.py`

Main authentication script that demonstrates user authentication and token generation.

**Key Functions:**

- `get_user_info_with_token()`: Authenticates user and returns comprehensive info + token
- `get_user_token_only()`: Returns just the access token
- `main()`: Demo function showing authentication flow

**Usage:**

```bash
uv run python auth-user.py
```

### 2. `auth_utils.py`

Utility module for authentication that can be imported by other parts of the application.

**Key Functions:**

- `get_user_token(scopes)`: Synchronous token retrieval
- `get_user_token_async(scopes)`: Async version of token retrieval  
- `get_user_info_and_token()`: Complete user info + token
- `main()`: Test function for all utilities

**Usage:**

```python
from auth_utils import get_user_token, get_user_info_and_token

# Get just a token
token_result = get_user_token()
if token_result["status"] == "success":
    access_token = token_result["access_token"]

# Get user info and token
user_result = get_user_info_and_token()
if user_result["status"] == "success":
    user_name = user_result["display_name"]
    access_token = user_result["access_token"]
```

### 3. `auth_mcp_server.py`

Standalone MCP server focused on authentication functionality.

**Available Tools:**

- `authenticate_user()`: Get user info and access token
- `get_access_token_only()`: Get just the access token
- `verify_user_permissions()`: Check user permissions/groups

**Usage:**

```bash
uv run mcp dev auth_mcp_server.py
```

### 4. Updated `servers/medicare_server.py`

Enhanced the main Medicare server with authentication capabilities.

**New Tools Added:**

- `authenticate_user()`: User authentication for Medicare server
- `get_user_access_token()`: Token-only authentication

**New Prompts Added:**

- `explain_authentication()`: How authentication works
- Updated `explain_available_tools()`: Now includes auth tools
- Updated `explain_role_escalation_policy()`: Mentions authentication

## Dependencies Added

The following packages were added to `pyproject.toml`:

```toml
"azure-identity>=1.23.1",
"msgraph-sdk>=1.40.0",
```

## Authentication Flow

1. **User Interaction**: When authentication tools are called, a browser window opens
2. **Entra ID Login**: User signs in with their organizational credentials
3. **Token Generation**: System receives an access token for Microsoft Graph
4. **Token Return**: Token is returned to the agent interface for further API calls

## Token Information Returned

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJub25jZSI6...",
  "expires_on": 1753988512,
  "display_name": "User, Name (Organization)",
  "email": "user@organization.com",
  "job_title": "Job Title",
  "group_count": 70,
  "status": "success"
}
```

## Use Cases for Agents

1. **Authentication**: Get user credentials for Microsoft services
2. **User Context**: Understand who is making requests
3. **Authorization**: Check user permissions/group memberships
4. **API Access**: Use tokens for Microsoft Graph, Azure, or Office 365 APIs
5. **Personalization**: Customize responses based on user information

## Security Considerations

- Tokens are short-lived (typically 1 hour)
- Authentication uses Microsoft's secure OAuth 2.0 flow
- Tokens should be treated as sensitive information
- Only display token previews in logs, not full tokens

## Integration with Existing MCP Tools

The authentication system is designed to be non-invasive:

- Existing tools continue to work without authentication
- Authentication tools are optional add-ons
- Graceful fallback when authentication packages aren't installed
- Clear error messages when authentication isn't available

## Next Steps

1. **Enhanced Permissions**: Add specific group/role checking
2. **Token Caching**: Implement persistent token storage
3. **Multiple Scopes**: Support different API scopes beyond Microsoft Graph  
4. **Silent Refresh**: Automatic token renewal
5. **Admin Consent**: Handle applications requiring admin consent
