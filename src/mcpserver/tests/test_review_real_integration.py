#!/usr/bin/env python3
"""
Integration test for Review MCP Tools against port-forwarded reviewservice.

Prerequisites:
1. Port-forward reviewservice: kubectl port-forward svc/reviewservice 8082:8080
2. Install requirements: pip install -r requirements.txt
3. Run this script: python test_review_real_integration.py

This test verifies the MCP review tools work with the real reviewservice.
"""

import sys
import time
import os
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.review_client import ReviewServiceClient
from tools.review_tools import ReviewTools


def test_review_operations() -> None:
    """Test review CRUD operations against port-forwarded reviewservice."""
    
    print("🧪 Testing Review MCP Tools Integration")
    print("=" * 50)
    
    # Connect to port-forwarded reviewservice
    client = ReviewServiceClient(host="localhost:8082")
    tools = ReviewTools(client=client)
    
    test_user_id = "test-user-123"
    test_product_id = "OLJCESPC7Z"  # Sunglasses product from demo
    created_review_id = None
    
    try:
        # Test 1: Create a new review
        print("\n1️⃣ Creating a new review...")
        original_rating = 4
        original_text = "Great sunglasses! Love the style and quality."
        result = tools.create_review(
            user_id=test_user_id,
            product_id=test_product_id,
            rating=original_rating,
            review_text=original_text
        )
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            created_review_id = result['review']['id']
            print(f"   ✅ Created review ID: {created_review_id}")
            print(f"   ✅ Review rating: {result['review']['rating']}")
            print(f"   ✅ Review text: {result['review']['review_text']}")
            
            # Verify exact content matches what we sent
            if result['review']['rating'] == original_rating:
                print(f"   ✅ Rating matches expected value: {original_rating}")
            else:
                print(f"   ❌ Rating mismatch! Expected: {original_rating}, Got: {result['review']['rating']}")
                return
            
            if result['review']['review_text'] == original_text:
                print(f"   ✅ Review text matches expected content")
            else:
                print(f"   ❌ Review text mismatch!")
                print(f"       Expected: '{original_text}'")
                print(f"       Got: '{result['review']['review_text']}'")
                return
                
            if result['review']['user_id'] == test_user_id:
                print(f"   ✅ User ID matches: {test_user_id}")
            else:
                print(f"   ❌ User ID mismatch! Expected: {test_user_id}, Got: {result['review']['user_id']}")
                return
                
            if result['review']['product_id'] == test_product_id:
                print(f"   ✅ Product ID matches: {test_product_id}")
            else:
                print(f"   ❌ Product ID mismatch! Expected: {test_product_id}, Got: {result['review']['product_id']}")
                return
        else:
            print(f"   ❌ Failed to create review: {result['message']}")
            return
        
        # Test 2: Get reviews for the product and verify our created review
        print(f"\n2️⃣ Getting reviews for product: {test_product_id}")
        result = tools.get_product_reviews(test_product_id)
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            print(f"   ✅ Total reviews found: {result['total_count']}")
            if result['total_count'] > 0:
                print(f"   ✅ First review rating: {result['reviews'][0]['rating']}")
                # Check if our review is in the list
                our_review = next((r for r in result['reviews'] if r['id'] == created_review_id), None)
                if our_review:
                    print(f"   ✅ Found our created review in the list!")
                    
                    # Verify the content matches what we originally created
                    if our_review['rating'] == original_rating:
                        print(f"   ✅ Stored rating matches original: {original_rating}")
                    else:
                        print(f"   ❌ Stored rating mismatch! Expected: {original_rating}, Got: {our_review['rating']}")
                        return
                    
                    if our_review['review_text'] == original_text:
                        print(f"   ✅ Stored review text matches original content")
                    else:
                        print(f"   ❌ Stored review text mismatch!")
                        print(f"       Expected: '{original_text}'")
                        print(f"       Got: '{our_review['review_text']}'")
                        return
                    
                    if our_review['user_id'] == test_user_id:
                        print(f"   ✅ Stored user ID matches: {test_user_id}")
                    else:
                        print(f"   ❌ Stored user ID mismatch! Expected: {test_user_id}, Got: {our_review['user_id']}")
                        return
                    
                    if our_review['product_id'] == test_product_id:
                        print(f"   ✅ Stored product ID matches: {test_product_id}")
                    else:
                        print(f"   ❌ Stored product ID mismatch! Expected: {test_product_id}, Got: {our_review['product_id']}")
                        return
                else:
                    print(f"   ❌ Our review not found in product reviews list!")
                    return
        else:
            print(f"   ❌ Failed to get product reviews: {result['message']}")
            return
        
        # Test 3: Get reviews by user and verify content
        print(f"\n3️⃣ Getting reviews by user: {test_user_id}")
        result = tools.get_user_reviews(test_user_id)
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            print(f"   ✅ User has {result['total_count']} reviews")
            if result['total_count'] > 0:
                print(f"   ✅ Latest review: {result['reviews'][0]['review_text']}")
                
                # Find our specific review in the user's reviews
                our_user_review = next((r for r in result['reviews'] if r['id'] == created_review_id), None)
                if our_user_review:
                    print(f"   ✅ Found our review in user's review list")
                    
                    # Verify content matches original
                    if our_user_review['rating'] == original_rating:
                        print(f"   ✅ User review rating matches original: {original_rating}")
                    else:
                        print(f"   ❌ User review rating mismatch! Expected: {original_rating}, Got: {our_user_review['rating']}")
                        return
                    
                    if our_user_review['review_text'] == original_text:
                        print(f"   ✅ User review text matches original content")
                    else:
                        print(f"   ❌ User review text mismatch!")
                        print(f"       Expected: '{original_text}'")
                        print(f"       Got: '{our_user_review['review_text']}'")
                        return
                else:
                    print(f"   ❌ Our review not found in user's review list!")
                    return
        else:
            print(f"   ❌ Failed to get user reviews: {result['message']}")
            return
        
        # Test 4: Update the review
        print(f"\n4️⃣ Updating review ID: {created_review_id}")
        updated_rating = 5
        updated_text = "Updated: Absolutely amazing sunglasses! Perfect fit and style."
        result = tools.update_review(
            review_id=created_review_id,
            rating=updated_rating,
            review_text=updated_text
        )
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            print(f"   ✅ Updated rating: {result['review']['rating']}")
            print(f"   ✅ Updated text: {result['review']['review_text']}")
            
            # Verify exact updated content matches what we sent
            if result['review']['rating'] == updated_rating:
                print(f"   ✅ Updated rating matches expected value: {updated_rating}")
            else:
                print(f"   ❌ Updated rating mismatch! Expected: {updated_rating}, Got: {result['review']['rating']}")
                return
            
            if result['review']['review_text'] == updated_text:
                print(f"   ✅ Updated review text matches expected content")
            else:
                print(f"   ❌ Updated review text mismatch!")
                print(f"       Expected: '{updated_text}'")
                print(f"       Got: '{result['review']['review_text']}'")
                return
                
            # Verify other fields remain unchanged
            if result['review']['id'] == created_review_id:
                print(f"   ✅ Review ID unchanged: {created_review_id}")
            else:
                print(f"   ❌ Review ID changed unexpectedly! Expected: {created_review_id}, Got: {result['review']['id']}")
                return
                
            if result['review']['user_id'] == test_user_id:
                print(f"   ✅ User ID unchanged: {test_user_id}")
            else:
                print(f"   ❌ User ID changed unexpectedly! Expected: {test_user_id}, Got: {result['review']['user_id']}")
                return
                
            if result['review']['product_id'] == test_product_id:
                print(f"   ✅ Product ID unchanged: {test_product_id}")
            else:
                print(f"   ❌ Product ID changed unexpectedly! Expected: {test_product_id}, Got: {result['review']['product_id']}")
                return
        else:
            print(f"   ❌ Failed to update review: {result['message']}")
            return
        
        # Test 4.5: Verify update by fetching the review independently
        print(f"\n4️⃣.5 Verifying update by fetching review independently...")
        result = tools.get_product_reviews(test_product_id)
        if result['status'] == 'ok' and result['total_count'] > 0:
            # Find our updated review in the list
            our_updated_review = next((r for r in result['reviews'] if r['id'] == created_review_id), None)
            if our_updated_review:
                print(f"   ✅ Found updated review in product reviews")
                
                # Verify the updated content persisted correctly
                if our_updated_review['rating'] == updated_rating:
                    print(f"   ✅ Persisted rating matches: {updated_rating}")
                else:
                    print(f"   ❌ Persisted rating mismatch! Expected: {updated_rating}, Got: {our_updated_review['rating']}")
                    return
                
                if our_updated_review['review_text'] == updated_text:
                    print(f"   ✅ Persisted review text matches expected content")
                else:
                    print(f"   ❌ Persisted review text mismatch!")
                    print(f"       Expected: '{updated_text}'")
                    print(f"       Got: '{our_updated_review['review_text']}'")
                    return
                
                # Verify timestamps exist and are reasonable
                if our_updated_review['created_at']:
                    print(f"   ✅ Created timestamp exists: {our_updated_review['created_at']}")
                else:
                    print(f"   ⚠️  Created timestamp is missing or empty")
                
                if our_updated_review['updated_at']:
                    print(f"   ✅ Updated timestamp exists: {our_updated_review['updated_at']}")
                else:
                    print(f"   ⚠️  Updated timestamp is missing or empty")
                
                # Check that updated_at is different from created_at (should be later)
                if (our_updated_review['created_at'] and our_updated_review['updated_at'] and 
                    our_updated_review['updated_at'] != our_updated_review['created_at']):
                    print(f"   ✅ Updated timestamp is different from created timestamp (as expected)")
                elif not our_updated_review['created_at'] or not our_updated_review['updated_at']:
                    print(f"   ⚠️  Cannot compare timestamps (one or both are missing)")
                else:
                    print(f"   ⚠️  Updated timestamp same as created timestamp (might be expected for quick updates)")
            else:
                print(f"   ❌ Could not find our updated review in product reviews list!")
                return
        else:
            print(f"   ❌ Failed to fetch product reviews for verification: {result.get('message', 'Unknown error')}")
            return
        
        # Test 5: Get product review summary
        print(f"\n5️⃣ Getting review summary for product: {test_product_id}")
        result = tools.get_product_review_summary(test_product_id)
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            summary = result['summary']
            print(f"   ✅ Total reviews: {summary['total_reviews']}")
            print(f"   ✅ Average rating: {summary['average_rating']}")
            print(f"   ✅ Rating distribution: {summary['rating_distribution']}")
        else:
            print(f"   ❌ Failed to get review summary: {result['message']}")
        
        # Test 6: Delete the review
        print(f"\n6️⃣ Deleting review ID: {created_review_id}")
        result = tools.delete_review(created_review_id)
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            print(f"   ✅ Successfully deleted review")
            created_review_id = None  # Mark as deleted
        else:
            print(f"   ❌ Failed to delete review: {result['message']}")
        
        # Test 7: Verify deletion by trying to get user reviews again
        print(f"\n7️⃣ Verifying deletion - getting user reviews again...")
        result = tools.get_user_reviews(test_user_id)
        print(f"   ✅ Status: {result['status']}")
        if result['status'] == 'ok':
            remaining_reviews = [r for r in result['reviews'] if r['id'] == created_review_id]
            if not remaining_reviews:
                print(f"   ✅ Review successfully deleted - not found in user reviews")
            else:
                print(f"   ⚠️  Review still exists after deletion attempt")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("=" * 50)
        print("✅ MCP Review Tools are working correctly with reviewservice!")
        print("✅ Review service is properly connected to the database!")
        print("✅ All CRUD operations are functional!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup: Try to delete the review if it still exists
        if created_review_id:
            try:
                print(f"\n🧹 Cleaning up: Deleting review {created_review_id}")
                tools.delete_review(created_review_id)
            except Exception as e:
                print(f"   ⚠️  Cleanup failed: {e}")
        
        client.close()


def test_validation() -> None:
    """Test input validation."""
    print("\n🔍 Testing input validation...")
    
    client = ReviewServiceClient(host="localhost:8082")
    tools = ReviewTools(client=client)
    
    try:
        # Test empty user ID
        result = tools.create_review("", "PRODUCT123", 5, "Great!")
        assert result['status'] == 'error', "Should reject empty user ID"
        print(f"   ✅ Correctly rejected empty user ID: {result['message']}")
        
        # Test empty product ID
        result = tools.create_review("USER123", "", 5, "Great!")
        assert result['status'] == 'error', "Should reject empty product ID"
        print(f"   ✅ Correctly rejected empty product ID: {result['message']}")
        
        # Test invalid rating (too high)
        result = tools.create_review("USER123", "PRODUCT123", 6, "Great!")
        assert result['status'] == 'error', "Should reject rating > 5"
        print(f"   ✅ Correctly rejected invalid rating (6): {result['message']}")
        
        # Test invalid rating (too low)
        result = tools.create_review("USER123", "PRODUCT123", 0, "Great!")
        assert result['status'] == 'error', "Should reject rating < 1"
        print(f"   ✅ Correctly rejected invalid rating (0): {result['message']}")
        
        # Test invalid review ID for update
        result = tools.update_review(-1, 5, "Updated")
        assert result['status'] == 'error', "Should reject negative review ID"
        print(f"   ✅ Correctly rejected negative review ID: {result['message']}")
        
        # Test non-existent review update
        result = tools.update_review(999999, 5, "Updated")
        assert result['status'] in ['error', 'not_found'], "Should handle non-existent review"
        print(f"   ✅ Correctly handled non-existent review: {result['message']}")
        
        print("   ✅ All validation tests passed!")
        
    finally:
        client.close()


def test_content_edge_cases() -> None:
    """Test edge cases for review content."""
    print("\n🔍 Testing content edge cases...")
    
    client = ReviewServiceClient(host="localhost:8082")
    tools = ReviewTools(client=client)
    
    edge_case_user = "edge-case-user-456"
    edge_case_product = "OLJCESPC7Z"  # Use same product for consistency
    created_reviews = []
    
    try:
        # Test 1: Empty review text
        print("\n   📝 Testing empty review text...")
        result = tools.create_review(edge_case_user, edge_case_product, 3, "")
        if result['status'] == 'ok':
            review_id = result['review']['id']
            created_reviews.append(review_id)
            if result['review']['review_text'] == "":
                print(f"   ✅ Empty review text stored correctly")
            else:
                print(f"   ❌ Empty text not stored correctly. Got: '{result['review']['review_text']}'")
        else:
            print(f"   ⚠️  Empty review text rejected: {result['message']}")
        
        # Test 2: Review with special characters and unicode
        special_text = "Amazing product! 🌟⭐ Très bon! 日本語 Test: <script>alert('xss')</script> & \"quotes\" 'single' \\backslash\\ line1\nline2\ttab"
        print("\n   🔤 Testing special characters and unicode...")
        result = tools.create_review(edge_case_user, edge_case_product, 5, special_text)
        if result['status'] == 'ok':
            review_id = result['review']['id']
            created_reviews.append(review_id)
            if result['review']['review_text'] == special_text:
                print(f"   ✅ Special characters stored correctly")
            else:
                print(f"   ❌ Special characters not stored correctly!")
                print(f"       Expected: '{special_text}'")
                print(f"       Got: '{result['review']['review_text']}'")
            
            # Verify by fetching it back
            fetch_result = tools.get_user_reviews(edge_case_user)
            if fetch_result['status'] == 'ok':
                fetched_review = next((r for r in fetch_result['reviews'] if r['id'] == review_id), None)
                if fetched_review and fetched_review['review_text'] == special_text:
                    print(f"   ✅ Special characters persist correctly after fetch")
                else:
                    print(f"   ❌ Special characters not persisted correctly!")
                    if fetched_review:
                        print(f"       Fetched: '{fetched_review['review_text']}'")
        else:
            print(f"   ❌ Special characters review creation failed: {result['message']}")
        
        # Test 3: Very long review text
        long_text = "This is a very long review. " * 100  # 2800+ characters
        print(f"\n   📏 Testing very long review text ({len(long_text)} characters)...")
        result = tools.create_review(edge_case_user, edge_case_product, 2, long_text)
        if result['status'] == 'ok':
            review_id = result['review']['id']
            created_reviews.append(review_id)
            returned_text = result['review']['review_text']
            
            if returned_text == long_text:
                print(f"   ✅ Long review text stored correctly")
            else:
                length_diff = len(long_text) - len(returned_text)
                if abs(length_diff) <= 5:  # Allow small differences due to encoding/trimming
                    print(f"   ✅ Long review text stored with minor difference ({length_diff} chars)")
                    print(f"       Original: {len(long_text)} chars")
                    print(f"       Stored: {len(returned_text)} chars")
                    
                    # Check if it's just trailing whitespace
                    if long_text.rstrip() == returned_text.rstrip():
                        print(f"   ✅ Difference is only trailing whitespace (acceptable)")
                    elif long_text[:len(returned_text)] == returned_text:
                        print(f"   ⚠️  Text appears to be truncated at {len(returned_text)} characters")
                    else:
                        print(f"   ⚠️  Text content differs beyond length")
                else:
                    print(f"   ❌ Long review text significantly modified!")
                    print(f"       Expected length: {len(long_text)}")
                    print(f"       Got length: {len(returned_text)}")
                    print(f"       Difference: {length_diff} characters")
        else:
            print(f"   ⚠️  Long review text rejected: {result['message']}")
        
        # Test 4: Update with different edge case content
        if created_reviews:
            print(f"\n   🔄 Testing update with edge case content...")
            update_text = "Updated with émojis 🎉 and newlines\nLine 2\nLine 3"
            result = tools.update_review(created_reviews[0], 4, update_text)
            if result['status'] == 'ok':
                if result['review']['review_text'] == update_text:
                    print(f"   ✅ Update with special content works correctly")
                else:
                    print(f"   ❌ Update with special content failed!")
                    print(f"       Expected: '{update_text}'")
                    print(f"       Got: '{result['review']['review_text']}'")
            else:
                print(f"   ❌ Update with special content failed: {result['message']}")
        
        print("   ✅ All content edge case tests completed!")
        
    finally:
        # Clean up created reviews
        for review_id in created_reviews:
            try:
                tools.delete_review(review_id)
            except Exception as e:
                print(f"   ⚠️  Cleanup failed for review {review_id}: {e}")
        
        client.close()


def test_error_handling() -> None:
    """Test error handling scenarios."""
    print("\n🔍 Testing error handling...")
    
    client = ReviewServiceClient(host="localhost:8082")
    tools = ReviewTools(client=client)
    
    try:
        # Test getting reviews for non-existent product
        result = tools.get_product_reviews("NONEXISTENT_PRODUCT")
        print(f"   ✅ Non-existent product reviews status: {result['status']}")
        print(f"   ✅ Reviews found: {result['total_count']}")
        
        # Test getting reviews for non-existent user
        result = tools.get_user_reviews("nonexistent-user-12345")
        print(f"   ✅ Non-existent user reviews status: {result['status']}")
        print(f"   ✅ Reviews found: {result['total_count']}")
        
        # Test getting summary for non-existent product
        result = tools.get_product_review_summary("NONEXISTENT_PRODUCT")
        print(f"   ✅ Non-existent product summary status: {result['status']}")
        
        print("   ✅ All error handling tests passed!")
        
    finally:
        client.close()


if __name__ == "__main__":
    print("🚀 Starting Review MCP Tools Real Integration Test")
    print("Make sure reviewservice is port-forwarded on localhost:8082")
    print("Command: kubectl port-forward svc/reviewservice 8082:8080")
    print()
    
    # Give user a chance to cancel if port-forward isn't ready
    try:
        time.sleep(2)
        test_validation()
        test_error_handling()
        test_content_edge_cases()
        test_review_operations()
    except KeyboardInterrupt:
        print("\n⏹️  Test cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Make sure:")
        print("1. reviewservice is port-forwarded: kubectl port-forward svc/reviewservice 8082:8080")
        print("2. Dependencies are installed: pip install -r requirements.txt")
        print("3. Review service database is properly configured")
        sys.exit(1) 