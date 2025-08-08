"""
Test client for the MCP Agent Web Service
Demonstrates how to interact with the AI agent via HTTP API
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

class MCPAgentClient:
    """Client for interacting with the MCP Agent Web Service"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the agent service"""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()
    
    async def list_servers(self) -> Dict[str, Any]:
        """List all configured MCP servers"""
        async with self.session.get(f"{self.base_url}/servers") as response:
            return await response.json()
    
    async def query(self, query_text: str, include_mcp_data: bool = True) -> Dict[str, Any]:
        """Send a query to the AI agent"""
        payload = {
            "query": query_text,
            "include_mcp_data": include_mcp_data
        }
        
        async with self.session.post(
            f"{self.base_url}/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            return await response.json()
    
    async def call_server_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Directly call a tool on a specific MCP server"""
        url = f"{self.base_url}/servers/{server_id}/tools/{tool_name}"
        
        async with self.session.post(
            url,
            json=arguments or {},
            headers={"Content-Type": "application/json"}
        ) as response:
            return await response.json()

async def test_agent_service():
    """Test the MCP Agent Web Service"""
    print("🧪 Testing MCP Agent Web Service")
    print("=" * 40)
    
    async with MCPAgentClient() as client:
        try:
            # Test health check
            print("1. Health Check...")
            health = await client.health_check()
            print(f"   Status: {health.get('status', 'unknown')}")
            print(f"   Servers: {health.get('servers', {})}")
            
            # Test server listing
            print("\n2. Server List...")
            servers = await client.list_servers()
            for server in servers:
                print(f"   - {server['name']} ({server['server_id']}): {server['status']}")
            
            # Test queries
            test_queries = [
                "What Medicare datasets are available?",
                "Can you list the Medicare documents?",
                "Tell me about nursing home data",
                "What is the structure of the Medicare datasets?"
            ]
            
            print("\n3. Testing Queries...")
            for i, query in enumerate(test_queries, 1):
                print(f"\n   Query {i}: {query}")
                try:
                    result = await client.query(query)
                    print(f"   Response: {result['response'][:200]}{'...' if len(result['response']) > 200 else ''}")
                    if result.get('sources'):
                        print(f"   Sources: {', '.join(result['sources'])}")
                    if result.get('mcp_data'):
                        print(f"   MCP Data Keys: {list(result['mcp_data'].keys())}")
                except Exception as e:
                    print(f"   Error: {e}")
            
            # Test direct tool call
            print("\n4. Testing Direct Tool Call...")
            try:
                tool_result = await client.call_server_tool(
                    "medicare_server", 
                    "list_medicare_documents"
                )
                print(f"   Tool Result: {tool_result}")
            except Exception as e:
                print(f"   Tool Call Error: {e}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    print("\n✅ All tests completed!")
    return True

async def interactive_client():
    """Interactive client for testing the agent"""
    print("🤖 MCP Agent Interactive Client")
    print("Type 'quit' to exit, 'health' for health check, 'servers' for server list")
    print("=" * 60)
    
    async with MCPAgentClient() as client:
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'health':
                    health = await client.health_check()
                    print(f"🏥 Health: {json.dumps(health, indent=2)}")
                    continue
                
                if user_input.lower() == 'servers':
                    servers = await client.list_servers()
                    print(f"🖥️  Servers: {json.dumps(servers, indent=2)}")
                    continue
                
                if not user_input:
                    continue
                
                print("🤔 Processing...")
                result = await client.query(user_input)
                
                print(f"🤖 Agent: {result['response']}")
                
                if result.get('sources'):
                    print(f"📚 Sources: {', '.join(result['sources'])}")
                
                if result.get('mcp_data'):
                    print(f"📊 MCP Data: {json.dumps(result['mcp_data'], indent=2)}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run automated tests
        asyncio.run(test_agent_service())
    else:
        # Run interactive client
        asyncio.run(interactive_client())
