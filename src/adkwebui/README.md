# ADK Web UI - Agent Development Kit Web Interface

A modern web interface for interacting with the Online Boutique Agent Service.

## Architecture

```
Browser → ADK Web UI → Agent Service → MCP Server → Backend Services
```

## Features

- 🤖 **Multi-Agent Chat Interface**: Interact with specialized AI agents
- 🔄 **Real-time Communication**: WebSocket-like experience with HTTP polling
- 🎨 **Modern UI**: Clean, responsive design
- 🔧 **Agent Information**: View available agents and their capabilities
- 📱 **Mobile Friendly**: Works on all device sizes

## Local Development

### Prerequisites

1. **Agent Service** running on port 8080
2. **MCP Server** accessible (directly or via port-forward)
3. Python 3.11+

### Setup

1. **Install dependencies:**
   ```bash
   cd src/adkwebui
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env as needed
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **Access the UI:**
   ```
   http://localhost:8000
   ```

### Testing with Port-Forward

If testing with Kubernetes services:

```bash
# Terminal 1: Port-forward MCP Server
kubectl port-forward svc/mcpserver 8081:8080

# Terminal 2: Port-forward Agent Service (if deployed)
kubectl port-forward svc/agentservice 8082:8080

# Terminal 3: Run ADK Web UI
cd src/adkwebui
AGENT_SERVICE_URL=http://localhost:8082 python main.py
```

### Testing with Local Agent Service

If running Agent Service locally:

```bash
# Terminal 1: Port-forward MCP Server
kubectl port-forward svc/mcpserver 8081:8080

# Terminal 2: Run Agent Service locally
cd src/agentservice
source venv/bin/activate
ENVIRONMENT=development MCP_BASE_URL=http://localhost:8081 python main.py

# Terminal 3: Run ADK Web UI
cd src/adkwebui
AGENT_SERVICE_URL=http://localhost:8080 python main.py
```

## Deployment

### Docker Build

```bash
cd src/adkwebui
docker build -t gcr.io/gke-hack-471804/adkwebui:latest .
docker push gcr.io/gke-hack-471804/adkwebui:latest
```

### Kubernetes Deployment

```bash
kubectl apply -f kubernetes-manifests/adkwebui.yaml
```

### Access via LoadBalancer

Add to your frontend NGINX configuration:

```nginx
location /adk/ {
    proxy_pass http://adkwebui:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## API Endpoints

- `GET /` - Main chat interface
- `GET /health` - Health check
- `POST /api/chat` - Chat with agents (proxied to Agent Service)
- `GET /api/agents` - List available agents (proxied)
- `GET /api/tools` - List available tools (proxied)

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AGENT_SERVICE_URL` | `http://agentservice:8080` | Agent Service URL |
| `ADK_WEBUI_PORT` | `8000` | Port for web UI |

## Usage

1. **Open the web interface** at `http://localhost:8000`
2. **Type your message** in the chat input
3. **Send** and watch as the orchestrator:
   - Analyzes your request
   - Delegates to appropriate domain agents
   - Executes tools via MCP server
   - Returns a comprehensive response

### Example Queries

- **Product Search**: "Show me red dresses under $100"
- **Image Analysis**: "What's in this image?" (with image URL)
- **Product Visualization**: "Show me how this sofa would look in my living room"
- **Multi-step Workflow**: "Find laptops, convert prices to EUR, and show reviews"
- **Cart Management**: "Add the highest-rated laptop to my cart"

## Architecture Details

### Request Flow

1. **User** types message in web UI
2. **ADK Web UI** sends POST to `/api/chat`
3. **Agent Service** receives request with `user_id` and `session_id`
4. **Orchestrator Agent** analyzes request and plans workflow
5. **Domain Agents** execute specialized tasks
6. **MCP Server** provides unified tool access
7. **Response** flows back through the chain

### Session Management

- **user_id**: Extracted from frontend session cookie
- **session_id**: Tracks conversation history
- **context**: Additional metadata (preferences, etc.)

### Error Handling

- Connection failures to Agent Service
- Tool execution errors
- Malformed responses
- Network timeouts

## Development

### Project Structure

```
src/adkwebui/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container build
├── .env.example        # Environment template
└── README.md          # This file
```

### Adding Features

1. **New API endpoints**: Add to `main.py`
2. **UI enhancements**: Modify the HTML template in `serve_index()`
3. **Proxy logic**: Update the `proxy_to_agent_service()` function

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Chat API test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test", "session_id": "test"}'
``` 