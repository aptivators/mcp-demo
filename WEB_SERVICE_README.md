# MCP Agent Web Service

An AI agent web service that orchestrates multiple MCP (Model Context Protocol) servers via streaming HTTP. This service provides a REST API for querying AI models enhanced with data from configured MCP servers.

## Features

- **Extensible Configuration**: Add new MCP servers via JSON configuration
- **Streaming HTTP Support**: Communicates with MCP servers using streaming HTTP protocols
- **AI Integration**: Uses Google Gemini models for natural language processing
- **REST API**: Full REST API with automatic documentation
- **Health Monitoring**: Built-in health checks for all MCP servers
- **CORS Support**: Configurable CORS for web frontend integration

## Architecture

```
Web Clients → FastAPI Agent Service → MCP Servers (via HTTP)
                      ↓
                 Gemini AI Model
```

## Quick Start

### 1. Environment Setup

Copy the environment template and configure your API keys:

```powershell
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

Required environment variables:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `GEMINI_MODEL`: Model name (optional, defaults to gemini-pro)

### 2. Install Dependencies

```powershell
# Using uv (recommended)
uv install

# Or using pip
pip install -r requirements.txt
```

### 3. Start the Services

```powershell
# Start both Medicare server and Agent service
.\start_web_service.ps1

# Or start with custom ports
.\start_web_service.ps1 -AgentPort 8080 -ServerPort 8000

# Skip Medicare server startup if already running
.\start_web_service.ps1 -SkipServerStart
```

### 4. Access the Service

- **API Documentation**: http://127.0.0.1:8080/docs
- **Health Check**: http://127.0.0.1:8080/health
- **Service Info**: http://127.0.0.1:8080/

## API Endpoints

### Core Endpoints

- `GET /` - Service information
- `GET /health` - Health check for all MCP servers
- `GET /servers` - List configured MCP servers
- `POST /query` - Query the AI agent

### MCP Server Integration

- `POST /servers/{server_id}/tools/{tool_name}` - Call MCP server tools directly
- `GET /servers/{server_id}/resources?uri={resource_uri}` - Get MCP server resources

## Configuration

The service uses `mcp_agent_config.json` for configuration:

```json
{
  "servers": {
    "medicare_server": {
      "name": "Medicare MCP Server",
      "description": "MCP server for Medicare data exploration",
      "base_url": "http://127.0.0.1:8000",
      "transport": "streaming-http",
      "enabled": true,
      "timeout": 30,
      "retry_attempts": 3,
      "health_endpoint": "/health",
      "capabilities": {
        "tools": ["health", "list_medicare_documents", ...],
        "resources": ["medicare://datasets", ...]
      }
    }
  },
  "agent": {
    "name": "MCP Agent Web Service",
    "model_config": {
      "provider": "gemini",
      "model": "gemini-1.5-flash-latest",
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "system_prompt": "You are an AI assistant...",
    "web_service": {
      "host": "0.0.0.0",
      "port": 8080,
      "cors_origins": ["*"],
      "docs_enabled": true
    }
  }
}
```

### Adding New MCP Servers

To add a new MCP server:

1. Add server configuration to `mcp_agent_config.json`:

```json
{
  "servers": {
    "your_server": {
      "name": "Your MCP Server",
      "base_url": "http://your-server:port",
      "transport": "streaming-http",
      "enabled": true,
      "timeout": 30,
      "retry_attempts": 3,
      "health_endpoint": "/health",
      "capabilities": {
        "tools": ["your_tools"],
        "resources": ["your://resources"]
      }
    }
  }
}
```

2. Restart the service - the new server will be automatically discovered and integrated.

## Usage Examples

### Query the Agent

```bash
curl -X POST http://127.0.0.1:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What Medicare datasets are available?",
    "include_mcp_data": true
  }'
```

### Check Health

```bash
curl http://127.0.0.1:8080/health
```

### List Servers

```bash
curl http://127.0.0.1:8080/servers
```

### Call MCP Server Tool Directly

```bash
curl -X POST http://127.0.0.1:8080/servers/medicare_server/tools/list_medicare_documents \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Testing

Use the included test client:

```powershell
# Interactive testing
python test_client.py

# Automated tests
python test_client.py test
```

## Development

### Project Structure

```
backend/
├── agent.py              # Main web service
mcp_agent_config.json     # MCP server configuration
start_web_service.ps1     # Startup script
test_client.py            # Test client
.env                      # Environment variables
```

### Running in Development

```powershell
# Start Medicare server separately
cd servers
python medicare_server.py

# Start agent service with reload
cd backend
uvicorn agent:app --reload --host 0.0.0.0 --port 8080
```

## Deployment Considerations

### Production Deployment

1. **Environment Variables**: Set production values in `.env`
2. **Security**: Configure appropriate CORS origins
3. **Monitoring**: Use health endpoints for monitoring
4. **Scaling**: Deploy behind a load balancer for high availability

### Docker Deployment

The service can be containerized for production deployment:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "backend/agent.py"]
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure MCP servers are running and accessible
2. **API Key Issues**: Verify `GEMINI_API_KEY` is set correctly
3. **Port Conflicts**: Use different ports if 8080/8000 are in use
4. **Health Check Failures**: Check MCP server health endpoints

### Logs

The service provides detailed logging. Check console output for:
- Server startup messages
- Health check results
- API request/response details
- Error messages with stack traces

## License

See LICENSE file for details.
