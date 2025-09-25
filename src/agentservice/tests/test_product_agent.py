#!/usr/bin/env python3
"""
Product Agent Testing Script

Test the Product Agent with multiple queries to ensure it works correctly.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory and agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))

import httpx
import vertexai
from google import genai

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # show DEBUG and above
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger.setLevel(logging.DEBUG)

# Import agents after path setup
from product_agent import ProductAgent

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

async def discover_tools_from_mcp(mcp_url: str) -> dict:
    """Discover tools from MCP server."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{mcp_url}/tools/schema")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"❌ Failed to discover tools from MCP: {str(e)}")
        print("Make sure MCP server is running and accessible")
        # Return empty schema as fallback
        return {"tools": []}

async def test_product_agent_multiple_queries(mcp_url: str, tools_schema: dict):
    """Test the Product Agent with multiple different queries."""
    print("🔍 Testing Product Agent with Multiple Queries")
    print("-" * 50)
    
    # Test queries
    test_queries = [
        {
            "message": "Find me a comfortable sofa for my living room",
            "description": "Furniture search query"
        },
        {
            "message": "Show me kitchen utensils under $50",
            "description": "Category and price-based search"
        },
        {
            "message": "I need a good T-shirt and shorts for female",
            "description": "Style-specific product search"
        },
        {
            "message": "What products do you have in the home category?",
            "description": "Category browsing query"
        },
        {
            "message": "Find me something similar to product OLJCESPC7Z",
            "description": "Product ID-based search"
        }
    ]
    
    try:
        # Initialize Gemini client
        project_id = GOOGLE_CLOUD_PROJECT
        location = GOOGLE_CLOUD_REGION
        
        vertexai.init(project=project_id, location=location)
        gemini_client = genai.Client(vertexai=True, project=project_id, location=location)
        
        # Initialize HTTP client
        http_client = httpx.AsyncClient(timeout=60.0)
        
        # Import and create agent
        from product_agent import ProductAgent
        
        agent = ProductAgent(
            gemini_client=gemini_client,
            http_client=http_client,
            mcp_base_url=mcp_url,
            tools_schema=tools_schema
        )
        
        # Test each query
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}: {test_case['description']}")
            print(f"Query: {test_case['message']}")
            
            try:
                result = await agent.process_request(
                    message=test_case['message'],
                    user_id="test_user_123",
                    session_id=f"test_session_{i}"
                )
                
                print(f"✅ Agent: {result['agent_used']}")
                print(f"✅ Tools called: {result['tools_called']}")
                print(f"✅ Response preview: {result['response']}")
                
            except Exception as e:
                print(f"❌ Test {i} failed: {str(e)}")
        
        await http_client.aclose()
        print(f"\n🎉 Product Agent testing completed!")
        
    except Exception as e:
        print(f"❌ Product Agent setup failed: {str(e)}")



async def test_base_agent_functionality(mcp_url: str, tools_schema: dict):
    """Test base agent functionality."""
    print("\n🧪 Testing Base Agent Functionality")
    print("-" * 40)
    
    try:
        # Initialize Gemini client
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        
        vertexai.init(project=project_id, location=location)
        gemini_client = genai.Client(vertexai=True, project=project_id, location=location)
        
        # Initialize HTTP client
        http_client = httpx.AsyncClient(timeout=30.0)
        
        # Import and create agent
        from product_agent import ProductAgent
        
        agent = ProductAgent(
            gemini_client=gemini_client,
            http_client=http_client,
            mcp_base_url=mcp_url,
            tools_schema=tools_schema
        )
        
        # Test response generation
        response = await agent.generate_response("Find a good knife set")
        print(f"✅ Response generation: {response[:100]}...")
        
        # Test tool filtering
        available_tools = agent.get_available_tools()
        print(f"✅ Available tools: {[tool['name'] for tool in available_tools]}")
        
        await http_client.aclose()
        
    except Exception as e:
        print(f"❌ Base agent functionality test failed: {str(e)}")

async def main():
    """Main test function."""
    print("🚀 Local Agent Testing")
    print("=" * 50)
    
    # Check environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set. Please check your .env file.")
        return
    
    # Determine MCP URL based on environment
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        mcp_url = "http://mcpserver:8080"
    else:
        mcp_url = "http://localhost:8081"
    
    print(f"📋 Using project: {project_id}")
    print(f"📋 Using region: {os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')}")
    print(f"📋 Environment: {environment}")
    print(f"📋 MCP URL: {mcp_url}")
    
    # Discover tools from MCP server
    print(f"\n🔍 Discovering tools from MCP server...")
    tools_schema = await discover_tools_from_mcp(mcp_url)
    
    if not tools_schema.get("tools"):
        print("❌ No tools discovered. Make sure MCP server is running.")
        print("For local testing, run: kubectl port-forward svc/mcpserver 8081:8080")
        return
    
    print(f"✅ Discovered {len(tools_schema['tools'])} tools")
    print(f"Tools: {[tool['name'] for tool in tools_schema['tools'][:5]]}{'...' if len(tools_schema['tools']) > 5 else ''}")
    
    # Run tests
    await test_base_agent_functionality(mcp_url, tools_schema)
    await test_product_agent_multiple_queries(mcp_url, tools_schema)
    
    print("\n" + "=" * 50)
    print("🏁 Product agent testing completed!")

if __name__ == "__main__":
    print("Product Agent Test")
    print("This script tests the Product Agent with multiple queries")
    print("Make sure your .env file is configured with GOOGLE_CLOUD_PROJECT")
    print()
    print("For local testing:")
    print("1. Set ENVIRONMENT=development in .env (default)")
    print("2. Port-forward MCP server: kubectl port-forward svc/mcpserver 8081:8080")
    print("3. Run this script")
    print()
    
    asyncio.run(main()) 