#!/usr/bin/env python3
"""
Test script for the AI Agent Web Service
Tests the agent's ability to query SharePoint MCP server for file listings
"""

import requests
import sys
from typing import Dict, Any, Optional


class AgentTester:
    """Test client for the AI Agent Web Service"""
    
    def __init__(self, agent_base_url: str = "https://127.0.0.1:8080"):
        self.agent_base_url = agent_base_url.rstrip('/')
        self.session = requests.Session()
        # Disable SSL verification for local testing with self-signed certs
        self.session.verify = False
        # Suppress SSL warnings for cleaner output
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def test_agent_health(self) -> bool:
        """Test if the agent service is healthy and responsive"""
        try:
            print("Testing agent health...")
            response = self.session.get(
                f"{self.agent_base_url}/health", 
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"Agent health status: {health_data.get('status', 'unknown')}")
                
                # Print server health details
                servers = health_data.get('servers', {})
                for server_name, is_healthy in servers.items():
                    status = "✓ healthy" if is_healthy else "✗ unhealthy"
                    print(f"  - {server_name}: {status}")
                
                return health_data.get('status') in ['healthy', 'degraded']
            else:
                print(f"Health check failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to agent service: {e}")
            return False
    
    def test_agent_info(self) -> bool:
        """Test the agent info endpoint"""
        try:
            print("\nTesting agent info endpoint...")
            response = self.session.get(
                f"{self.agent_base_url}/", 
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                info_data = response.json()
                print(f"Agent name: {info_data.get('name', 'Unknown')}")
                print(f"Description: {info_data.get('description', 'N/A')}")
                print(f"Available servers: {', '.join(info_data.get('servers', []))}")
                return True
            else:
                print(f"Info endpoint failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to get agent info: {e}")
            return False
    
    def test_list_servers(self) -> bool:
        """Test listing all configured servers"""
        try:
            print("\nTesting server listing...")
            response = self.session.get(
                f"{self.agent_base_url}/servers", 
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                servers_data = response.json()
                print(f"Found {len(servers_data)} configured servers:")
                
                for server in servers_data:
                    name = server.get('name', 'Unknown')
                    server_id = server.get('server_id', 'unknown')
                    status = server.get('status', 'unknown')
                    health = "✓" if server.get('health', False) else "✗"
                    
                    print(f"  - {name} ({server_id}): {status} {health}")
                    
                    # Show capabilities
                    capabilities = server.get('capabilities', {})
                    tools = capabilities.get('tools', [])
                    resources = capabilities.get('resources', [])
                    
                    if tools:
                        print(f"    Tools: {', '.join(tools)}")
                    if resources:
                        print(f"    Resources: {', '.join(resources)}")
                
                return True
            else:
                print(f"Server listing failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to list servers: {e}")
            return False
    
    def query_agent(self, query: str, include_mcp_data: bool = True) -> Optional[Dict[str, Any]]:
        """Send a query to the AI agent"""
        try:
            print(f"\nQuerying agent: '{query}'")
            
            payload = {
                "query": query,
                "stream": False,
                "include_mcp_data": include_mcp_data
            }
            
            response = self.session.post(
                f"{self.agent_base_url}/query",
                headers=self.headers,
                json=payload,
                timeout=30  # Longer timeout for AI processing
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("Agent response:")
                print(f"  Response: {result.get('response', 'No response')}")
                
                sources = result.get('sources', [])
                if sources:
                    print(f"  Sources: {', '.join(sources)}")
                
                mcp_data = result.get('mcp_data', {})
                if mcp_data:
                    print("  MCP Data retrieved:")
                    for server, data in mcp_data.items():
                        print(f"    {server}: {len(str(data))} chars")
                
                return result
            else:
                print(f"Query failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to query agent: {e}")
            return None
    
    def test_direct_tool_call(self, server_id: str, tool_name: str, arguments: Dict[str, Any] = None) -> bool:
        """Test calling a tool directly on a specific server"""
        try:
            print(f"\nTesting direct tool call: {server_id}.{tool_name}")
            
            payload = {
                "arguments": arguments or {}
            }
            
            response = self.session.post(
                f"{self.agent_base_url}/servers/{server_id}/tools/{tool_name}",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("Tool call result:")
                print(f"  Server: {result.get('server', 'unknown')}")
                print(f"  Tool: {result.get('tool', 'unknown')}")
                
                tool_result = result.get('result', {})
                if isinstance(tool_result, dict):
                    # Handle MCP tool result format
                    if 'content' in tool_result:
                        content = tool_result['content']
                        if isinstance(content, list) and content:
                            print(f"  Content: {content[0].get('text', 'No text')[:200]}...")
                        else:
                            print(f"  Content: {content}")
                    else:
                        print(f"  Result: {str(tool_result)[:200]}...")
                else:
                    print(f"  Result: {str(tool_result)[:200]}...")
                
                return True
            else:
                print(f"Tool call failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to call tool: {e}")
            return False
    
    def test_auth_and_sharepoint_flow(self) -> bool:
        """Test the complete auth + SharePoint flow"""
        try:
            print("\nTesting complete auth + SharePoint flow...")
            
            # Step 1: Get token from auth server
            print("  Step 1: Getting service token...")
            auth_result = self.test_direct_tool_call("auth_mcp", "get_service_token")
            if not auth_result:
                print("  ✗ Failed to get service token")
                return False
            
            print("  ✓ Service token obtained")
            
            # Step 2: Use token to access SharePoint
            print("  Step 2: Accessing SharePoint with token...")
            sp_result = self.test_direct_tool_call("sharepoint_mcp", "get_sharepoint_files")
            if not sp_result:
                print("  ✗ Failed to get SharePoint files")
                return False
            
            print("  ✓ SharePoint files retrieved successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Auth + SharePoint flow failed: {e}")
            return False


def main():
    """Main test function"""
    print("=== AI Agent Test Suite ===")
    print("Testing agent's ability to query SharePoint MCP server for file listings")
    print("Auth MCP Server: 127.0.0.1:8001 | SharePoint MCP Server: 127.0.0.1:8002 | Agent: 127.0.0.1:8080\n")
    
    # Initialize tester
    agent_url = "https://127.0.0.1:8080"  # Default agent URL with HTTPS
    tester = AgentTester(agent_url)
    
    # Test sequence
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Agent health
    total_tests += 1
    if tester.test_agent_health():
        tests_passed += 1
        print("✓ Agent health test passed")
    else:
        print("✗ Agent health test failed")
        print("Cannot proceed with further tests - agent is not healthy")
        return 1
    
    # Test 2: Agent info
    total_tests += 1
    if tester.test_agent_info():
        tests_passed += 1
        print("✓ Agent info test passed")
    else:
        print("✗ Agent info test failed")
    
    # Test 3: List servers
    total_tests += 1
    if tester.test_list_servers():
        tests_passed += 1
        print("✓ Server listing test passed")
    else:
        print("✗ Server listing test failed")
    
    # Test 4: Test auth server token retrieval
    total_tests += 1
    auth_server_id = "auth_mcp"  # Updated to match your config
    if tester.test_direct_tool_call(auth_server_id, "get_service_token"):
        tests_passed += 1
        print("✓ Auth server token retrieval passed")
    else:
        print("✗ Auth server token retrieval failed")
    
    # Test 5: Test complete auth + SharePoint flow
    total_tests += 1
    if tester.test_auth_and_sharepoint_flow():
        tests_passed += 1
        print("✓ Complete auth + SharePoint flow test passed")
    else:
        print("✗ Complete auth + SharePoint flow test failed")
    
    # Test 6: Direct tool call to SharePoint server for file listing
    total_tests += 1
    sharepoint_server_id = "sharepoint_mcp"  # Updated to match your config
    if tester.test_direct_tool_call(sharepoint_server_id, "get_sharepoint_files"):
        tests_passed += 1
        print("✓ Direct SharePoint list_files tool call passed")
    else:
        print("✗ Direct SharePoint list_files tool call failed")
    
    # Test 7: Agent query for SharePoint files
    total_tests += 1
    queries_to_test = [
        "List all files in SharePoint",
        "What files are available in SharePoint?",
        "Show me the SharePoint file listing",
        "Get SharePoint files"
    ]
    
    query_success = False
    for query in queries_to_test:
        result = tester.query_agent(query, include_mcp_data=True)
        if result and result.get('response'):
            query_success = True
            print(f"✓ Agent query test passed with: '{query}'")
            break
    
    if query_success:
        tests_passed += 1
    else:
        print("✗ Agent query test failed for all test queries")
    
    # Test 8: Agent query without MCP data (AI-only response)
    total_tests += 1
    result = tester.query_agent("What is SharePoint used for?", include_mcp_data=False)
    if result and result.get('response'):
        tests_passed += 1
        print("✓ AI-only query test passed")
    else:
        print("✗ AI-only query test failed")
    
    # Final results
    print("\n=== Test Results ===")
    print(f"Passed: {tests_passed}/{total_tests}")
    print(f"Success rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)