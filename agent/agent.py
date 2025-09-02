"""
AI Agent Web Service for MCP Server Integration
Provides a FastAPI web service that orchestrates multiple MCP servers via streaming HTTP
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi.params import Query
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel
import agent_config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class QueryRequest(BaseModel):
    """Request model for querying the AI agent"""

    query: str
    stream: bool = False
    include_mcp_data: bool = True


class QueryResponse(BaseModel):
    """Response model for querying the AI agent"""

    response: str
    sources: List[str] = []
    mcp_data: Dict[str, Any] = {}

class ServerStatusResponse(BaseModel):
    """Response model for querying the status of an MCP server"""

    server_id: str
    name: str
    status: str
    health: bool
    capabilities: Dict[str, List[str]]

# Pydantic model for tool call arguments
class ToolCallArguments(BaseModel):
    """Arguments for calling a tool on an MCP server"""
    arguments: Optional[Dict[str, Any]] = None

# Pydantic model for tool call response
class ToolCallResponse(BaseModel):
    """Response model for calling a tool on an MCP server"""
    result: Any
    server: str
    tool: str

class MCPStreamingClient:
    """Client for communicating with MCP servers via streaming HTTP"""

    def __init__(self, server_config: agent_config.MCPServerConfig):
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
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
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
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    async def _send_mcp_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send an MCP JSON-RPC request and parse the response"""
        request_body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._get_next_request_id(),
        }

        url = f"{self.config.base_url}/mcp/"

        try:
            async with self.session.post(
                url, json=request_body, headers=self._get_headers()
            ) as response:

                # Extract session ID from headers if present
                if response.headers.get("Mcp-Session-Id"):
                    self.session_id = response.headers["Mcp-Session-Id"]

                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"Server returned status {response.status}: {error_text}"
                    )

                # Parse SSE response
                content = await response.text()
                return self._parse_sse_response(content)

        except aiohttp.ClientError as e:
            logger.error("MCP request failed: %s", e)
            raise RuntimeError(f"MCP request failed: {str(e)}") from e

    def _parse_sse_response(self, content: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response to extract JSON data"""
        # Split on double newlines to separate events
        events = content.split("\n\n")

        for event in events:
            if not event.strip():
                continue

            lines = event.split("\n")
            data_lines = []

            for line in lines:
                line = line.strip()
                if line.startswith("data:"):
                    # Extract data after 'data:' (with or without space)
                    if line.startswith("data: "):
                        data_lines.append(line[6:])
                    elif line.startswith("data:"):
                        data_lines.append(line[5:])

            if data_lines:
                data = "".join(data_lines)
                if data.strip():
                    try:
                        json_data = json.loads(data)

                        # Check for JSON-RPC errors
                        if "error" in json_data:
                            error = json_data["error"]
                            raise RuntimeError(
                                f"MCP error {error.get('code', 'unknown')}: "
                                f"{error.get('message', 'unknown error')}"
                            )

                        return json_data
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse JSON from SSE data: %s", data)
                        raise RuntimeError(f"Invalid JSON in response: {str(e)}") from e

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
                    "clientInfo": {"name": "mcp-agent", "version": "1.0.0"},
                    "capabilities": {},
                },
            )

            logger.info("MCP initialize response: %s", init_response)

            # Step 2: Send initialized notification (critical!)
            await self._send_mcp_notification("notifications/initialized", {})

            self.initialized = True
            logger.info("MCP session initialized successfully")

        except (RuntimeError, ValueError) as e:
            logger.error("Failed to initialize MCP session: %s", e)
            raise RuntimeError(f"MCP session initialization failed: {str(e)}") from e

    async def _send_mcp_notification(self, method: str, params: Dict[str, Any]):
        """Send an MCP notification (no response expected)"""
        request_body = {"jsonrpc": "2.0", "method": method, "params": params}

        url = f"{self.config.base_url}/mcp/"

        try:
            async with self.session.post(
                url, json=request_body, headers=self._get_headers()
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
                "tools/call", {"name": "health", "arguments": {}}
            )

            # Check if we got a successful response
            if "result" in result:
                tool_result = result["result"]

                # Handle different response formats from MCP tools
                if isinstance(tool_result, dict):
                    # Check if it's an MCP tool result with content
                    if "content" in tool_result and isinstance(
                        tool_result["content"], list
                    ):
                        # Look for successful content and no errors
                        has_content = len(tool_result["content"]) > 0
                        is_not_error = not tool_result.get("isError", False)
                        return has_content and is_not_error
                    # Check for simple success indicators
                    elif "status" in tool_result:
                        return (
                            tool_result["status"] == "ok"
                            or tool_result["status"] == "healthy"
                        )
                    else:
                        # If it's a dict but no clear success indicator,
                        # consider it healthy if no error
                        return not tool_result.get("error") and not tool_result.get(
                            "isError", False
                        )
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

        except (aiohttp.ClientError, RuntimeError) as e:
            logger.warning("Health check failed for %s: %s", self.config.name, e)
            return False

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.config.enabled:
            raise ValueError(f"Server {self.config.name} is disabled")

        if not self.initialized:
            await self._initialize_mcp_session()

        for attempt in range(self.config.retry_attempts):
            try:
                result = await self._send_mcp_request(
                    "tools/call", {"name": tool_name, "arguments": arguments or {}}
                )

                if "result" in result:
                    return result["result"]
                else:
                    raise RuntimeError(f"No result in response: {result}")

            except (RuntimeError, ValueError) as e:
                if attempt == self.config.retry_attempts - 1:
                    raise e
                logger.warning(
                    "Tool call attempt %s failed, retrying: %s", attempt + 1, e
                )
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
                    "resources/read", {"uri": resource_uri}
                )

                if "result" in result:
                    return result["result"]
                else:
                    raise RuntimeError(f"No result in response: {result}")

            except (aiohttp.ClientError, RuntimeError, ValueError) as e:
                if attempt == self.config.retry_attempts - 1:
                    raise e
                logger.warning(
                    "Resource request attempt %s failed, retrying: %s", attempt + 1, e
                )
                await asyncio.sleep(1)

    async def list_tools(self) -> List[str]:
        """List available tools on the MCP server"""
        if not self.initialized:
            await self._initialize_mcp_session()

        result = await self._send_mcp_request("tools/list", {})

        if "result" in result and "tools" in result["result"]:
            return [tool["name"] for tool in result["result"]["tools"]]
        return []

    async def list_resources(self) -> List[str]:
        """List available resources on the MCP server"""
        if not self.initialized:
            await self._initialize_mcp_session()

        result = await self._send_mcp_request("resources/list", {})

        if "result" in result and "resources" in result["result"]:
            return [resource["uri"] for resource in result["result"]["resources"]]
        return []

class MCPAgent:
    """AI Agent that orchestrates MCP servers via streaming HTTP"""

    def __init__(self, config_path: str = "mcp_agent_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, agent_config.MCPServerConfig] = {}
        self.agent_config: agent_config.AgentConfig = None
        self.gemini_model = None
        self._load_config()
        self._setup_gemini()

    def _load_config(self) -> None:
        """Load configuration from JSON file"""
        try:
            agent_config_file = Path(self.config_path)
            if not agent_config_file.exists():
                raise FileNotFoundError(f"Configuration file {self.config_path} not found")

            with open(agent_config_file, "r", encoding="utf-8") as config_file_handle:
                config_data = json.load(config_file_handle)

            # Parse server configurations
            servers_data = config_data.get("servers", [])
            if not isinstance(servers_data, list):
                raise ValueError("Expected 'servers' to be a list in config")

            for server_data in servers_data:
                try:
                    server_name = server_data.get("name")
                    if not server_name:
                        raise ValueError("Server config missing 'name' field")
                    
                    # Parse tools
                    tools = {}
                    tools_data = server_data.get("tools", {})
                    for tool_name, tool_config in tools_data.items():
                        tools[tool_name] = agent_config.ToolConfig(
                            description=tool_config.get("description", ""),
                            keywords=tool_config.get("keywords", [])
                        )
                    
                    # Parse prompts
                    prompts = {}
                    prompts_data = server_data.get("prompts", {})
                    for prompt_name, prompt_config in prompts_data.items():
                        prompts[prompt_name] = agent_config.PromptConfig(
                            description=prompt_config.get("description", ""),
                            template=prompt_config.get("template", "")
                        )
                    
                    # Parse resources
                    resources = {}
                    resources_data = server_data.get("resources", {})
                    for resource_name, resource_config in resources_data.items():
                        resources[resource_name] = agent_config.ResourceConfig(
                            description=resource_config.get("description", ""),
                            url=resource_config.get("url", ""),
                            keywords=resource_config.get("keywords", [])
                        )
                    
                    # Create server config
                    server_config = agent_config.MCPServerConfig(
                        name=server_data.get("name", ""),
                        description=server_data.get("description", ""),
                        url=server_data.get("url", ""),
                        transport=server_data.get("transport", "streamable-http"),
                        version=server_data.get("version", "1.0.0"),
                        documentation_url=server_data.get("documentation_url", ""),
                        tools=tools,
                        prompts=prompts,
                        resources=resources,
                        enabled=server_data.get("enabled", True),
                        timeout=server_data.get("timeout", 30),
                        retry_attempts=server_data.get("retry_attempts", 3),
                        health_endpoint=server_data.get("health_endpoint", "/health")
                    )
                    
                    self.servers[server_name] = server_config
                    
                except (TypeError, ValueError, KeyError) as e:
                    logger.warning("Skipping invalid server config '%s': %s", 
                                server_data.get("name", "unknown"), e)

            # Parse agent configuration
            agent_data = config_data.get("agent", {})
            
            # Parse error handling
            error_handling_data = agent_data.get("error_handling", {})
            error_handling = agent_config.ErrorHandling(
                on_error=error_handling_data.get("on_error", "fail"),
                retry=error_handling_data.get("retry", 0),
                on_tool_failure=error_handling_data.get("on_tool_failure"),
                max_retries=error_handling_data.get("max_retries"),
                retry_delay_ms=error_handling_data.get("retry_delay_ms")
            )
            
            # Parse conditions
            conditions_data = agent_data.get("conditions", {})
            conditions = agent_config.ProcessorConditions(
                only_for_tools=conditions_data.get("only_for_tools"),
                exclude_for_tools=conditions_data.get("exclude_for_tools"),
                activate_for_users=conditions_data.get("activate_for_users"),
                exclude_tools=conditions_data.get("exclude_tools")
            )
            
            # Create agent config
            self.agent_config = agent_config.AgentConfig(
                enabled=agent_data.get("enabled", True),
                order=agent_data.get("order", 1),
                allowed_tool_names=agent_data.get("allowed_tool_names", []),
                max_concurrent_requests=agent_data.get("max_concurrent_requests", 10),
                logging_level=agent_data.get("logging_level", "info"),
                trace_enabled=agent_data.get("trace_enabled", False),
                error_handling=error_handling,
                conditions=conditions
            )

            logger.info("Loaded configuration for %d MCP servers", len(self.servers))

        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to load configuration: %s", e)
            raise

    def _setup_gemini(self):
        """Setup Gemini AI model using environment variables"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")

            genai.configure(api_key=api_key)

            model_name = os.getenv(
                "GEMINI_MODEL",
                self.agent_config.model_config.get("model", "gemini-pro"),
            )
            self.gemini_model = genai.GenerativeModel(model_name)

            logger.info("Initialized Gemini model: %s", model_name)

        except (ValueError, KeyError) as e:
            logger.error("Failed to setup Gemini: %s", e)
            raise

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all enabled MCP servers"""
        async def check_server(sid, sconfig):
            async with MCPStreamingClient(sconfig) as client:
                return sid, await client.health_check()

        health_status = {}

        tasks = [
            check_server(server_id, server_config)
            for server_id, server_config in self.servers.items()
            if server_config.enabled
        ]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Health check error: %s", result)
                else:
                    server_id, is_healthy = result
                    health_status[server_id] = is_healthy

        return health_status

    async def call_server_tool(
        self, server_id: str, tool_name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a specific tool on a specific MCP server"""
        if server_id not in self.servers:
            raise ValueError(f"Server {server_id} not found in configuration")

        server_config = self.servers[server_id]
        arguments = arguments or {}

        try:
            async with MCPStreamingClient(server_config) as client:
                return await client.call_tool(tool_name, arguments)
        except Exception as e:
            logger.error("Error calling tool '%s' on server '%s': %s", tool_name, server_id, e)
            raise

    async def get_server_resource(
        self, server_id: str, resource_uri: str
    ) -> Dict[str, Any]:
        """Get a resource from a specific MCP server"""
        if server_id not in self.servers:
            raise ValueError(f"Server {server_id} not found in configuration")

        server_config = self.servers[server_id]
        try:
            async with MCPStreamingClient(server_config) as client:
                return await client.get_resource(resource_uri)
        except Exception as e:
            logger.error("Error getting resource '%s' from server '%s': %s",
                         resource_uri,
                         server_id,
                         e)
            raise

    async def generate_response(
        self, user_query: str, include_mcp_data: bool = True
    ) -> Dict[str, Any]:
        """Generate AI response using Gemini and optionally enhance with MCP data"""
        try:
            # Create context-aware prompt
            available_capabilities = self._format_server_capabilities()

            system_context = f"""
{self.agent_config.system_prompt}

Available MCP servers and their capabilities:
{available_capabilities}

Instructions:
1. Analyze the user's query to determine if any MCP server tools or resources are needed.
2. If MCP data is needed and available, incorporate it into your response.
3. Provide helpful, accurate responses based on available information.
4. If you cannot access certain data, explain why and suggest alternatives.
"""

            # Generate initial response
            full_prompt = f"{system_context}\n\nUser Query: {user_query}\n\nResponse:"

            response_text = await self._generate_ai_response(full_prompt)

            # Enhance with MCP data if requested and relevant
            mcp_data = {}
            sources = []

            if include_mcp_data:
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

            return {"response": response_text, "sources": sources, "mcp_data": mcp_data}

        except (RuntimeError, ValueError) as e:
            logger.error(
                "[%s.generate_response] Error generating response for query '%s': %s",
                __name__,
                user_query,
                e,
                exc_info=True,
            )
            # Detect common non-serializable object issues (like 'slice')
            error_str = str(e)
            if "slice(" in error_str:
                user_message = (
                    "An internal error occurred while processing your request. "
                    "It appears the server returned an unexpected object (like a Python 'slice'). "
                    "This is likely a backend bug. Please contact support with your query: '"
                    f"{user_query}'; Error detail: {error_str}"
                )
            else:
                user_message = (
                    f"I encountered an error processing your request: {error_str}"
                )
            return {
                "response": user_message,
                "sources": [],
                "mcp_data": {"error": error_str},
            }

    async def _generate_ai_response(self, prompt: str) -> str:
        """Generate AI response using Gemini"""
        try:
            model_config = self.agent_config.model_config
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=model_config.get("temperature", 0.7),
                    max_output_tokens=model_config.get("max_tokens", 4096),
                ),
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
                tools = server_config.capabilities.get("tools", [])
                resources = server_config.capabilities.get("resources", [])
                tools_str = ", ".join(sorted(tools)) if tools else "None"
                resources_str = ", ".join(sorted(resources)) if resources else "None"
                capabilities.append(f"- {server_config.name} ({server_id}):")
                capabilities.append(f"  Tools: {tools_str}")
                capabilities.append(f"  Resources: {resources_str}")
        return "\n".join(capabilities)

    def _resource_relevant_to_query(
        self, server_id: str, resource_name: str, user_query: str) -> bool:
        """Check if the user query matches any keywords configured for the resource."""
        server_config = self.servers.get(server_id)
        if not server_config:
            return False

        # Access resources dictionary from server config
        resources_config = server_config.get("resources", {})
        resource_config = resources_config.get(resource_name, {})
        keywords = resource_config.get("keywords", [])

        query_lower = user_query.lower()
        return any(keyword.lower() in query_lower for keyword in keywords)

    def _tool_relevant_to_query(self, server_id: str, tool_name: str, user_query: str) -> bool:
        """Check if the user query matches any keywords configured for the tool."""
        server_config = self.servers.get(server_id)
        if not server_config:
            return False

        # Access tools dictionary from server config
        tools_config = server_config.get("tools", {})
        tool_config = tools_config.get(tool_name, {})
        keywords = tool_config.get("keywords", [])

        query_lower = user_query.lower()
        return any(keyword.lower() in query_lower for keyword in keywords)

    async def _fetch_relevant_mcp_data(self, user_query: str) -> tuple[Dict[str, Any], List[str]]:
        mcp_data = {}
        sources = []

        health_status = await self.health_check_all()

        for server_id, server_config in self.servers.items():
            if not server_config.enabled or not health_status.get(server_id, False):
                continue

            # Example: check if any tool keywords match user query
            for tool_name in server_config.capabilities.get("tools", []):
                if self._tool_relevant_to_query(server_id, tool_name, user_query):
                    try:
                        result = await self.call_server_tool(server_id, tool_name)
                        mcp_data.setdefault(server_id, {})[tool_name] = result
                        sources.append(f"{server_config.name} - {tool_name}")
                    except (RuntimeError, ValueError, aiohttp.ClientError) as e:
                        logger.warning("Failed to fetch %s from %s: %s", tool_name, server_id, e)

            # Similarly for resources if applicable
            for resource_uri in server_config.capabilities.get("resources", []):
                if self._tool_relevant_to_query(server_id, resource_uri, user_query):
                    try:
                        result = await self.get_server_resource(server_id, resource_uri)
                        mcp_data.setdefault(server_id, {})[resource_uri] = result
                        sources.append(f"{server_config.name} - {resource_uri}")
                    except (RuntimeError, ValueError, aiohttp.ClientError) as e:
                        logger.warning("Failed to fetch %s from %s: %s", resource_uri, server_id, e)

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
        docs_url=(
            "/docs"
            if agent.agent_config.web_service.get("docs_enabled", True)
            else None
        ),
    )

    # Add CORS middleware
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=agent.agent_config.web_service.get("cors_origins", ["*"]),
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
                "docs": "/docs",
            },
        }

    @fastapi_app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            server_health = await agent.health_check_all()
            overall_healthy = all(server_health.values()) if server_health else False

            return {
                "status": "healthy" if overall_healthy else "degraded",
                "servers": server_health,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
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
                servers.append(
                    ServerStatusResponse(
                        server_id=server_id,
                        name=server_config.name,
                        status="enabled" if server_config.enabled else "disabled",
                        health=health_status.get(server_id, False),
                        capabilities=server_config.capabilities,
                        url=server_config.url,            # Added URL
                        version=server_config.version     # Added version
                    )
                )

            return servers
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @fastapi_app.post("/query", response_model=QueryResponse)
    async def query_agent(request: QueryRequest):
        """Send a query to the AI agent"""
        try:
            # Basic sanitization: strip whitespace and limit length
            sanitized_query = request.query.strip()
            if len(sanitized_query) == 0:
                raise HTTPException(status_code=400, detail="Query cannot be empty")
            if len(sanitized_query) > 1000:
                raise HTTPException(status_code=400, detail="Query too long")

            result = await agent.generate_response(
                sanitized_query, include_mcp_data=request.include_mcp_data
            )

            return QueryResponse(**result)

        except Exception as e:
            logger.error(
                "[%s.query_agent] Query error for query '%s': %s",
                __name__,
                request.query,
                e,
                exc_info=True,
            )
            error_str = str(e)
            if "slice(" in error_str:
                user_message = (
                    "An internal error occurred while processing your request. "
                    "It appears the server returned an unexpected object (like a Python 'slice'). "
                    "This is likely a backend bug. Please contact support with your query: '"
                    f"{request.query}'; Error detail: {error_str}"
                )
            else:
                user_message = (
                    f"I encountered an error processing your request: {error_str}"
                )
            raise HTTPException(status_code=500, detail=user_message) from e

    @fastapi_app.post("/servers/{server_id}/tools/{tool_name}", response_model=ToolCallResponse)
    async def call_server_tool(server_id: str, tool_name: str, arguments: ToolCallArguments):
        """Directly call a tool on a specific MCP server"""
        try:
            args_dict = arguments.arguments or {}
            result = await agent.call_server_tool(server_id, tool_name, args_dict)
            return ToolCallResponse(result=result, server=server_id, tool=tool_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @fastapi_app.get("/servers/{server_id}/resources")
    async def get_server_resource(server_id: str, uri: str = Query(...)):
        """Get a resource from a specific MCP server"""
        try:
            result = await agent.get_server_resource(server_id, uri)
            return {"result": result, "server": server_id, "resource_uri": uri}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

# Create the app instance
app: FastAPI = create_app()

if __name__ == "__main__":
    # Load agent config to get web service settings
    with open("mcp_agent_config.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    web_config = config.get("agent", {}).get("web_service", {})

    uvicorn.run(
        "agent:app",
        host=web_config.get("host", "127.0.0.1"),
        port=web_config.get("port", 8080),
        ssl_certfile="certs/cert.pem",
        ssl_keyfile="certs/key.pem",
        reload=False,
        log_level="info",
    )
