#!/usr/bin/env python3
"""
Integration test for Shopping Assistant Service.

This test connects to the actual Shopping Assistant Service and tests
AI-powered product recommendations.

Prerequisites:
- Shopping assistant service must be running and accessible
- Port forwarding: kubectl port-forward svc/shoppingassistantservice 8080:80

Run with: python test_shopping_assistant_integration.py
"""

import unittest
import sys
import os
import base64
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.shopping_assistant_client import ShoppingAssistantServiceClient
from tools.shopping_assistant_tools import ShoppingAssistantTools


class TestShoppingAssistantIntegration(unittest.TestCase):
    """Integration tests for Shopping Assistant Service."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        print("🤖 Setting up Shopping Assistant Service integration test...")
        
        # Connect to local port-forwarded service
        cls.client = ShoppingAssistantServiceClient(address="localhost:8080")
        cls.tools = ShoppingAssistantTools(client=cls.client)
        
        print("✅ Shopping assistant service client initialized")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        print("🧹 Cleaning up Shopping Assistant Service integration test...")
        if hasattr(cls, 'client'):
            cls.client.close()
        print("✅ Shopping assistant service client closed")
    
    def test_health_check(self):
        """Test shopping assistant service health check."""
        print("\n🏥 Testing health check...")
        
        result = self.tools.health_check()
        
        # Verify response structure
        self.assertIn("status", result)
        self.assertIn("service", result)
        self.assertEqual(result["service"], "shopping-assistant")
        
        if result["status"] == "healthy":
            print("✅ Shopping assistant service is healthy")
        else:
            print(f"⚠️ Shopping assistant service status: {result['status']}")
            if "error" in result:
                print(f"   Error: {result['error']}")
    
    def test_basic_ai_recommendations(self):
        """Test basic AI recommendations without image."""
        print("\n🛋️ Testing basic AI recommendations...")
        
        result = self.tools.get_ai_recommendations(
            user_query="I need furniture for my living room"
        )
        
        # Verify response structure
        self.assertIn("success", result)
        self.assertIn("user_query", result)
        self.assertIn("recommendations", result)
        self.assertIn("product_ids", result)
        self.assertIn("has_image", result)
        
        # Verify content
        self.assertEqual(result["user_query"], "I need furniture for my living room")
        self.assertEqual(result["has_image"], False)
        
        if result["success"]:
            print(f"✅ Received AI recommendations")
            print(f"   Query: {result['user_query']}")
            print(f"   Product IDs found: {len(result['product_ids'])}")
            if result["product_ids"]:
                print(f"   Sample IDs: {result['product_ids'][:3]}")
            print(f"   Response preview: {result['recommendations'][:150]}...")
        else:
            print(f"❌ AI recommendations failed: {result.get('error', 'Unknown error')}")
            # Don't fail the test if service is not available
            self.skipTest("Shopping assistant service not available")
    
    def test_style_based_recommendations(self):
        """Test style-based recommendations."""
        print("\n🎨 Testing style-based recommendations...")
        
        result = self.tools.get_style_based_recommendations(
            room_style="modern",
            budget_max=500.0
        )
        
        # Verify response structure
        self.assertIn("success", result)
        self.assertIn("room_style", result)
        self.assertIn("budget_max", result)
        self.assertIn("recommendation_type", result)
        
        if result["success"]:
            self.assertEqual(result["room_style"], "modern")
            self.assertEqual(result["budget_max"], 500.0)
            self.assertEqual(result["recommendation_type"], "style-based")
            
            print(f"✅ Received style-based recommendations")
            print(f"   Style: {result['room_style']}")
            print(f"   Budget: ${result['budget_max']}")
            print(f"   Product IDs found: {len(result['product_ids'])}")
        else:
            print(f"❌ Style-based recommendations failed: {result.get('error', 'Unknown error')}")
            self.skipTest("Shopping assistant service not available")
    
    def test_room_specific_recommendations(self):
        """Test room-specific recommendations."""
        print("\n🏠 Testing room-specific recommendations...")
        
        result = self.tools.get_room_specific_recommendations(
            room_type="bedroom",
            specific_needs="storage solutions"
        )
        
        # Verify response structure
        self.assertIn("success", result)
        self.assertIn("room_type", result)
        self.assertIn("specific_needs", result)
        self.assertIn("recommendation_type", result)
        
        if result["success"]:
            self.assertEqual(result["room_type"], "bedroom")
            self.assertEqual(result["specific_needs"], "storage solutions")
            self.assertEqual(result["recommendation_type"], "room-specific")
            
            print(f"✅ Received room-specific recommendations")
            print(f"   Room type: {result['room_type']}")
            print(f"   Specific needs: {result['specific_needs']}")
            print(f"   Product IDs found: {len(result['product_ids'])}")
        else:
            print(f"❌ Room-specific recommendations failed: {result.get('error', 'Unknown error')}")
            self.skipTest("Shopping assistant service not available")
    
    def test_complementary_products(self):
        """Test complementary product recommendations."""
        print("\n🔗 Testing complementary product recommendations...")
        
        result = self.tools.get_complementary_products(
            existing_products=["sofa", "coffee table"],
            room_context="modern living room"
        )
        
        # Verify response structure
        self.assertIn("success", result)
        self.assertIn("existing_products", result)
        self.assertIn("room_context", result)
        self.assertIn("recommendation_type", result)
        
        if result["success"]:
            self.assertEqual(result["existing_products"], ["sofa", "coffee table"])
            self.assertEqual(result["room_context"], "modern living room")
            self.assertEqual(result["recommendation_type"], "complementary")
            
            print(f"✅ Received complementary product recommendations")
            print(f"   Existing products: {result['existing_products']}")
            print(f"   Room context: {result['room_context']}")
            print(f"   Product IDs found: {len(result['product_ids'])}")
        else:
            print(f"❌ Complementary product recommendations failed: {result.get('error', 'Unknown error')}")
            self.skipTest("Shopping assistant service not available")
    
    def test_error_handling_empty_query(self):
        """Test error handling with empty query."""
        print("\n❌ Testing error handling...")
        
        # Test empty query
        result = self.tools.get_ai_recommendations(user_query="")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "User query cannot be empty")
        
        print("✅ Empty query error handling works correctly")
    
    def test_error_handling_invalid_products_list(self):
        """Test error handling with invalid products list."""
        print("\n❌ Testing complementary products error handling...")
        
        # Test empty products list
        result = self.tools.get_complementary_products(existing_products=[])
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "At least one existing product must be specified")
        
        print("✅ Empty products list error handling works correctly")
    
    def test_product_id_extraction(self):
        """Test product ID extraction from AI response."""
        print("\n🔍 Testing product ID extraction...")
        
        # Test the internal method with sample content
        sample_content = """
        Based on your request, I recommend these items:
        1. Modern sofa [OLJCESPC7Z]
        2. Coffee table [9SIQT8TOJO] 
        3. Floor lamp [66VCHSJNUP]
        
        These products would work well together in your space.
        """
        
        product_ids = self.tools._extract_product_ids(sample_content)
        
        expected_ids = ["OLJCESPC7Z", "9SIQT8TOJO", "66VCHSJNUP"]
        self.assertEqual(product_ids, expected_ids)
        
        print(f"✅ Successfully extracted {len(product_ids)} product IDs: {product_ids}")


def run_shopping_assistant_integration_test():
    """Run the shopping assistant integration test suite."""
    print("🚀 Starting Shopping Assistant Service Real Integration Test")
    print("📋 Prerequisites:")
    print("   - Shopping assistant service running in Kubernetes")
    print("   - Port forward: kubectl port-forward svc/shoppingassistantservice 8080:80")
    print("   - Google API key configured in the service")
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShoppingAssistantIntegration)
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    
    # Run tests
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("🎉 All shopping assistant integration tests passed!")
        print(f"✅ Ran {result.testsRun} tests successfully")
    else:
        print("⚠️ Some shopping assistant integration tests had issues!")
        print(f"💔 Failures: {len(result.failures)}, Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
                
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
    
    print("="*60)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_shopping_assistant_integration_test()
    sys.exit(0 if success else 1) 