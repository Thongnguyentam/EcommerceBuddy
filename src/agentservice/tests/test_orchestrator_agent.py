#!/usr/bin/env python3
"""
Test script for the Orchestrator Agent

This script tests the orchestrator's ability to:
1. Analyze complex user requests
2. Plan multi-step workflows
3. Delegate to appropriate domain agents
4. Synthesize responses from multiple agents

Prerequisites:
- MCP server running and accessible (port-forward: kubectl port-forward svc/mcpserver 8081:8080)
- Environment configured with GOOGLE_CLOUD_PROJECT
- Agent service dependencies installed
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'agents'))

from agents.orchestrator import OrchestratorAgent
import httpx
import vertexai
from google import genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_orchestrator_agent():
    """Set up the orchestrator agent for testing."""
    
    # Load environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gke-hack-471804")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Set MCP URL based on environment
    if environment == "development":
        mcp_base_url = "http://localhost:8081"
    else:
        mcp_base_url = "http://mcpserver:8080"
    
    print(f"📋 Using project: {project_id}")
    print(f"📋 Using region: {region}")
    print(f"📋 Environment: {environment}")
    print(f"📋 MCP URL: {mcp_base_url}")
    
    # Initialize Vertex AI and Gemini
    vertexai.init(project=project_id, location=region)
    gemini_client = genai.Client(vertexai=True, project=project_id, location=region)
    
    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=60.0)
    
    # Discover tools from MCP server
    print(f"\n🔍 Discovering tools from MCP server...")
    response = await http_client.get(f"{mcp_base_url}/tools/schema")
    response.raise_for_status()
    tools_schema = response.json()
    
    print(f"✅ Discovered {len(tools_schema.get('tools', []))} tools")
    tool_names = [tool['name'] for tool in tools_schema.get('tools', [])]
    print(f"Tools: {tool_names[:5]}{'...' if len(tool_names) > 5 else ''}")
    
    # Initialize orchestrator agent
    orchestrator = OrchestratorAgent(
        gemini_client=gemini_client,
        http_client=http_client,
        mcp_base_url=mcp_base_url,
        tools_schema=tools_schema
    )
    
    # Initialize domain agents (simplified for testing)
    from agents.product_agent import ProductAgent
    from agents.image_agent import ImageAgent
    from agents.cart_agent import CartAgent
    from agents.currency_agent import CurrencyAgent
    from agents.sentiment_agent import SentimentAgent
    
    domain_agents = {
        "product": ProductAgent(gemini_client, http_client, mcp_base_url, tools_schema),
        "image": ImageAgent(gemini_client, http_client, mcp_base_url, tools_schema),
        "cart": CartAgent(gemini_client, http_client, mcp_base_url, tools_schema),
        "currency": CurrencyAgent(gemini_client, http_client, mcp_base_url, tools_schema),
        "sentiment": SentimentAgent(gemini_client, http_client, mcp_base_url, tools_schema),
    }
    
    # Set domain agents on orchestrator for delegation
    orchestrator._domain_agents = domain_agents
    
    return orchestrator, http_client

async def test_orchestrator_agent():
    """Test the orchestrator agent with complex multi-domain queries."""
    
    print("🚀 Orchestrator Agent Testing")
    print("=" * 50)
    
    orchestrator, http_client = await setup_orchestrator_agent()
    
    # Test queries that require orchestration across multiple domains
    test_queries = [
        # {
        #     "name": "Complex shopping workflow",
        #     "query": "I'm looking for a comfortable chair under $200. Show me some options, convert the prices to EUR, and help me visualize how it would look in my living room.",
        #     "context": {
        #         "base_image_url": "https://example.com/living_room.jpg",
        #         "budget": 200,
        #         "currency": "USD"
        #     }
        # },
        # {
        #     "name": "Product research with reviews",
        #     "query": "I want to buy a coffee maker. Find me some options, show me what people are saying about them, and add the best-rated one to my cart.",
        #     "context": {
        #         "category": "appliances",
        #         "user_preferences": "high-rated"
        #     }
        # },
        # {
        #     "name": "Multi-currency shopping",
        #     "query": "Show me all laptops, convert their prices to Japanese Yen, and tell me which ones have the best reviews.",
        #     "context": {
        #         "target_currency": "JPY",
        #         "product_type": "laptop"
        #     }Error analyzing image:
        # },
        # {
        #     "name": "Image analysis and product matching",
        #     "query": "Analyze this room image (https://www.anvekitchenandbath.com/wp-content/uploads/2022/12/modern-minimalist-kitchen-1200x630-cropped.jpeg) and recommend products that would fit the style, then show me reviews for the top recommendation.",
        #     "context": {
        #         "image_url": "https://www.anvekitchenandbath.com/wp-content/uploads/2022/12/modern-minimalist-kitchen-1200x630-cropped.jpeg",
        #         "style_preference": "modern"
        #     }
        # },
        {
            "name": "Cart management workflow",
            "query": "Show me what's in my cart, convert all prices to British Pounds, and if the total is over £100, remove the cheapest item.",
            "context": {
                "user_id": "test_user_123",
                "target_currency": "GBP",
                "budget_limit": 100
            }
        }
    ]
    
    print(f"\n🧪 Testing Orchestrator with {len(test_queries)} Complex Queries")
    print("-" * 60)
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        
        try:
            # Process the request with proper user context
            user_id = "test_user_123"
            session_id = f'test_session_456'
            
            result = await orchestrator.process_request(
                message=test_case['query'],
                user_id=user_id,
                session_id=session_id,
                context=test_case.get('context')
            )
            
            # Display results
            print(f"✅ Agent: {result['agent_used']}")
            print(f"✅ Tools called: {result['tools_called']}")
            print(f"✅ Workflow steps: {len(result.get('workflow_steps', []))}")
            
            # Show workflow step summary
            if 'workflow_steps' in result:
                for step in result['workflow_steps']:
                    step_domain = step.get('domain', 'unknown')
                    step_status = step.get('status', 'unknown')
                    step_tools = step.get('tools_used', [])
                    agent_used = step.get('agent_used', 'unknown')
                    print(f"   Step {step.get('step', '?')}: {step_domain} ({step_status}) - Agent: {agent_used} - Tools: {step_tools}")
                    
                    # Debug: Show step results if tools were called
                    if step_tools:
                        print(f"     → Tool results: {len(step.get('results', []))} results")
                    else:
                        print(f"     → No tools called - Results: {step.get('results', [])}")
            
            # Show response preview
            response_preview = result['response']
            print(f"✅ Response preview: {response_preview}")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            logger.error(f"Orchestrator test {i} failed: {str(e)}")
    
    print(f"\n🎉 Orchestrator Agent testing completed!")
    
    # Cleanup
    await http_client.aclose()

async def test_orchestrator_analysis():
    """Test the orchestrator's request analysis capabilities."""
    
    print("\n" + "=" * 50)
    print("🧠 Testing Orchestrator Analysis Capabilities")
    print("-" * 60)
    
    orchestrator, http_client = await setup_orchestrator_agent()
    
    # Test different types of request analysis
    analysis_tests = [
        # {
        #     "query": "Find me a red dress",
        #     "expected_domains": ["product"],
        #     "expected_complexity": "simple"
        # },
        # {
        #     "query": "I want to see how this couch would look in my room and check its reviews",
        #     "expected_domains": ["image", "sentiment"],
        #     "expected_complexity": "moderate"
        # },
        # {
        #     "query": "Show me all electronics, convert prices to EUR, analyze customer sentiment, and add the best-rated item to my cart",
        #     "expected_domains": ["product", "currency", "sentiment", "cart"],
        #     "expected_complexity": "complex"
        # }
    ]
    
    for i, test in enumerate(analysis_tests, 1):
        print(f"\n📊 Analysis Test {i}: {test['query']}")
        
        try:
            # Test the analysis method directly
            analysis = await orchestrator._analyze_request(test['query'])
            
            print(f"✅ Intent: {analysis.get('intent', 'Unknown')}")
            print(f"✅ Complexity: {analysis.get('complexity', 'Unknown')}")
            print(f"✅ Domains needed: {analysis.get('domains_needed', [])}")
            print(f"✅ Workflow steps: {len(analysis.get('workflow_steps', []))}")
            
            # Validate analysis
            complexity = analysis.get('complexity', 'unknown')
            domains = analysis.get('domains_needed', [])
            
            if complexity == test['expected_complexity']:
                print(f"✅ Complexity prediction correct: {complexity}")
            else:
                print(f"⚠️  Complexity mismatch: expected {test['expected_complexity']}, got {complexity}")
            
            # Check if expected domains are covered
            expected_covered = all(domain in domains for domain in test['expected_domains'])
            if expected_covered:
                print(f"✅ Domain prediction correct: {domains}")
            else:
                print(f"⚠️  Domain mismatch: expected {test['expected_domains']}, got {domains}")
                
        except Exception as e:
            print(f"❌ Analysis test failed: {str(e)}")
    
    await http_client.aclose()

if __name__ == "__main__":
    print("Orchestrator Agent Test")
    print("This script tests the Orchestrator Agent's coordination capabilities")
    print("Make sure your .env file is configured with GOOGLE_CLOUD_PROJECT")
    print()
    print("For local testing:")
    print("1. Set ENVIRONMENT=development in .env (default)")
    print("2. Port-forward MCP server: kubectl port-forward svc/mcpserver 8081:8080")
    print("3. Run this script")
    print()
    
    asyncio.run(test_orchestrator_agent())
    asyncio.run(test_orchestrator_analysis()) 