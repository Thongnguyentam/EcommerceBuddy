#!/usr/bin/env python3
"""
Test script for Agent Service

Tests the main chat endpoint and agent functionality.
Run this after starting the agent service locally.
"""

import asyncio
import json
import httpx
from typing import Dict, Any

# Configuration
AGENT_SERVICE_URL = "http://localhost:8080"

async def test_agent_service():
    """Test the agent service endpoints."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🚀 Testing Agent Service")
        print("=" * 50)
        
        # Test 1: Health check
        print("\n🏥 Testing health endpoint...")
        try:
            response = await client.get(f"{AGENT_SERVICE_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed: {health_data['status']}")
                print(f"   MCP Connection: {health_data['mcp_connection']}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return
        
        # Test 2: List agents
        print("\n🤖 Testing agents endpoint...")
        try:
            response = await client.get(f"{AGENT_SERVICE_URL}/agents")
            if response.status_code == 200:
                agents_data = response.json()
                print("✅ Agents endpoint working")
                print(f"   Orchestrator: {agents_data['orchestrator']['name']}")
                print(f"   Domain agents: {len(agents_data['domain_agents'])}")
                for agent_name in agents_data['domain_agents']:
                    agent = agents_data['domain_agents'][agent_name]
                    print(f"     - {agent['name']}: {len(agent['tools'])} tools")
            else:
                print(f"❌ Agents endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Agents endpoint error: {str(e)}")
        
        # Test 3: Get tools
        print("\n🔧 Testing tools endpoint...")
        try:
            response = await client.get(f"{AGENT_SERVICE_URL}/tools")
            if response.status_code == 200:
                tools_data = response.json()
                print(f"✅ Tools endpoint working: {len(tools_data.get('tools', []))} tools available")
            else:
                print(f"❌ Tools endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Tools endpoint error: {str(e)}")
        
        # Test 4: Chat endpoint - Product search
        print("\n💬 Testing chat endpoint - Product search...")
        chat_request = {
            "message": "Find me some furniture for my living room",
            "user_id": "test_user_123",
            "context": {}
        }
        
        try:
            response = await client.post(
                f"{AGENT_SERVICE_URL}/chat",
                json=chat_request,
                timeout=60.0
            )
            
            if response.status_code == 200:
                chat_data = response.json()
                print("✅ Chat request successful")
                print(f"   Agent used: {chat_data['agent_used']}")
                print(f"   Tools called: {chat_data['tools_called']}")
                print(f"   Session ID: {chat_data['session_id']}")
                print(f"   Response preview: {chat_data['response'][:100]}...")
            else:
                print(f"❌ Chat request failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Raw response: {response.text}")
                    
        except Exception as e:
            print(f"❌ Chat request error: {str(e)}")
        
        # Test 5: Chat endpoint - Currency conversion
        print("\n💱 Testing chat endpoint - Currency conversion...")
        currency_request = {
            "message": "Convert $100 to EUR",
            "user_id": "test_user_123"
        }
        
        try:
            response = await client.post(
                f"{AGENT_SERVICE_URL}/chat",
                json=currency_request,
                timeout=30.0
            )
            
            if response.status_code == 200:
                chat_data = response.json()
                print("✅ Currency chat successful")
                print(f"   Agent used: {chat_data['agent_used']}")
                print(f"   Tools called: {chat_data['tools_called']}")
                print(f"   Response: {chat_data['response']}")
            else:
                print(f"❌ Currency chat failed: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Currency chat error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🏁 Agent Service testing completed!")

if __name__ == "__main__":
    print("Agent Service Test")
    print("This script tests the full Agent Service REST API")
    print()
    print("Prerequisites:")
    print("1. MCP server running (port-forward: kubectl port-forward svc/mcpserver 8081:8080)")
    print("2. Agent service running (port-forward: kubectl port-forward svc/agentservice 8080:8080)")
    print("   OR run locally with: python main.py")
    print()
    
    asyncio.run(test_agent_service()) 