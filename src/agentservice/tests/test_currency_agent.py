#!/usr/bin/env python3
"""
Currency Agent Testing Script

Test the Currency Agent with multiple queries to ensure it works correctly.
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

# Import agents after path setup
from currency_agent import CurrencyAgent

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
        return {"tools": []}

async def test_currency_agent_multiple_queries(mcp_url: str, tools_schema: dict):
    """Test the Currency Agent with multiple different queries."""
    print("💱 Testing Currency Agent with Multiple Queries")
    print("-" * 50)
    
    # Test queries
    test_queries = [
        {
            "message": "Convert $100 to EUR",
            "description": "Basic USD to EUR conversion"
        },
        {
            "message": "How much is 50 pounds in Japanese yen?",
            "description": "GBP to JPY conversion"
        },
        {
            "message": "What currencies do you support?",
            "description": "List supported currencies"
        },
        {
            "message": "Show me current exchange rates",
            "description": "Get all exchange rates"
        },
        {
            "message": "Format 1234.56 as US dollars",
            "description": "Money formatting request"
        },
        {
            "message": "Convert 500 CAD to Indian rupees",
            "description": "CAD to INR conversion"
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
        
        agent = CurrencyAgent(
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
                    session_id=f"currency_test_{i}"
                )
                
                print(f"✅ Agent: {result['agent_used']}")
                print(f"✅ Tools called: {result['tools_called']}")
                print(f"✅ Response preview: {result['response'][:150]}...")
                
            except Exception as e:
                print(f"❌ Test {i} failed: {str(e)}")
        
        await http_client.aclose()
        print(f"\n🎉 Currency Agent testing completed!")
        
    except Exception as e:
        print(f"❌ Currency Agent setup failed: {str(e)}")

async def test_base_agent_functionality(mcp_url: str, tools_schema: dict):
    """Test base agent functionality."""
    print("\n🧪 Testing Base Agent Functionality")
    print("-" * 40)
    
    try:
        # Initialize Gemini client
        project_id = GOOGLE_CLOUD_PROJECT
        location = GOOGLE_CLOUD_REGION
        
        vertexai.init(project=project_id, location=location)
        gemini_client = genai.Client(vertexai=True, project=project_id, location=location)
        
        # Initialize HTTP client
        http_client = httpx.AsyncClient(timeout=30.0)
        
        agent = CurrencyAgent(
            gemini_client=gemini_client,
            http_client=http_client,
            mcp_base_url=mcp_url,
            tools_schema=tools_schema
        )
        
        # Test response generation
        response = await agent.generate_response("What is currency conversion?")
        print(f"✅ Response generation: {response[:100]}...")
        
        # Test tool filtering
        available_tools = agent.get_available_tools()
        print(f"✅ Available tools: {[tool['name'] for tool in available_tools]}")
        
        await http_client.aclose()
        
    except Exception as e:
        print(f"❌ Base agent functionality test failed: {str(e)}")

async def main():
    """Main test function."""
    print("🚀 Currency Agent Testing")
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
    await test_currency_agent_multiple_queries(mcp_url, tools_schema)
    
    print("\n" + "=" * 50)
    print("🏁 Currency agent testing completed!")

if __name__ == "__main__":
    print("Currency Agent Test")
    print("This script tests the Currency Agent with multiple queries")
    print("Make sure your .env file is configured with GOOGLE_CLOUD_PROJECT")
    print()
    print("For local testing:")
    print("1. Set ENVIRONMENT=development in .env (default)")
    print("2. Port-forward MCP server: kubectl port-forward svc/mcpserver 8081:8080")
    print("3. Run this script")
    print()
    
    asyncio.run(main()) 