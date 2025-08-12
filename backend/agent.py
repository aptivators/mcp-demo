"""
AI Agent Web Service for MCP Server Integration
Provides a FastAPI web service that orchestrates multiple MCP servers via streaming HTTP
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class QueryRequest(BaseModel):
    query: str
    stream: bool = False
    include_mcp_data: bool = True

class QueryResponse(BaseModel):
    response: str
    sources: List[str] = []
    mcp_data: Dict[str, Any] = {}

class ServerStatusResponse(BaseModel):
    server_id: str
    name: str
    status: str
    health: bool
    capabilities: Dict[str, List[str]]

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    description: str
    base_url: str
    transport: str
    enabled: bool
    timeout: int
    retry_attempts: int
    health_endpoint: str
    capabilities: Dict[str, List[str]]

@dataclass
class AgentConfig:
    """Configuration for the AI agent"""
    name: str
    description: str
    model_config: Dict[str, Any]
    system_prompt: str
    web_service: Dict[str, Any]

class MCPStreamingClient:
    """Client for communicating with MCP servers via streaming HTTP"""
    
    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
        self.request_id = 0
        self.initialized = False
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream'
            }
        )
        
        # Initialize MCP session
        await self._initialize_mcp_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_next_request_id(self) -> int:
        """Get the next request ID"""
        self.request_id += 1
        return self.request_id
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers including session ID if available"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        if self.session_id:
            headers['Mcp-Session-Id'] = self.session_id
        return headers
    
    async def _send_mcp_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send an MCP JSON-RPC request and parse the response"""
        request_body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._get_next_request_id()
        }
        
        url = f"{self.config.base_url}/mcp/"
        
        try:
            async with self.session.post(
                url, 
                json=request_body, 
                headers=self._get_headers()
            ) as response:
                
                # Extract session ID from headers if present
                if response.headers.get('Mcp-Session-Id'):
                    self.session_id = response.headers['Mcp-Session-Id']
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Server returned status {response.status}: {error_text}")
                
                # Parse SSE response
                content = await response.text()
                return self._parse_sse_response(content)
                
        except aiohttp.ClientError as e:
            logger.error("MCP request failed: %s", e)
            raise RuntimeError(f"MCP request failed: {str(e)}")
    
    def _parse_sse_response(self, content: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response to extract JSON data"""
        # Split on double newlines to separate events
        events = content.split('\n\n')
        
        for event in events:
            if not event.strip():
                continue
                
            lines = event.split('\n')
            data_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('data:'):
                    # Extract data after 'data:' (with or without space)
                    if line.startswith('data: '):
                        data_lines.append(line[6:])
                    elif line.startswith('data:'):
                        data_lines.append(line[5:])
            
            if data_lines:
                data = ''.join(data_lines)
                if data.strip():
                    try:
                        json_data = json.loads(data)
                        
                        # Check for JSON-RPC errors
                        if 'error' in json_data:
                            error = json_data['error']
                            raise RuntimeError(f"MCP error {error.get('code', 'unknown')}: {error.get('message', 'unknown error')}")
                        
                        return json_data
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse JSON from SSE data: %s", data)
                        raise RuntimeError(f"Invalid JSON in response: {str(e)}")
        
        raise RuntimeError("No valid JSON data found in SSE response")
    
    async def _initialize_mcp_session(self):
        """Initialize the MCP session with proper handshake"""
        if self.initialized:
            return
        
        try:
            # Step 1: Send initialize request
            logger.info("Initializing MCP session with %s", self.config.name)
            
            init_response = await self._send_mcp_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {
                        "name": "mcp-agent",
                        "version": "1.0.0"
                    },
                    "capabilities": {}
                }
            )
            
            logger.info("MCP initialize response: %s", init_response)
            
            # Step 2: Send initialized notification (critical!)
            await self._send_mcp_notification("notifications/initialized", {})
            
            self.initialized = True
            logger.info("MCP session initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize MCP session: %s", e)
            raise RuntimeError(f"MCP session initialization failed: {str(e)}")
    
    async def _send_mcp_notification(self, method: str, params: Dict[str, Any]):
        """Send an MCP notification (no response expected)"""
        request_body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        url = f"{self.config.base_url}/mcp/"
        
        try:
            async with self.session.post(
                url,
                json=request_body,
                headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.warning("Notification failed: %s", error_text)
                    
        except aiohttp.ClientError as e:
            logger.warning("Failed to send notification: %s", e)
    
    async def health_check(self) -> bool:
        """Check if the MCP server is healthy using the health tool"""
        if not self.config.enabled:
            return False
            
        try:
            if not self.initialized:
                await self._initialize_mcp_session()
            
            # Call the health tool via MCP protocol
            result = await self._send_mcp_request(
                "tools/call",
                {
                    "name": "health",
                    "arguments": {}
                }
            )
            
            # Check if we got a successful response
            if 'result' in result:
                tool_result = result['result']
                
                # Handle different response formats from MCP tools
                if isinstance(tool_result, dict):
                    # Check if it's an MCP tool result with content
                    if 'content' in tool_result and isinstance(tool_result['content'], list):
                        # Look for successful content and no errors
                        has_content = len(tool_result['content']) > 0
                        is_not_error = not tool_result.get('isError', False)
                        return has_content and is_not_error
                    # Check for simple success indicators
                    elif 'status' in tool_result:
                        return tool_result['status'] == 'ok' or tool_result['status'] == 'healthy'
                    else:
                        # If it's a dict but no clear success indicator, consider it healthy if no error
                        return not tool_result.get('error') and not tool_result.get('isError', False)
                elif isinstance(tool_result, str):
                    # String responses from health tool - consider non-empty as healthy
                    return len(tool_result.strip()) > 0
                elif isinstance(tool_result, bool):
                    # Direct boolean response
                    return tool_result
                else:
                    # Any other response type, consider it healthy if we got here without exception
                    return True
            
            return False
            
        except Exception as e:
            logger.warning("Health check failed for %s: %s", self.config.name, e)
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.config.enabled:
            raise ValueError(f"Server {self.config.name} is disabled")
        
        if not self.initialized:
            await self._initialize_mcp_session()
        
        for attempt in range(self.config.retry_attempts):
            try:
                result = await self._send_mcp_request(
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": arguments or {}
                    }
                )
                
                if 'result' in result:
                    return result['result']
                else:
                    raise RuntimeError(f"No result in response: {result}")
                    
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    raise e
                logger.warning("Tool call attempt %s failed, retrying: %s", attempt + 1, e)
                await asyncio.sleep(1)
    
    async def get_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Get a resource from the MCP server"""
        if not self.config.enabled:
            raise ValueError(f"Server {self.config.name} is disabled")
        
        if not self.initialized:
            await self._initialize_mcp_session()
        
        for attempt in range(self.config.retry_attempts):
            try:
                result = await self._send_mcp_request(
                    "resources/read",
                    {
                        "uri": resource_uri
                    }
                )
                
                if 'result' in result:
                    return result['result']
                else:
                    raise RuntimeError(f"No result in response: {result}")
                    
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    raise e
                logger.warning("Resource request attempt %s failed, retrying: %s", attempt + 1, e)
                await asyncio.sleep(1)
    
    async def list_tools(self) -> List[str]:
        """List available tools on the MCP server"""
        if not self.initialized:
            await self._initialize_mcp_session()
        
        result = await self._send_mcp_request("tools/list", {})
        
        if 'result' in result and 'tools' in result['result']:
            return [tool['name'] for tool in result['result']['tools']]
        return []
    
    async def list_resources(self) -> List[str]:
        """List available resources on the MCP server"""
        if not self.initialized:
            await self._initialize_mcp_session()
        
        result = await self._send_mcp_request("resources/list", {})
        
        if 'result' in result and 'resources' in result['result']:
            return [resource['uri'] for resource in result['result']['resources']]
        return []

class MCPAgent:
    """AI Agent that orchestrates MCP servers via streaming HTTP"""
    
    def __init__(self, config_path: str = "mcp_agent_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServerConfig] = {}
        self.agent_config: AgentConfig = None
        self.gemini_model = None
        self._load_config()
        self._setup_gemini()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            agent_config_file = Path(self.config_path)
            if not agent_config_file.exists():
                raise FileNotFoundError(f"Configuration file {self.config_path} not found")
            
            with open(agent_config_file, 'r', encoding='utf-8') as config_file_handle:
                config_data = json.load(config_file_handle)
            
            # Load server configurations
            for server_id, server_data in config_data.get('servers', {}).items():
                self.servers[server_id] = MCPServerConfig(**server_data)
            
            # Load agent configuration
            agent_data = config_data.get('agent', {})
            self.agent_config = AgentConfig(**agent_data)
            
            logger.info("Loaded configuration for %s MCP servers", len(self.servers))
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load configuration: %s", e)
            raise
    
    def _setup_gemini(self):
        """Setup Gemini AI model using environment variables"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            
            model_name = os.getenv('GEMINI_MODEL', self.agent_config.model_config.get('model', 'gemini-pro'))
            self.gemini_model = genai.GenerativeModel(model_name)
            
            logger.info("Initialized Gemini model: %s", model_name)
            
        except (ValueError, KeyError) as e:
            logger.error("Failed to setup Gemini: %s", e)
            raise
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all enabled MCP servers"""
        health_status = {}
        
        tasks = []
        for server_id, server_config in self.servers.items():
            if server_config.enabled:
                async def check_server(sid, sconfig):
                    async with MCPStreamingClient(sconfig) as client:
                        return sid, await client.health_check()
                tasks.append(check_server(server_id, server_config))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Health check error: %s", result)
                else:
                    server_id, is_healthy = result
                    health_status[server_id] = is_healthy
        
        return health_status
    
    async def call_server_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific tool on a specific MCP server"""
        if server_id not in self.servers:
            raise ValueError(f"Server {server_id} not found in configuration")
        
        server_config = self.servers[server_id]
        async with MCPStreamingClient(server_config) as client:
            return await client.call_tool(tool_name, arguments)
    
    async def get_server_resource(self, server_id: str, resource_uri: str) -> Dict[str, Any]:
        """Get a resource from a specific MCP server"""
        if server_id not in self.servers:
            raise ValueError(f"Server {server_id} not found in configuration")
        
        server_config = self.servers[server_id]
        async with MCPStreamingClient(server_config) as client:
            return await client.get_resource(resource_uri)
    
    async def generate_response(self, user_query: str, include_mcp_data: bool = True) -> Dict[str, Any]:
        """Generate AI response using Gemini and optionally enhance with MCP data"""
        try:
            # Create context-aware prompt
            available_capabilities = self._format_server_capabilities()
            
            system_context = f"""
{self.agent_config.system_prompt}

Available MCP servers and their capabilities:
{available_capabilities}

Instructions:
1. Analyze the user's query to determine if any MCP server tools or resources are needed
2. If MCP data is needed and available, incorporate it into your response
3. Provide helpful, accurate responses based on available information
4. If you cannot access certain data, explain why and suggest alternatives
"""
            
            # Generate initial response
            full_prompt = f"{system_context}\n\nUser Query: {user_query}\n\nResponse:"
            
            response_text = await self._generate_ai_response(full_prompt)
            
            # Enhance with MCP data if requested and relevant
            mcp_data = {}
            sources = []
            
            if include_mcp_data and self._should_fetch_mcp_data(user_query):
                mcp_data, sources = await self._fetch_relevant_mcp_data(user_query)
                if mcp_data:
                    enhanced_prompt = f"""
{system_context}

Additional context from MCP servers:
{json.dumps(mcp_data, indent=2)}

User Query: {user_query}

Please provide a comprehensive response incorporating the MCP data above:
"""
                    response_text = await self._generate_ai_response(enhanced_prompt)
            
            return {
                "response": response_text,
                "sources": sources,
                "mcp_data": mcp_data
            }
            
        except (RuntimeError, ValueError) as e:
            logger.error("[%s.generate_response] Error generating response for query '%s': %s", __name__, user_query, e, exc_info=True)
            # Detect common non-serializable object issues (like 'slice')
            error_str = str(e)
            if 'slice(' in error_str:
                user_message = (
                    "An internal error occurred while processing your request. "
                    "It appears the server returned an unexpected object (like a Python 'slice'). "
                    "This is likely a backend bug. Please contact support with your query: '"
                    f"{user_query}'; Error detail: {error_str}"
                )
            else:
                user_message = f"I encountered an error processing your request: {error_str}"
            return {
                "response": user_message,
                "sources": [],
                "mcp_data": {"error": error_str}
            }
    
    async def _generate_ai_response(self, prompt: str) -> str:
        """Generate AI response using Gemini"""
        try:
            model_config = self.agent_config.model_config
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=model_config.get('temperature', 0.7),
                    max_output_tokens=model_config.get('max_tokens', 4096)
                )
            )
            return response.text
        except (ValueError, RuntimeError) as e:
            logger.error("Error generating AI response: %s", e)
            raise
    
    def _format_server_capabilities(self) -> str:
        """Format server capabilities for the prompt"""
        capabilities = []
        for server_id, server_config in self.servers.items():
            if server_config.enabled:
                tools = ', '.join(server_config.capabilities.get('tools', []))
                resources = ', '.join(server_config.capabilities.get('resources', []))
                capabilities.append(f"- {server_config.name} ({server_id}):")
                capabilities.append(f"  Tools: {tools}")
                capabilities.append(f"  Resources: {resources}")
        return '\n'.join(capabilities)
    
    def _should_fetch_mcp_data(self, user_query: str) -> bool:
        """Determine if we should fetch MCP data based on the query"""
        # Keywords that suggest Medicare or healthcare data is needed
        medicare_keywords = [
            'medicare', 'dataset', 'nursing home', 'deficit', 'document', 'data',
            'healthcare', 'medical', 'cms', 'hospital', 'patient', 'provider'
        ]
        query_lower = user_query.lower()
        return any(keyword in query_lower for keyword in medicare_keywords)
    
    async def _fetch_relevant_mcp_data(self, user_query: str) -> tuple[Dict[str, Any], List[str]]:
        """Fetch relevant data from MCP servers based on the query"""
        mcp_data = {}
        sources = []
        
        try:
            # Check if Medicare server is available
            health_status = await self.health_check_all()
            
            if 'medicare_server' in health_status and health_status['medicare_server']:
                try:
                    # Fetch relevant Medicare data based on query context
                    if any(word in user_query.lower() for word in ['document', 'documents']):
                        docs = await self.call_server_tool('medicare_server', 'list_medicare_documents')
                        mcp_data['available_documents'] = docs
                        sources.append('Medicare Documents List')
                    
                    if any(word in user_query.lower() for word in ['data', 'dataset', 'nursing', 'home']):
                        row_count = await self.call_server_tool(
                            'medicare_server', 
                            'get_medicare_dataset_row_count', 
                            {'dataset_name': 'nursing_home_dataset'}
                        )
                        columns = await self.call_server_tool(
                            'medicare_server',
                            'get_medicare_dataset_columns',
                            {'dataset_name': 'nursing_home_dataset'}
                        )
                        # Fetch actual data rows (top 10)
                        rows = await self.call_server_tool(
                            'medicare_server',
                            'get_medicare_dataset_rows',
                            {'dataset_name': 'nursing_home_dataset', 'limit': 10, 'offset': 0}
                        )
                        logger.debug(f"Fetched columns: {columns}")
                        logger.debug(f"Fetched rows: {rows}")
                        # Robustly extract columns
                        if isinstance(columns, dict):
                            if 'structuredContent' in columns and 'result' in columns['structuredContent']:
                                columns_list = columns['structuredContent']['result']
                            elif 'result' in columns and isinstance(columns['result'], list):
                                columns_list = columns['result']
                            else:
                                columns_list = []
                        else:
                            columns_list = columns if isinstance(columns, list) else []
                        # Robustly extract rows
                        if isinstance(rows, dict):
                            if 'structuredContent' in rows and 'result' in rows['structuredContent']:
                                rows_list = rows['structuredContent']['result']
                            elif 'result' in rows and isinstance(rows['result'], list):
                                rows_list = rows['result']
                            else:
                                rows_list = []
                        else:
                            rows_list = rows if isinstance(rows, list) else []
                        mcp_data['nursing_home_dataset'] = {
                            'row_count': row_count,
                            'columns': columns_list[:10],
                            'rows': rows_list
                        }
                        sources.append('Medicare Nursing Home Dataset')
                    
                    # Add health status for transparency
                    mcp_data['server_status'] = 'healthy'
                    
                except (RuntimeError, ValueError) as e:
                    logger.warning("Could not fetch Medicare data: %s", e)
                    mcp_data['server_status'] = f'error: {str(e)}'
            else:
                mcp_data['server_status'] = 'unavailable'
        
        except (RuntimeError, ValueError) as e:
            logger.error("Error fetching MCP data: %s", e)
            mcp_data['error'] = str(e)
        
        return mcp_data, sources

# Create FastAPI application
def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    # Initialize the MCP Agent
    agent = MCPAgent()
    
    fastapi_app = FastAPI(
        title=agent.agent_config.name,
        description=agent.agent_config.description,
        version="1.0.0",
        docs_url="/docs" if agent.agent_config.web_service.get('docs_enabled', True) else None
    )
    
    # Add CORS middleware
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=agent.agent_config.web_service.get('cors_origins', ['*']),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @fastapi_app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "name": agent.agent_config.name,
            "description": agent.agent_config.description,
            "version": "1.0.0",
            "servers": list(agent.servers.keys()),
            "endpoints": {
                "query": "/query",
                "health": "/health",
                "servers": "/servers",
                "docs": "/docs"
            }
        }
    
    @fastapi_app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            server_health = await agent.health_check_all()
            overall_healthy = any(server_health.values()) if server_health else False
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "servers": server_health,
                "timestamp": asyncio.get_event_loop().time()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    @fastapi_app.get("/servers", response_model=List[ServerStatusResponse])
    async def list_servers():
        """List all configured MCP servers and their status"""
        try:
            health_status = await agent.health_check_all()
            
            servers = []
            for server_id, server_config in agent.servers.items():
                servers.append(ServerStatusResponse(
                    server_id=server_id,
                    name=server_config.name,
                    status="enabled" if server_config.enabled else "disabled",
                    health=health_status.get(server_id, False),
                    capabilities=server_config.capabilities
                ))
            
            return servers
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    @fastapi_app.post("/query", response_model=QueryResponse)
    async def query_agent(request: QueryRequest):
        """Send a query to the AI agent"""
        try:
            result = await agent.generate_response(
                request.query, 
                include_mcp_data=request.include_mcp_data
            )
            
            return QueryResponse(**result)
            
        except Exception as e:
            logger.error("[%s.query_agent] Query error for query '%s': %s", __name__, request.query, e, exc_info=True)
            # Detect common non-serializable object issues (like 'slice')
            error_str = str(e)
            if 'slice(' in error_str:
                user_message = (
                    "An internal error occurred while processing your request. "
                    "It appears the server returned an unexpected object (like a Python 'slice'). "
                    "This is likely a backend bug. Please contact support with your query: '"
                    f"{request.query}'; Error detail: {error_str}"
                )
            else:
                user_message = f"I encountered an error processing your request: {error_str}"
            raise HTTPException(status_code=500, detail=user_message) from e
    
    @fastapi_app.post("/servers/{server_id}/tools/{tool_name}")
    async def call_server_tool(server_id: str, tool_name: str, arguments: Dict[str, Any] = None):
        """Directly call a tool on a specific MCP server"""
        try:
            result = await agent.call_server_tool(server_id, tool_name, arguments)
            return {"result": result, "server": server_id, "tool": tool_name}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    @fastapi_app.get("/servers/{server_id}/resources")
    async def get_server_resource(server_id: str, uri: str):
        """Get a resource from a specific MCP server"""
        try:
            result = await agent.get_server_resource(server_id, uri)
            return {"result": result, "server": server_id, "resource_uri": uri}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    return fastapi_app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    # Load agent config to get web service settings
    with open("mcp_agent_config.json", 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
    
    web_config = config.get('agent', {}).get('web_service', {})
    
    uvicorn.run(
        "agent:app",
        host=web_config.get('host', '127.0.0.1'),
        port=web_config.get('port', 8080),
        ssl_certfile="certs/cert.pem",
        ssl_keyfile="certs/key.pem",
        reload=True,
        log_level="info"
    )
