#!/usr/bin/env python3
"""
Online Boutique Agent Service

This service provides AI-powered shopping assistants that leverage the MCP server
for tool discovery and execution. Multiple specialized agents handle different
domains while an orchestrator coordinates complex multi-step workflows.

Architecture:
- Orchestrator Agent: Discovers tools from MCP, plans workflows, coordinates domain agents
- Domain Agents: Product, Image, Cart, Currency, Sentiment - each specialized for their domain
- All agents use Gemini for reasoning and MCP server for tool execution
"""

import os
import logging
import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import vertexai
from google import genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request/Response models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    user_id: str  # Required: User identifier from frontend session
    session_id: str  # Required: Chat session identifier (same as user_id in this system)
    context: Optional[Dict[str, Any]] = None  # Additional context (preferences, etc.)

class ChatResponse(BaseModel):
    response: str
    agent_used: str
    tools_called: List[str]
    session_id: str
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    mcp_connection: str

# Global variables
mcp_base_url: str = None
http_client: httpx.AsyncClient = None
tools_schema: Dict[str, Any] = None
gemini_client = None
orchestrator_agent = None
domain_agents: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global mcp_base_url, http_client, tools_schema, gemini_client, orchestrator_agent, domain_agents
    
    # Startup
    logger.info("🚀 Starting Agent Service...")
    
    try:
        # Initialize configuration
        environment = os.getenv("ENVIRONMENT", "production")
        
        # Set MCP URL based on environment
        if environment == "development":
            mcp_base_url = os.getenv("MCP_BASE_URL", "http://localhost:8081")
        else:
            mcp_base_url = os.getenv("MCP_BASE_URL", "http://mcpserver:8080")
        
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        
        logger.info(f"🌍 Environment: {environment}")
        logger.info(f"🔗 MCP Base URL: {mcp_base_url}")
        
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
        
        # Initialize Vertex AI and Gemini
        try:
            vertexai.init(project=project_id, location=location)
            gemini_client = genai.Client(vertexai=True, project=project_id, location=location)
            logger.info(f"✅ Initialized Gemini client for project: {project_id}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vertex AI: {str(e)}")
            raise
        
        # Initialize HTTP client
        http_client = httpx.AsyncClient(timeout=60.0)
        
        # Discover tools from MCP server
        try:
            await discover_tools()
            logger.info(f"✅ Discovered {len(tools_schema.get('tools', []))} tools from MCP server")
        except Exception as e:
            logger.error(f"❌ Failed to discover tools from MCP: {str(e)}")
            raise
        
        # Initialize agents
        from agents.orchestrator import OrchestratorAgent
        from agents.product_agent import ProductAgent
        from agents.image_agent import ImageAgent
        from agents.cart_agent import CartAgent
        from agents.currency_agent import CurrencyAgent
        from agents.sentiment_agent import SentimentAgent
        # from agents.shopping_assistant_agent import ShoppingAssistantAgent
        
        # Initialize domain agents first
        domain_agents = {
            "product": ProductAgent(gemini_client, http_client, mcp_base_url, tools_schema),
            "image": ImageAgent(gemini_client, http_client, mcp_base_url, tools_schema),
            "cart": CartAgent(gemini_client, http_client, mcp_base_url, tools_schema),
            "currency": CurrencyAgent(gemini_client, http_client, mcp_base_url, tools_schema),
            "sentiment": SentimentAgent(gemini_client, http_client, mcp_base_url, tools_schema),
            # "shopping_assistant": ShoppingAssistantAgent(gemini_client, http_client, mcp_base_url, tools_schema)
        }
        
        # Initialize orchestrator and provide it access to domain agents
        orchestrator_agent = OrchestratorAgent(
            gemini_client=gemini_client,
            http_client=http_client,
            mcp_base_url=mcp_base_url,
            tools_schema=tools_schema
        )
        
        # Set domain agents on orchestrator for delegation
        orchestrator_agent._domain_agents = domain_agents
        
        logger.info(f"✅ Initialized orchestrator and {len(domain_agents)} domain agents")
        logger.info(f"✅ Agent Service ready - connected to MCP at {mcp_base_url}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down Agent Service...")
    try:
        if http_client:
            await http_client.aclose()
            logger.info("✅ HTTP client closed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")

async def discover_tools():
    """Discover available tools from MCP server."""
    global tools_schema
    try:
        response = await http_client.get(f"{mcp_base_url}/tools/schema")
        response.raise_for_status()
        tools_schema = response.json()
        logger.info(f"Discovered tools: {[tool['name'] for tool in tools_schema.get('tools', [])]}")
    except Exception as e:
        logger.error(f"Failed to discover tools: {str(e)}")
        raise

# Create FastAPI app
app = FastAPI(
    title="Online Boutique Agent Service",
    description="AI-powered shopping assistants with specialized domain agents",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Test MCP connection
    mcp_status = "healthy"
    try:
        response = await http_client.get(f"{mcp_base_url}/health", timeout=5.0)
        if response.status_code != 200:
            mcp_status = "unhealthy"
    except Exception:
        mcp_status = "unreachable"
    
    return HealthResponse(
        status="healthy",
        service="online-boutique-agent-service",
        version="1.0.0",
        mcp_connection=mcp_status
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - routes to orchestrator agent."""
    try:
        start_time = datetime.now()
        
        # Log user context for debugging
        logger.info(f"Chat request from user: {request.user_id or 'anonymous'}, session: {request.session_id or 'new'}")
        
        # Use orchestrator to handle the request
        result = await orchestrator_agent.process_request(
            message=request.message,
            user_id=request.user_id,  # Flows from frontend authentication
            session_id=request.session_id,
            context=request.context
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Chat request processed in {processing_time:.2f}s")
        
        return ChatResponse(
            response=result["response"],
            agent_used=result["agent_used"],
            tools_called=result["tools_called"],
            session_id=result["session_id"],
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/agents")
async def list_agents():
    """List all available agents and their capabilities."""
    return {
        "orchestrator": {
            "name": "Orchestrator Agent",
            "description": "Coordinates complex workflows across domain agents",
            "capabilities": ["workflow_planning", "agent_coordination", "tool_discovery"]
        },
        "domain_agents": {
            agent_name: {
                "name": agent.name,
                "description": agent.description,
                "tools": agent.get_available_tools()
            }
            for agent_name, agent in domain_agents.items()
        }
    }

@app.get("/tools")
async def get_available_tools():
    """Get all tools available from MCP server."""
    return tools_schema

@app.post("/tools/refresh")
async def refresh_tools():
    """Refresh tool discovery from MCP server."""
    try:
        await discover_tools()
        
        # Update all agents with new tools
        orchestrator_agent.update_tools_schema(tools_schema)
        for agent in domain_agents.values():
            agent.update_tools_schema(tools_schema)
            
        return {
            "status": "success",
            "message": f"Refreshed {len(tools_schema.get('tools', []))} tools",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool refresh failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("AGENT_SERVICE_PORT", "8080"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )
