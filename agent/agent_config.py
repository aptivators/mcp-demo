from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ToolConfig:
    """Configuration for an MCP tool"""
    description: str
    keywords: List[str]

@dataclass
class PromptConfig:
    """Configuration for an MCP prompt"""
    description: str
    template: str

@dataclass
class ResourceConfig:
    """Configuration for an MCP resource"""
    description: str
    url: str
    keywords: List[str]

@dataclass
class ErrorHandling:
    """Error handling configuration"""
    on_error: str = "fail"
    retry: int = 0
    on_tool_failure: Optional[str] = None
    max_retries: Optional[int] = None
    retry_delay_ms: Optional[int] = None

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "info"
    trace: bool = False

@dataclass
class ProcessorConditions:
    """Conditions for processors"""
    only_for_tools: Optional[List[str]] = None
    exclude_for_tools: Optional[List[str]] = None
    activate_for_users: Optional[List[str]] = None
    exclude_tools: Optional[List[str]] = None

@dataclass
class ProcessorConfig:
    """Base configuration for processors"""
    description: str
    type: str
    order: int
    enabled: bool
    error_handling: ErrorHandling
    logging: LoggingConfig
    conditions: ProcessorConditions

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    description: str
    url: str  # Changed from base_url to match your config
    transport: str
    version: str
    documentation_url: str
    tools: Dict[str, ToolConfig]
    prompts: Dict[str, PromptConfig]
    resources: Dict[str, ResourceConfig]
    
    # Add these fields with defaults for backward compatibility
    enabled: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    health_endpoint: str = "/health"
    
    @property
    def base_url(self) -> str:
        """Compatibility property for base_url"""
        return self.url
    
    @property
    def capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities in the format expected by existing code"""
        return {
            "tools": list(self.tools.keys()),
            "resources": list(self.resources.keys())
        }

@dataclass
class AgentConfig:
    """Configuration for the AI agent"""
    enabled: bool
    order: int
    allowed_tool_names: List[str]
    max_concurrent_requests: int
    logging_level: str
    trace_enabled: bool
    error_handling: ErrorHandling
    conditions: ProcessorConditions
    
    # Add these fields with defaults for backward compatibility
    name: str = "MCP Agent"
    description: str = "AI Agent for MCP server integration"
    model_config: Dict[str, Any] = None
    system_prompt: str = "You are an AI assistant that helps users by coordinating multiple MCP servers."
    web_service: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.model_config is None:
            self.model_config = {
                "model": "gemini-pro",
                "temperature": 0.7,
                "max_tokens": 4096
            }
        if self.web_service is None:
            self.web_service = {
                "host": "127.0.0.1",
                "port": 8080,
                "docs_enabled": True,
                "cors_origins": ["*"]
            }

@dataclass
class MCPAgentConfiguration:
    """Complete MCP Agent configuration"""
    servers: List[MCPServerConfig]
    preprocessors: Dict[str, ProcessorConfig]
    postprocessors: Dict[str, ProcessorConfig]
    agent: AgentConfig