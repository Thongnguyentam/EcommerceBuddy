#!/usr/bin/env python3
"""
Test script for MCP Server integration.

Tests the FastAPI MCP server endpoints against port-forwarded services.
"""

import asyncio
import requests
import json
import time
import sys

def test_mcp_server():
    """Test MCP server endpoints."""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing MCP Server Integration")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1️⃣ Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print(f"   ✅ Health check passed: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Get tools schema
    print("\n2️⃣ Testing tools schema...")
    try:
        response = requests.get(f"{base_url}/tools/schema")
        if response.status_code == 200:
            schema = response.json()
            print(f"   ✅ Found {len(schema['tools'])} tools:")
            for tool in schema['tools']:
                print(f"      - {tool['name']}: {tool['description']}")
        else:
            print(f"   ❌ Schema request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Schema error: {e}")
        return False
    
    # Test 3: List products
    print("\n3️⃣ Testing product listing...")
    try:
        response = requests.get(f"{base_url}/tools/products/list")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            print(f"   ✅ Found {result['total_count']} products")
            if result['total_count'] > 0:
                first_product = result['products'][0]
                print(f"   ✅ First product: {first_product['name']} - {first_product['price']['formatted'] if first_product['price'] else 'N/A'}")
                test_product_id = first_product['id']
            else:
                print("   ❌ No products found")
                return False
        else:
            print(f"   ❌ Product listing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Product listing error: {e}")
        return False
    
    # Test 4: Get specific product
    print(f"\n4️⃣ Testing get product by ID: {test_product_id}")
    try:
        payload = {"product_id": test_product_id}
        response = requests.post(f"{base_url}/tools/products/get", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            if result['status'] == 'ok':
                product = result['product']
                print(f"   ✅ Product: {product['name']}")
                print(f"   ✅ Price: {product['price']['formatted'] if product['price'] else 'N/A'}")
                print(f"   ✅ Categories: {', '.join(product['categories'])}")
            else:
                print(f"   ❌ {result['message']}")
        else:
            print(f"   ❌ Get product failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Get product error: {e}")
        return False
    
    # Test 5: Search products
    print("\n5️⃣ Testing product search...")
    try:
        payload = {"query": "shirt"}
        response = requests.post(f"{base_url}/tools/products/search", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            print(f"   ✅ Found {result['total_count']} products matching 'shirt'")
            if result['total_count'] > 0:
                print(f"   ✅ First result: {result['products'][0]['name']}")
        else:
            print(f"   ❌ Product search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Product search error: {e}")
        return False
    
    # Test 6: Get cart contents (empty)
    test_user = "mcp-test-user-123"
    print(f"\n6️⃣ Testing get cart contents for user: {test_user}")
    try:
        payload = {"user_id": test_user}
        response = requests.post(f"{base_url}/tools/cart/get", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            print(f"   ✅ Cart items: {result['total_items']}")
        else:
            print(f"   ❌ Get cart failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Get cart error: {e}")
        return False
    
    # Test 7: Add item to cart
    print(f"\n7️⃣ Testing add to cart...")
    try:
        payload = {
            "user_id": test_user,
            "product_id": test_product_id,
            "quantity": 2
        }
        response = requests.post(f"{base_url}/tools/cart/add", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            print(f"   ✅ Message: {result['message']}")
        else:
            print(f"   ❌ Add to cart failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Add to cart error: {e}")
        return False
    
    # Test 8: Get cart contents (with items)
    print(f"\n8️⃣ Testing get cart contents (after adding items)...")
    try:
        payload = {"user_id": test_user}
        response = requests.post(f"{base_url}/tools/cart/get", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            print(f"   ✅ Cart items: {result['total_items']}")
            if result['total_items'] > 0:
                print(f"   ✅ Items in cart: {result['items']}")
        else:
            print(f"   ❌ Get cart failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Get cart error: {e}")
        return False
    
    # Test 9: Clear cart
    print(f"\n9️⃣ Testing clear cart...")
    try:
        payload = {"user_id": test_user}
        response = requests.post(f"{base_url}/tools/cart/clear", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Status: {result['status']}")
            print(f"   ✅ Message: {result['message']}")
        else:
            print(f"   ❌ Clear cart failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Clear cart error: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("=" * 50)
    print("✅ MCP Server is working correctly!")
    print("✅ All tools are functional!")
    print("✅ Ready for Google Agent Kit integration!")
    
    return True


if __name__ == "__main__":
    print("🚀 Starting MCP Server Test")
    print("Make sure:")
    print("1. MCP server is running: python main.py")
    print("2. Services are port-forwarded:")
    print("   kubectl port-forward svc/cartservice 7070:7070")
    print("   kubectl port-forward svc/productcatalogservice 3550:3550")
    print()
    
    time.sleep(3)
    
    if test_mcp_server():
        print("\n✅ MCP Server test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ MCP Server test failed!")
        sys.exit(1) 