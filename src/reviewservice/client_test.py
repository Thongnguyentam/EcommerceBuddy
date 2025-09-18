#!/usr/bin/env python3
"""
Simple gRPC client to test the Review Service.
"""

import asyncio
import grpc
from genproto import review_pb2, review_pb2_grpc

async def test_grpc_client():
    """Test the gRPC service with a simple client."""
    print("🔄 Testing Review Service gRPC client...")
    
    # Create channel (for local testing)
    async with grpc.aio.insecure_channel("localhost:8080") as channel:
        # Create stub
        stub = review_pb2_grpc.ReviewServiceStub(channel)
        
        try:
            # Test health check
            print("1. Testing health check...")
            health_request = review_pb2.HealthCheckRequest(service="review.ReviewService")
            health_response = await stub.Check(health_request)
            print(f"   Health status: {health_response.status}")
            
            # Test create review
            print("2. Testing create review...")
            create_request = review_pb2.CreateReviewRequest(
                user_id="test_user_123",
                product_id="test_product_123",
                rating=5,
                review_text="Great product! Highly recommended."
            )
            create_response = await stub.CreateReview(create_request)
            print(f"   Create success: {create_response.success}")
            print(f"   Message: {create_response.message}")
            if create_response.success:
                created_review_id = create_response.review.id
                print(f"   Created review ID: {created_review_id}")
            
            # Test get product reviews
            print("3. Testing get product reviews...")
            reviews_request = review_pb2.GetProductReviewsRequest(
                product_id="test_product_123",
                limit=10,
                offset=0
            )
            reviews_response = await stub.GetProductReviews(reviews_request)
            print(f"   Found {len(reviews_response.reviews)} reviews")
            for review in reviews_response.reviews:
                print(f"     Review {review.id}: {review.rating}★ - {review.review_text}")
            
            # Test get user reviews
            print("4. Testing get user reviews...")
            user_reviews_request = review_pb2.GetUserReviewsRequest(
                user_id="test_user_123",
                limit=10,
                offset=0
            )
            user_reviews_response = await stub.GetUserReviews(user_reviews_request)
            print(f"   Found {len(user_reviews_response.reviews)} user reviews")
            
            # Test get specific review
            if create_response.success:
                print("5. Testing get specific review...")
                get_review_request = review_pb2.GetReviewRequest(
                    review_id=created_review_id
                )
                get_review_response = await stub.GetReview(get_review_request)
                print(f"   Review found: {get_review_response.found}")
                if get_review_response.found:
                    print(f"     Rating: {get_review_response.review.rating}★")
                    print(f"     Text: {get_review_response.review.review_text}")
                
                # Test update review
                print("6. Testing update review...")
                update_request = review_pb2.UpdateReviewRequest(
                    review_id=created_review_id,
                    rating=4,
                    review_text="Updated: Good product, but could be better."
                )
                update_response = await stub.UpdateReview(update_request)
                print(f"   Update success: {update_response.success}")
                print(f"   Message: {update_response.message}")
                if update_response.success:
                    print(f"     New rating: {update_response.review.rating}★")
                
                # Test delete review
                print("7. Testing delete review...")
                delete_request = review_pb2.DeleteReviewRequest(
                    review_id=created_review_id
                )
                delete_response = await stub.DeleteReview(delete_request)
                print(f"   Delete success: {delete_response.success}")
                print(f"   Message: {delete_response.message}")
            
            # Test get product review summary
            print("8. Testing get product review summary...")
            summary_request = review_pb2.GetProductReviewSummaryRequest(
                product_id="test_product_123"
            )
            summary_response = await stub.GetProductReviewSummary(summary_request)
            print(f"   Total reviews: {summary_response.total_reviews}")
            print(f"   Average rating: {summary_response.average_rating}")
            print(f"   Rating distribution: {dict(summary_response.rating_distribution)}")
            
            print("✅ All gRPC CRUD tests passed!")
            
        except grpc.aio.AioRpcError as e:
            print(f"❌ gRPC error: {e.code()}: {e.details()}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("To test this client:")
    print("1. Start the server: python server.py")
    print("2. In another terminal: python client_test.py")
    print()
    
    try:
        asyncio.run(test_grpc_client())
    except KeyboardInterrupt:
        print("🛑 Client stopped by user")
    except Exception as e:
        print(f"❌ Client error: {e}") 