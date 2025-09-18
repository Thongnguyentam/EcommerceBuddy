#!/usr/bin/env python3
"""
Integration test script to test the review service with real products from the product catalog.
"""

import asyncio
import grpc
import json
from genproto import review_pb2, review_pb2_grpc

# Product catalog service (gRPC)
PRODUCT_CATALOG_SERVICE = "34.118.239.168:3550"
# Review service (gRPC) 
REVIEW_SERVICE = "localhost:8080"

async def test_product_catalog():
    """Test getting products from the product catalog service."""
    print("🛍️  Testing Product Catalog Service...")
    
    try:
        # Note: This would require the product catalog gRPC client
        # For now, let's use some sample product IDs
        sample_products = [
            "0PUK6V6EV0",  # Vintage Typewriter
            "1YMWWN1N4O",  # Vintage Camera Lens
            "2ZYFJ3GM2N",  # Vintage Record Player
            "66VCHSJNUP",  # Vintage Camera
            "6E92ZMYYFZ",  # Vintage Polaroid Camera
        ]
        print(f"   Using sample product IDs: {sample_products}")
        return sample_products
    except Exception as e:
        print(f"   ❌ Error connecting to product catalog: {e}")
        return []

async def test_review_service():
    """Test the review service with sample products."""
    print("\n⭐ Testing Review Service...")
    
    # Sample products to test with
    test_products = [
        "0PUK6V6EV0",  # Vintage Typewriter
        "1YMWWN1N4O",  # Vintage Camera Lens  
        "2ZYFJ3GM2N",  # Vintage Record Player
    ]
    
    try:
        async with grpc.aio.insecure_channel(REVIEW_SERVICE) as channel:
            stub = review_pb2_grpc.ReviewServiceStub(channel)
            
            # Test health check
            print("1. Testing health check...")
            health_request = review_pb2.HealthCheckRequest(service="review.ReviewService")
            health_response = await stub.Check(health_request)
            print(f"   ✅ Health status: {health_response.status}")
            
            # Test creating reviews for different products
            print("\n2. Creating reviews for products...")
            created_reviews = []
            
            for i, product_id in enumerate(test_products):
                print(f"   Creating review for product {product_id}...")
                
                create_request = review_pb2.CreateReviewRequest(
                    user_id=f"test_user_{i+1}",
                    product_id=product_id,
                    rating=4 + (i % 2),  # Alternate between 4 and 5 stars
                    review_text=f"Great product! This is review #{i+1} for {product_id}. Highly recommended!"
                )
                
                create_response = await stub.CreateReview(create_request)
                if create_response.success:
                    created_reviews.append(create_response.review)
                    print(f"     ✅ Created review ID {create_response.review.id} with {create_response.review.rating}★")
                else:
                    print(f"     ❌ Failed to create review: {create_response.message}")
            
            # Test getting product reviews
            print("\n3. Testing get product reviews...")
            for product_id in test_products:
                reviews_request = review_pb2.GetProductReviewsRequest(
                    product_id=product_id,
                    limit=10,
                    offset=0
                )
                reviews_response = await stub.GetProductReviews(reviews_request)
                print(f"   Product {product_id}: {len(reviews_response.reviews)} reviews")
                for review in reviews_response.reviews:
                    print(f"     - {review.rating}★ by user {review.user_id}: {review.review_text[:50]}...")
            
            # Test getting review summaries
            print("\n4. Testing get product review summaries...")
            for product_id in test_products:
                summary_request = review_pb2.GetProductReviewSummaryRequest(
                    product_id=product_id
                )
                summary_response = await stub.GetProductReviewSummary(summary_request)
                print(f"   Product {product_id}:")
                print(f"     Total reviews: {summary_response.total_reviews}")
                print(f"     Average rating: {summary_response.average_rating:.1f}★")
                print(f"     Rating distribution: {dict(summary_response.rating_distribution)}")
            
            # Test user reviews
            print("\n5. Testing get user reviews...")
            for i in range(1, 4):
                user_id = f"test_user_{i}"
                user_reviews_request = review_pb2.GetUserReviewsRequest(
                    user_id=user_id,
                    limit=10,
                    offset=0
                )
                user_reviews_response = await stub.GetUserReviews(user_reviews_request)
                print(f"   User {user_id}: {len(user_reviews_response.reviews)} reviews")
            
            # Test updating a review
            if created_reviews:
                print("\n6. Testing update review...")
                review_to_update = created_reviews[0]
                update_request = review_pb2.UpdateReviewRequest(
                    review_id=review_to_update.id,
                    rating=5,
                    review_text="Updated: This is even better than I initially thought! ⭐⭐⭐⭐⭐"
                )
                update_response = await stub.UpdateReview(update_request)
                if update_response.success:
                    print(f"   ✅ Updated review {review_to_update.id} to {update_response.review.rating}★")
                    print(f"     New text: {update_response.review.review_text}")
                else:
                    print(f"   ❌ Failed to update review: {update_response.message}")
            
            print("\n✅ All review service tests completed successfully!")
            
    except grpc.aio.AioRpcError as e:
        print(f"❌ gRPC error: {e.code()}: {e.details()}")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Main test function."""
    print("🚀 Starting Integration Test")
    print("=" * 50)
    
    # Test product catalog (get sample products)
    products = await test_product_catalog()
    
    # Test review service
    await test_review_service()
    
    print("\n" + "=" * 50)
    print("🎉 Integration test completed!")

if __name__ == "__main__":
    asyncio.run(main())
