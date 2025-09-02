import json
import requests

def get_service_token():
    base_url = "http://127.0.0.1:8001/mcp"
    headers = {
        'accept': 'application/json, text/event-stream',
        'content-type': 'application/json'
    }

    print("check 1")

    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "python-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }

    response = requests.post(base_url, headers=headers, json=init_payload, timeout=30)
    session_id = response.headers.get('mcp-session-id')
    print(f"Session ID: {session_id}")

    if not session_id:
        print("No session ID received")
        return None

    headers['mcp-session-id'] = session_id

    # Send notifications/initialized with session header
    init_complete_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }

    requests.post(base_url, headers=headers, json=init_complete_payload, timeout=30)
    print("Initialization complete")

    add_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_service_token"
        },
        "id": 2
    }

    response = requests.post(base_url, headers=headers, json=add_payload, timeout=30)

    lines = response.text.split('\n')
    data_line = next((line for line in lines if line.startswith('data: ')), None)

    if data_line:
        json_data = data_line[6:]
        result = json.loads(json_data)
        token_json = result['result']['content'][0]['text']
        print(f"Add result: {token_json}")
    else:
        print("No data found in response")
        print("Raw response:", response.text)
        return None

    print("Test complete")
    # Parse the returned JSON string
    try:
        token_info = json.loads(token_json)
        if token_info.get('status') != 'success':
            print(f"Token retrieval failed: {token_info.get('error')}")
            return None
        access_token = token_info['authentication']['access_token']
        print(f"Access Token: {access_token[:20]}...")  # Print a preview of the token
        return access_token
    except json.JSONDecodeError as e:
        print(f"Error parsing token: {e}")
        return None

def test_sharepoint_access(access_token):
    """Test SharePoint access via the SharePoint MCP server."""
    base_url = "http://127.0.0.1:8002/mcp"
    headers = {
        'accept': 'application/json, text/event-stream',
        'content-type': 'application/json',
        'authorization': f'Bearer {access_token}'
    }
    # Initialize session
    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "python-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    response = requests.post(base_url, headers=headers, json=init_payload, timeout=10)
    session_id = response.headers.get('mcp-session-id')
    if not session_id:
        print("No session ID received from SharePoint MCP")
        return
    headers['mcp-session-id'] = session_id

    # Send notifications/initialized with session header
    init_complete_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    requests.post(base_url, headers=headers, json=init_complete_payload, timeout=10)

    # Call SharePoint tool
    sp_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_sharepoint_files"
        },
        "id": 2
    }
    response = requests.post(base_url, headers=headers, json=sp_payload, timeout=10)
    print("SharePoint MCP response:", response.text)
    lines = response.text.split('\n')
    data_line = next((line for line in lines if line.startswith('data: ')), None)
    if data_line:
        json_data = data_line[6:]
        result = json.loads(json_data)
        answer = result['result']['content'][0]['text']
        print(f"SharePoint result: {answer}")
    else:
        print("No data found in SharePoint MCP response")

def test_fastmcp_server():
    try:
        print("Testing Auth MCP server for token...")
        access_token = get_service_token()
        if not access_token:
            print("No access token retrieved, aborting SharePoint test.")
            return
        print(f"Access token (preview): {access_token[:20]}...")
    except requests.exceptions.ConnectionError:
        print("Check MCP its not working on port 8001")
        return
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return

    try:
        print("Testing SharePoint MCP server access...")
        test_sharepoint_access(access_token)
        print("SharePoint access test complete.")
    except requests.exceptions.ConnectionError:
        print("Check MCP its not working on port 8002")
    except requests.exceptions.RequestException as e:
        print(f"Request error in SharePoint access test: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error in SharePoint access test: {e}")

    try:
        print("Testing list_files tool...")
        test_list_files(access_token)
        print("list_files test complete.")
    except requests.exceptions.RequestException as e:
        print(f"Request error in list_files test: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error in list_files test: {e}")

def test_list_files(access_token):
    """Test the new list_files tool on the SharePoint MCP server."""
    base_url = "http://127.0.0.1:8002/mcp"
    headers = {
        'accept': 'application/json, text/event-stream',
        'content-type': 'application/json',
        'authorization': f'Bearer {access_token}'
    }

    # Initialize MCP session
    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "python-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    response = requests.post(base_url, headers=headers, json=init_payload, timeout=10)
    session_id = response.headers.get('mcp-session-id')
    if not session_id:
        print("No session ID received from SharePoint MCP")
        return
    headers['mcp-session-id'] = session_id

    # Send notifications/initialized with session header
    init_complete_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    requests.post(base_url, headers=headers, json=init_complete_payload, timeout=10)

    # Call the list_files tool
    list_files_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "list_files"
        },
        "id": 2
    }
    response = requests.post(base_url, headers=headers, json=list_files_payload, timeout=10)
    print("list_files MCP response:", response.text)

    # Parse the streamed response
    lines = response.text.split('\n')
    data_line = next((line for line in lines if line.startswith('data: ')), None)
    if data_line:
        json_data = data_line[6:]
        result = json.loads(json_data)
        answer = result['result']['content'][0]['text']
        print(f"list_files result: {answer}")
    else:
        print("No data found in list_files MCP response")

if __name__ == "__main__":
    test_fastmcp_server()
