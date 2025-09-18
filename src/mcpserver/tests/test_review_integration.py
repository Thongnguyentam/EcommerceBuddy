#!/usr/bin/env python3
"""
Test script for Review Service MCP integration.

This script tests the review tools and client integration without requiring
a full MCP server setup.
"""

import sys
import os
import asyncio
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.review_tools import ReviewTools
from clients.review_client import ReviewServiceClient
from genproto import review_pb2

def test_review_tools_validation():
    """Test input validation in review tools."""
    print("🧪 Testing Review Tools Validation...")
    
    # Mock client
    mock_client = Mock(spec=ReviewServiceClient)
    tools = ReviewTools(client=mock_client)
    
    # Test create review validation
    result = tools.create_review("", "PRODUCT123", 5, "Great!")
    assert result["status"] == "error"
    assert "User ID cannot be empty" in result["message"]
    print("  ✅ Empty user ID validation works")
    
    result = tools.create_review("USER123", "", 5, "Great!")
    assert result["status"] == "error"
    assert "Product ID cannot be empty" in result["message"]
    print("  ✅ Empty product ID validation works")
    
    result = tools.create_review("USER123", "PRODUCT123", 6, "Great!")
    assert result["status"] == "error"
    assert "Rating must be an integer between 1 and 5" in result["message"]
    print("  ✅ Invalid rating validation works")
    
    result = tools.create_review("USER123", "PRODUCT123", 0, "Great!")
    assert result["status"] == "error"
    assert "Rating must be an integer between 1 and 5" in result["message"]
    print("  ✅ Zero rating validation works")

def test_review_tools_success():
    """Test successful review operations."""
    print("\n🧪 Testing Review Tools Success Cases...")
    
    # Mock client with successful responses
    mock_client = Mock(spec=ReviewServiceClient)
    
    # Mock create review response
    mock_review = Mock()
    mock_review.id = 123
    mock_review.user_id = "USER123"
    mock_review.product_id = "PRODUCT123"
    mock_review.rating = 5
    mock_review.review_text = "Great product!"
    mock_review.created_at = 1640995200  # 2022-01-01
    mock_review.updated_at = 1640995200
    
    mock_response = Mock()
    mock_response.success = True
    mock_response.message = "Review created successfully"
    mock_response.review = mock_review
    
    mock_client.create_review.return_value = mock_response
    
    tools = ReviewTools(client=mock_client)
    
    # Test create review
    result = tools.create_review("USER123", "PRODUCT123", 5, "Great product!")
    assert result["status"] == "ok"
    assert result["review"]["id"] == 123
    assert result["review"]["rating"] == 5
    print("  ✅ Create review success case works")
    
    # Test get product reviews
    mock_reviews_response = Mock()
    mock_reviews_response.reviews = [mock_review]
    mock_client.get_product_reviews.return_value = mock_reviews_response
    
    result = tools.get_product_reviews("PRODUCT123")
    assert result["status"] == "ok"
    assert len(result["reviews"]) == 1
    assert result["reviews"][0]["id"] == 123
    print("  ✅ Get product reviews success case works")
    
    # Test update review
    mock_update_response = Mock()
    mock_update_response.success = True
    mock_update_response.review = mock_review
    mock_client.update_review.return_value = mock_update_response
    
    result = tools.update_review(123, 4, "Updated review")
    assert result["status"] == "ok"
    assert result["review"]["id"] == 123
    print("  ✅ Update review success case works")
    
    # Test delete review
    mock_delete_response = Mock()
    mock_delete_response.success = True
    mock_delete_response.message = "Review deleted successfully"
    mock_client.delete_review.return_value = mock_delete_response
    
    result = tools.delete_review(123)
    assert result["status"] == "ok"
    print("  ✅ Delete review success case works")

def test_review_tools_error_cases():
    """Test error handling in review tools."""
    print("\n🧪 Testing Review Tools Error Cases...")
    
    # Mock client that raises exceptions
    mock_client = Mock(spec=ReviewServiceClient)
    mock_client.create_review.side_effect = Exception("Connection failed")
    
    tools = ReviewTools(client=mock_client)
    
    # Test connection error
    result = tools.create_review("USER123", "PRODUCT123", 5, "Great!")
    assert result["status"] == "error"
    assert "Failed to create review" in result["message"]
    print("  ✅ Connection error handling works")
    
    # Test not found error
    mock_client.update_review.side_effect = Exception("NOT_FOUND: Review not found")
    result = tools.update_review(999, 5, "Updated")
    assert result["status"] == "not_found"
    print("  ✅ Not found error handling works")

def test_format_review():
    """Test review formatting."""
    print("\n🧪 Testing Review Formatting...")
    
    mock_client = Mock(spec=ReviewServiceClient)
    tools = ReviewTools(client=mock_client)
    
    # Mock review object
    mock_review = Mock()
    mock_review.id = 456
    mock_review.user_id = "USER456"
    mock_review.product_id = "PRODUCT456"
    mock_review.rating = 3
    mock_review.review_text = "It's okay"
    mock_review.created_at = 1640995200  # 2022-01-01
    mock_review.updated_at = 1641081600  # 2022-01-02
    
    formatted = tools._format_review(mock_review)
    
    assert formatted["id"] == 456
    assert formatted["user_id"] == "USER456"
    assert formatted["product_id"] == "PRODUCT456"
    assert formatted["rating"] == 3
    assert formatted["review_text"] == "It's okay"
    # Check that timestamps are properly formatted (ISO format)
    assert "T" in formatted["created_at"]
    assert "T" in formatted["updated_at"]
    # Verify the timestamps are different (updated_at should be later)
    assert formatted["created_at"] != formatted["updated_at"]
    print("  ✅ Review formatting works correctly")

def main():
    """Run all tests."""
    print("🚀 Starting Review Service MCP Integration Tests...\n")
    
    try:
        test_review_tools_validation()
        test_review_tools_success()
        test_review_tools_error_cases()
        test_format_review()
        
        print("\n✅ All tests passed! Review Service MCP integration is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 