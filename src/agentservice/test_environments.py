#!/usr/bin/env python3
"""
Agent Service Environment Testing Script

This script tests the agent service in both development and production modes
to demonstrate the environment-specific configurations.
"""

import asyncio
import os
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv
import httpx

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

async def test_agent_service(base_url: str, environment: str) -> Dict[str, Any]:
    """Test the agent service endpoints."""
    print(f"{Colors.BLUE}🧪 Testing Agent Service ({environment.upper()}){Colors.NC}")
    print(f"{Colors.BLUE}Base URL: {base_url}{Colors.NC}")
    print("-" * 50)
    
    results = {
        "environment": environment,
        "base_url": base_url,
        "tests": {}
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health Check
        try:
            print(f"{Colors.YELLOW}📋 Testing health endpoint...{Colors.NC}")
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
            health_data = response.json()
            
            print(f"{Colors.GREEN}✅ Health check passed{Colors.NC}")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Service: {health_data.get('service')}")
            print(f"   MCP Connection: {health_data.get('mcp_connection')}")
            
            results["tests"]["health"] = {
                "status": "passed",
                "data": health_data
            }
        except Exception as e:
            print(f"{Colors.RED}❌ Health check failed: {str(e)}{Colors.NC}")
            results["tests"]["health"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 2: List Agents
        try:
            print(f"\n{Colors.YELLOW}📋 Testing agents endpoint...{Colors.NC}")
            response = await client.get(f"{base_url}/agents")
            response.raise_for_status()
            agents_data = response.json()
            
            print(f"{Colors.GREEN}✅ Agents endpoint passed{Colors.NC}")
            print(f"   Orchestrator: {agents_data.get('orchestrator', {}).get('name')}")
            domain_agents = agents_data.get('domain_agents', {})
            print(f"   Domain Agents: {list(domain_agents.keys())}")
            
            results["tests"]["agents"] = {
                "status": "passed",
                "data": agents_data
            }
        except Exception as e:
            print(f"{Colors.RED}❌ Agents endpoint failed: {str(e)}{Colors.NC}")
            results["tests"]["agents"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 3: List Tools
        try:
            print(f"\n{Colors.YELLOW}📋 Testing tools endpoint...{Colors.NC}")
            response = await client.get(f"{base_url}/tools")
            response.raise_for_status()
            tools_data = response.json()
            
            tools_count = len(tools_data.get('tools', []))
            print(f"{Colors.GREEN}✅ Tools endpoint passed{Colors.NC}")
            print(f"   Available Tools: {tools_count}")
            if tools_count > 0:
                tool_names = [tool['name'] for tool in tools_data['tools'][:5]]
                print(f"   Sample Tools: {tool_names}{'...' if tools_count > 5 else ''}")
            
            results["tests"]["tools"] = {
                "status": "passed",
                "data": {"tool_count": tools_count}
            }
        except Exception as e:
            print(f"{Colors.RED}❌ Tools endpoint failed: {str(e)}{Colors.NC}")
            results["tests"]["tools"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 4: Simple Chat Request
        try:
            print(f"\n{Colors.YELLOW}📋 Testing chat endpoint...{Colors.NC}")
            chat_request = {
                "message": "Hello, can you help me find products?",
                "user_id": "test_user_123",
                "session_id": "test_session_123",
                "context": {"test_environment": environment}
            }
            
            response = await client.post(f"{base_url}/chat", json=chat_request)
            response.raise_for_status()
            chat_data = response.json()
            
            print(f"{Colors.GREEN}✅ Chat endpoint passed{Colors.NC}")
            print(f"   Agent Used: {chat_data.get('agent_used')}")
            print(f"   Tools Called: {chat_data.get('tools_called')}")
            print(f"   Response Length: {len(chat_data.get('response', ''))}")
            
            results["tests"]["chat"] = {
                "status": "passed",
                "data": {
                    "agent_used": chat_data.get('agent_used'),
                    "tools_called": chat_data.get('tools_called'),
                    "response_length": len(chat_data.get('response', ''))
                }
            }
        except Exception as e:
            print(f"{Colors.RED}❌ Chat endpoint failed: {str(e)}{Colors.NC}")
            results["tests"]["chat"] = {
                "status": "failed",
                "error": str(e)
            }
    
    return results

async def test_development_environment():
    """Test the development environment setup."""
    print(f"{Colors.CYAN}🚀 DEVELOPMENT ENVIRONMENT TEST{Colors.NC}")
    print("=" * 60)
    
    # Load development environment
    load_dotenv(dotenv_path=".env")
    
    dev_url = os.getenv("MCP_BASE_URL", "http://localhost:8081").replace("8081", "8080")
    
    return await test_agent_service(dev_url, "development")

async def test_production_environment():
    """Test the production environment setup."""
    print(f"\n{Colors.CYAN}🚀 PRODUCTION ENVIRONMENT TEST{Colors.NC}")
    print("=" * 60)
    
    # For production testing, we'll use port-forwarding
    prod_url = "http://localhost:8080"
    
    return await test_agent_service(prod_url, "production")

async def main():
    """Main test function."""
    print(f"{Colors.BLUE}🧪 Agent Service Environment Testing{Colors.NC}")
    print("=" * 60)
    print("This script tests the agent service in different environments")
    print("")
    
    # Check environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print(f"{Colors.YELLOW}⚠️ GOOGLE_CLOUD_PROJECT not set. Loading from .env...{Colors.NC}")
        load_dotenv()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            print(f"{Colors.RED}❌ GOOGLE_CLOUD_PROJECT still not set. Please check your .env file.{Colors.NC}")
            return
    
    print(f"{Colors.GREEN}✅ Using Google Cloud Project: {project_id}{Colors.NC}")
    print("")
    
    # Test environments
    dev_results = await test_development_environment()
    
    # Ask user if they want to test production
    print(f"\n{Colors.YELLOW}To test production environment:{Colors.NC}")
    print("1. Deploy the service: kubectl apply -f kubernetes-manifests/agentservice-deployment.yaml")
    print("2. Port-forward: kubectl port-forward svc/agentservice 8080:8080")
    print("3. Run this script again")
    
    # Summary
    print(f"\n{Colors.CYAN}📊 TEST SUMMARY{Colors.NC}")
    print("=" * 40)
    
    print(f"\n{Colors.BLUE}Development Environment:{Colors.NC}")
    for test_name, test_result in dev_results["tests"].items():
        status_icon = "✅" if test_result["status"] == "passed" else "❌"
        print(f"  {status_icon} {test_name.capitalize()}: {test_result['status']}")
    
    print(f"\n{Colors.GREEN}🎉 Environment testing completed!{Colors.NC}")

if __name__ == "__main__":
    print("Agent Service Environment Testing")
    print("This script tests the agent service in different environments")
    print()
    print("Prerequisites:")
    print("1. MCP server running (kubectl port-forward svc/mcpserver 8081:8080)")
    print("2. Agent service running locally or deployed to cluster")
    print("3. .env file configured with GOOGLE_CLOUD_PROJECT")
    print()
    
    asyncio.run(main()) 