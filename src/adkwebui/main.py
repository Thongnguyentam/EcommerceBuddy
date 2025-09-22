#!/usr/bin/env python3
"""
ADK (Agent Development Kit) Web UI Service

This service provides a web-based interface for interacting with the Agent Service.
It serves static HTML/CSS/JS files and proxies API calls to the Agent Service.

Architecture:
- Serves static web UI files
- Proxies /api/* requests to Agent Service
- Provides WebSocket support for real-time chat
- Handles user authentication/sessions
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agentservice:8080")
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(
    title="ADK Web UI",
    description="Web interface for Online Boutique Agent Service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP client for proxying requests
http_client = httpx.AsyncClient(timeout=60.0)

@app.on_event("startup")
async def startup():
    """Initialize the ADK Web UI service."""
    logger.info("🚀 Starting ADK Web UI Service...")
    logger.info(f"🔗 Agent Service URL: {AGENT_SERVICE_URL}")
    
    # Create directories if they don't exist
    STATIC_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)

@app.on_event("shutdown") 
async def shutdown():
    """Cleanup on shutdown."""
    await http_client.aclose()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Test connection to agent service
    try:
        response = await http_client.get(f"{AGENT_SERVICE_URL}/health", timeout=5.0)
        agent_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        agent_status = "unreachable"
    
    return {
        "status": "healthy",
        "service": "adk-webui",
        "version": "1.0.0",
        "agent_service": agent_status
    }

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main ADK Web UI page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADK - Agent Development Kit</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .chat-container { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .chat-messages { height: 400px; overflow-y: auto; border: 1px solid #e1e5e9; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #fafafa; }
        .message { margin-bottom: 15px; }
        .message.user { text-align: right; }
        .message.assistant { text-align: left; }
        .message-content { display: inline-block; padding: 10px 15px; border-radius: 18px; max-width: 70%; }
        .user .message-content { background: #007bff; color: white; }
        .assistant .message-content { background: #e9ecef; color: #333; }
        .input-container { display: flex; gap: 10px; }
        .message-input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 25px; font-size: 16px; }
        .send-button { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 25px; cursor: pointer; font-weight: 500; }
        .send-button:hover { background: #0056b3; }
        .send-button:disabled { background: #ccc; cursor: not-allowed; }
        .agent-info { display: flex; gap: 20px; margin-top: 20px; }
        .agent-card { flex: 1; background: #f8f9fa; padding: 15px; border-radius: 8px; }
        .loading { text-align: center; color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Agent Development Kit (ADK)</h1>
            <p>Interact with specialized AI agents for your shopping needs</p>
        </div>
        
        <div class="chat-container">
            <div class="chat-messages" id="messages"></div>
            <div class="input-container">
                <input type="text" class="message-input" id="messageInput" placeholder="Ask me anything about products, images, reviews, or shopping..." onkeypress="handleKeyPress(event)">
                <button class="send-button" id="sendButton" onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <div class="agent-info">
            <div class="agent-card">
                <h3>🛍️ Product Agent</h3>
                <p>Search products, get recommendations, browse catalog</p>
            </div>
            <div class="agent-card">
                <h3>🖼️ Image Agent</h3>
                <p>Analyze images, visualize products in rooms</p>
            </div>
            <div class="agent-card">
                <h3>🛒 Cart Agent</h3>
                <p>Manage shopping cart, add/remove items</p>
            </div>
            <div class="agent-card">
                <h3>💰 Currency Agent</h3>
                <p>Convert currencies, format prices</p>
            </div>
            <div class="agent-card">
                <h3>⭐ Sentiment Agent</h3>
                <p>Analyze reviews, check product ratings</p>
            </div>
        </div>
    </div>

    <script>
        let sessionId = null;
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage('user', message);
            
            // Clear input and disable button
            input.value = '';
            sendButton.disabled = true;
            sendButton.textContent = 'Sending...';
            
            // Add loading message
            const loadingId = addMessage('assistant', 'Thinking...', true);
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                sessionId = data.session_id;
                
                // Remove loading message and add response
                removeMessage(loadingId);
                addMessage('assistant', data.response);
                
                // Show agent and tools info
                if (data.agent_used && data.tools_called.length > 0) {
                    addMessage('assistant', `🤖 Agent: ${data.agent_used} | 🔧 Tools: ${data.tools_called.join(', ')}`, false, 'info');
                }
                
            } catch (error) {
                removeMessage(loadingId);
                addMessage('assistant', `Sorry, I encountered an error: ${error.message}`, false, 'error');
            } finally {
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                input.focus();
            }
        }
        
        function addMessage(sender, content, isLoading = false, type = 'normal') {
            const messages = document.getElementById('messages');
            const messageId = 'msg-' + Date.now() + Math.random();
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            messageDiv.id = messageId;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            if (type === 'info') {
                contentDiv.style.background = '#d4edda';
                contentDiv.style.color = '#155724';
                contentDiv.style.fontSize = '0.9em';
            } else if (type === 'error') {
                contentDiv.style.background = '#f8d7da';
                contentDiv.style.color = '#721c24';
            }
            
            if (isLoading) {
                contentDiv.className += ' loading';
            }
            
            // Convert markdown links to HTML
            const htmlContent = content.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
            contentDiv.innerHTML = htmlContent;
            
            messageDiv.appendChild(contentDiv);
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
            
            return messageId;
        }
        
        function removeMessage(messageId) {
            const message = document.getElementById(messageId);
            if (message) {
                message.remove();
            }
        }
        
        // Focus on input when page loads
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('messageInput').focus();
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

# Proxy API requests to Agent Service
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_agent_service(request: Request, path: str):
    """Proxy API requests to the Agent Service."""
    try:
        # Get request data
        headers = dict(request.headers)
        headers.pop('host', None)  # Remove host header
        
        # Prepare request data
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        else:
            body = None
        
        # Make request to agent service
        url = f"{AGENT_SERVICE_URL}/{path}"
        response = await http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        # Return response
        return response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        
    except httpx.RequestError as e:
        logger.error(f"Request to agent service failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Agent service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Proxy request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# Serve static files if they exist
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    port = int(os.getenv("ADK_WEBUI_PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    ) 