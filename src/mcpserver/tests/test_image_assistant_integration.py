#!/usr/bin/env python3
"""
Integration test for Image Assistant MCP Tools against port-forwarded MCP server.

Prerequisites:
1. Port-forward MCP server: kubectl port-forward svc/mcpserver 8081:8080
2. Install requirements: pip install -r requirements.txt
3. Run this script: python test_image_assistant_integration.py

This test verifies the MCP Image Assistant tools work with the real MCP server.
"""

import asyncio
import aiohttp
import json
import sys
import time
import os
from typing import Dict, Any

# Test configuration
MCP_SERVER_URL = "http://localhost:8081"  # Port-forwarded MCP server
TEST_IMAGE_URL = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Living room
TEST_PRODUCT_URL = "https://static.athome.com/images/w_1200,h_1200,c_pad,f_auto,fl_lossy,q_auto/v1746793260/p/124379171_E1/providence-blue-white-floral-porcelain-vase-12.jpg"  # Vase

async def test_mcp_server_health():
    """Test if the MCP server is healthy."""
    print("🏥 Testing MCP Server Health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MCP_SERVER_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ MCP Server is healthy: {data['status']}")
                    return True
                else:
                    print(f"❌ MCP Server health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to connect to MCP Server: {e}")
        return False

async def test_image_assistant_health():
    """Test if the Image Assistant Service is healthy through MCP."""
    print("\n🔍 Testing Image Assistant Service Health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MCP_SERVER_URL}/image-assistant/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Image Assistant Service is healthy: {data['status']}")
                    return True
                else:
                    print(f"❌ Image Assistant Service health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to check Image Assistant Service health: {e}")
        return False

async def test_tools_schema():
    """Test if the tools schema includes Image Assistant tools."""
    print("\n📋 Testing Tools Schema...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MCP_SERVER_URL}/tools/schema") as response:
                if response.status == 200:
                    data = await response.json()
                    tools = data.get("tools", [])
                    
                    # Check for Image Assistant tools
                    image_tools = [tool for tool in tools if "image" in tool["name"].lower()]
                    
                    if image_tools:
                        print(f"✅ Found {len(image_tools)} Image Assistant tools:")
                        for tool in image_tools:
                            print(f"   - {tool['name']}: {tool['description']}")
                        return True
                    else:
                        print("❌ No Image Assistant tools found in schema")
                        return False
                else:
                    print(f"❌ Failed to get tools schema: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to get tools schema: {e}")
        return False

async def test_analyze_image_tool():
    """Test the analyze image tool."""
    print("\n🔍 Testing Analyze Image Tool...")
    
    payload = {
        "image_url": TEST_IMAGE_URL,
        "context": "Interior design analysis for product placement"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MCP_SERVER_URL}/image-assistant/tools/analyze-image",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        analysis = data.get("analysis", {})
                        print(f"✅ Image analysis successful:")
                        print(f"   - Scene type: {analysis.get('scene_type')}")
                        print(f"   - Styles: {analysis.get('styles')}")
                        print(f"   - Objects detected: {len(analysis.get('objects', []))}")
                        print(f"   - Colors: {len(analysis.get('colors', []))}")
                        return True
                    else:
                        print(f"❌ Image analysis failed: {data.get('error')}")
                        return False
                else:
                    text = await response.text()
                    print(f"❌ Image analysis request failed: {response.status} - {text}")
                    return False
    except Exception as e:
        print(f"❌ Failed to test analyze image tool: {e}")
        return False

async def test_visualize_product_tool():
    """Test the visualize product tool."""
    print("\n🎨 Testing Visualize Product Tool...")
    
    payload = {
        "base_image_url": TEST_IMAGE_URL,
        "product_image_url": TEST_PRODUCT_URL,
        "prompt": "Place this decorative vase on the coffee table in this living room"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MCP_SERVER_URL}/image-assistant/tools/visualize-product",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        visualization = data.get("visualization", {})
                        print(f"✅ Product visualization successful:")
                        print(f"   - Render URL: {visualization.get('render_url')}")
                        print(f"   - Processing time: {visualization.get('processing_time_ms')}ms")
                        return True
                    else:
                        print(f"❌ Product visualization failed: {data.get('error')}")
                        return False
                else:
                    text = await response.text()
                    print(f"❌ Product visualization request failed: {response.status} - {text}")
                    return False
    except Exception as e:
        print(f"❌ Failed to test visualize product tool: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing Image Assistant Service Integration with MCP Server")
    print("=" * 80)
    
    tests = [
        ("MCP Server Health", test_mcp_server_health),
        ("Image Assistant Health", test_image_assistant_health),
        ("Tools Schema", test_tools_schema),
        ("Analyze Image Tool", test_analyze_image_tool),
        ("Visualize Product Tool", test_visualize_product_tool),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 80)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Image Assistant Service is properly integrated with MCP Server.")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    print("🚀 Starting Image Assistant MCP Tools Real Integration Test")
    print("Make sure MCP server is port-forwarded on localhost:8081")
    print("Command: kubectl port-forward svc/mcpserver 8081:8080")
    print()
    
    # Give user a chance to cancel if port-forward isn't ready
    try:
        time.sleep(2)
    asyncio.run(main()) 
    except KeyboardInterrupt:
        print("\n⏹️  Test cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Make sure:")
        print("1. MCP server is port-forwarded: kubectl port-forward svc/mcpserver 8081:8080")
        print("2. Dependencies are installed: pip install -r requirements.txt")
        print("3. Image Assistant Service is properly deployed and running")
        sys.exit(1) 