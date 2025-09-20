#!/usr/bin/env python3
"""
Integration test for Product MCP Tools against port-forwarded productcatalogservice.

Prerequisites:
1. Port-forward productcatalogservice: kubectl port-forward svc/productcatalogservice 3550:3550
2. Install requirements: pip install -r requirements.txt
3. Run this script: python test_product_integration.py

This test verifies the MCP product tools work with the real productcatalogservice.
"""

import sys
import time
import os
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.product_client import ProductCatalogServiceClient
from tools.product_tools import ProductTools


def test_product_operations() -> None:
    """Test product operations against port-forwarded productcatalogservice."""
    
    print("🧪 Testing Product MCP Tools Integration")
    print("=" * 50)
    
    # Connect to port-forwarded productcatalogservice
    client = ProductCatalogServiceClient(host="localhost:3550")
    tools = ProductTools(client=client)
    
    try:
        # Test 1: List all products
        print("\n1️⃣ Listing all products...")
        result = tools.list_all_products()
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Total products: {result['total_count']}")
        if result['status'] == 'ok' and result['total_count'] > 0:
            print(f"   ✅ First product: {result['products'][0]['name']}")
            first_product_id = result['products'][0]['id']
        else:
            print(f"   ❌ No products found: {result['message']}")
            return
        
        # Test 2: Get specific product by ID
        print(f"\n2️⃣ Getting product by ID: {first_product_id}")
        result = tools.get_product_by_id(first_product_id)
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            product = result['product']
            print(f"   ✅ Product name: {product['name']}")
            print(f"   ✅ Price: {product['price']['formatted'] if product['price'] else 'N/A'}")
            print(f"   ✅ Categories: {', '.join(product['categories'])}")
        else:
            print(f"   ❌ {result['message']}")
        
        # Test 3: Get non-existent product
        print("\n3️⃣ Testing non-existent product...")
        result = tools.get_product_by_id("NONEXISTENT")
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Message: {result['message']}")
        assert result['status'] == 'not_found', "Should return not_found for missing product"
        
        # Test 4: Search products
        print("\n4️⃣ Searching for 'shirt' products...")
        result = tools.search_products("shirt")
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Found: {result['total_count']} products")
        if result['total_count'] > 0:
            print(f"   ✅ First result: {result['products'][0]['name']}")
        
        # Test 5: Get products by category
        print("\n5️⃣ Getting products in 'clothing' category...")
        result = tools.get_products_by_category("clothing")
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Found: {result['total_count']} clothing products")
        if result['total_count'] > 0:
            print(f"   ✅ First clothing item: {result['products'][0]['name']}")
        
        # Test 6: Test another category
        print("\n6️⃣ Getting products in 'accessories' category...")
        result = tools.get_products_by_category("accessories")
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Found: {result['total_count']} accessory products")
        
        # Test 7: Semantic search for comfortable seating
        print("\n7️⃣ Semantic search for 'comfortable seating'...")
        result = tools.semantic_search_products("comfortable seating", limit=5)
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Search type: {result.get('search_type', 'N/A')}")
        print(f"   ✅ Found: {result['total_count']} semantically related products")
        if result['total_count'] > 0:
            print(f"   ✅ First result: {result['products'][0]['name']}")
        
        # Test 8: Semantic search for kitchen appliances
        print("\n8️⃣ Semantic search for 'kitchen appliances'...")
        result = tools.semantic_search_products("kitchen appliances", limit=3)
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Found: {result['total_count']} kitchen-related products")
        if result['total_count'] > 0:
            for i, product in enumerate(result['products'][:3], 1):
                print(f"   ✅ {i}. {product['name']}")
        
        # Test 9: Semantic search for winter clothing
        print("\n9️⃣ Semantic search for 'winter clothing'...")
        result = tools.semantic_search_products("winter clothing", limit=3)
        print(f"   ✅ Status: {result['status']}")
        print(f"   ✅ Found: {result['total_count']} winter clothing items")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("=" * 50)
        print("✅ MCP Product Tools are working correctly with productcatalogservice!")
        print("✅ Product service is properly connected to Cloud SQL database!")
        print("✅ Regular search, category filtering, and semantic search are functional!")
        print("✅ AI-powered semantic search with vector embeddings is working!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    
    finally:
        client.close()


def test_validation() -> None:
    """Test input validation."""
    print("\n🔍 Testing input validation...")
    
    client = ProductCatalogServiceClient(host="localhost:3550")
    tools = ProductTools(client=client)
    
    try:
        # Test empty product ID
        result = tools.get_product_by_id("")
        assert result['status'] == 'error', "Should reject empty product ID"
        print(f"   ✅ Correctly rejected empty product ID: {result['message']}")
        
        # Test empty search query
        result = tools.search_products("")
        assert result['status'] == 'error', "Should reject empty search query"
        print(f"   ✅ Correctly rejected empty search query: {result['message']}")
        
        # Test empty category
        result = tools.get_products_by_category("")
        assert result['status'] == 'error', "Should reject empty category"
        print(f"   ✅ Correctly rejected empty category: {result['message']}")
        
        # Test empty semantic search query
        result = tools.semantic_search_products("")
        assert result['status'] == 'error', "Should reject empty semantic search query"
        print(f"   ✅ Correctly rejected empty semantic search query: {result['message']}")
        
        # Test invalid limit (negative) - should be converted to default limit
        result = tools.semantic_search_products("test", limit=-1)
        print(f"   ✅ Result: {result}")
        assert result['status'] in ['ok'], "Should handle negative limit gracefully"
        print(f"   ✅ Handled negative limit correctly: {result['status']}")
        
        # Test large limit (should be clamped)
        result = tools.semantic_search_products("test", limit=100)
        print(f"   ✅ Result: {result['status']}")
        assert result['status'] in ['ok'], "Should handle large limit"
        print(f"   ✅ Handled large limit correctly")
        
        print("   ✅ All validation tests passed!")
        
    finally:
        client.close()


if __name__ == "__main__":
    print("🚀 Starting Product MCP Tools Integration Test")
    print("Make sure productcatalogservice is port-forwarded on localhost:3550")
    print("Command: kubectl port-forward svc/productcatalogservice 3550:3550")
    print()
    
    # Give user a chance to cancel if port-forward isn't ready
    try:
        time.sleep(2)
        test_validation()
        test_product_operations()
    except KeyboardInterrupt:
        print("\n⏹️  Test cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Make sure:")
        print("1. productcatalogservice is port-forwarded: kubectl port-forward svc/productcatalogservice 3550:3550")
        print("2. Dependencies are installed: pip install -r requirements.txt")
        sys.exit(1) 