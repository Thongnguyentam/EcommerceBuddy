#!/usr/bin/env python3

"""
Copyright 2024 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
import logging
import asyncio

import grpc
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from genproto import review_pb2, review_pb2_grpc
from database import DatabaseManager, ReviewRepository
from models import ReviewCreate, ReviewUpdate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReviewServicer(review_pb2_grpc.ReviewServiceServicer):
    """gRPC servicer for review operations."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.repository = None
        
    async def _ensure_repository(self):
        """Ensure repository is initialized."""
        if self.repository is None:
            if not self.db_manager.engine:
                await self.db_manager.initialize()
            self.repository = ReviewRepository(self.db_manager)
    
    def _set_error(self, context, code, details):
        """Set error code and details if context is available."""
        if context:
            context.set_code(code)
            context.set_details(details)
    
    def _convert_to_proto_review(self, review_dict: dict) -> review_pb2.Review:
        """Convert database review dict to protobuf Review."""
        created_ts = int(review_dict['created_at'].timestamp()) if review_dict['created_at'] else 0
        updated_ts = int(review_dict['updated_at'].timestamp()) if review_dict['updated_at'] else 0
        
        return review_pb2.Review(
            id=review_dict['id'],
            user_id=review_dict['user_id'],
            product_id=review_dict['product_id'],
            rating=review_dict['rating'],
            review_text=review_dict['review_text'] or "",
            created_at=created_ts,
            updated_at=updated_ts
        )
    
    async def CreateReview(self, request, context):
        """Create a new review."""
        try:
            await self._ensure_repository()
            
            # Validate request
            if not request.user_id or not request.product_id:
                self._set_error(context, grpc.StatusCode.INVALID_ARGUMENT, "user_id and product_id are required")
                return review_pb2.CreateReviewResponse(success=False, message="Missing required fields")
            
            if request.rating < 1 or request.rating > 5:
                self._set_error(context, grpc.StatusCode.INVALID_ARGUMENT, "Rating must be between 1 and 5")
                return review_pb2.CreateReviewResponse(success=False, message="Invalid rating")
            
            # Create review data
            review_data = ReviewCreate(
                user_id=request.user_id,
                product_id=request.product_id,
                rating=request.rating,
                review_text=request.review_text if request.review_text else None
            )
            
            # Create review in database
            review = await self.repository.create_review(review_data)
            
            # Convert to protobuf
            proto_review = self._convert_to_proto_review(review)
            
            return review_pb2.CreateReviewResponse(
                review=proto_review,
                success=True,
                message="Review created successfully"
            )
            
        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.CreateReviewResponse(success=False, message=str(e))
    
    async def GetProductReviews(self, request, context):
        """Get reviews for a product."""
        try:
            await self._ensure_repository()
            
            # Set defaults
            limit = request.limit if request.limit > 0 else 50
            offset = max(0, request.offset)
            
            # Get reviews from database
            reviews = await self.repository.get_product_reviews(
                request.product_id, limit, offset
            )
            
            # Convert to protobuf
            proto_reviews = [self._convert_to_proto_review(review) for review in reviews]
            
            return review_pb2.GetProductReviewsResponse(reviews=proto_reviews)
            
        except Exception as e:
            logger.error(f"Error getting product reviews: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.GetProductReviewsResponse()
    
    async def GetUserReviews(self, request, context):
        """Get reviews by a user."""
        try:
            await self._ensure_repository()
            
            # Set defaults
            limit = request.limit if request.limit > 0 else 50
            offset = max(0, request.offset)
            
            # Get reviews from database
            reviews = await self.repository.get_user_reviews(
                request.user_id, limit, offset
            )
            
            # Convert to protobuf
            proto_reviews = [self._convert_to_proto_review(review) for review in reviews]
            
            return review_pb2.GetUserReviewsResponse(reviews=proto_reviews)
            
        except Exception as e:
            logger.error(f"Error getting user reviews: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.GetUserReviewsResponse()
    
    async def GetReview(self, request, context):
        """Get a specific review by ID."""
        try:
            await self._ensure_repository()
            
            # Get review from database
            review = await self.repository.get_review_by_id(request.review_id)
            
            if review:
                proto_review = self._convert_to_proto_review(review)
                return review_pb2.GetReviewResponse(review=proto_review, found=True)
            else:
                return review_pb2.GetReviewResponse(found=False)
            
        except Exception as e:
            logger.error(f"Error getting review: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.GetReviewResponse(found=False)
    
    async def UpdateReview(self, request, context):
        """Update an existing review."""
        try:
            await self._ensure_repository()
            
            # Validate rating if provided
            if request.rating < 1 or request.rating > 5:
                self._set_error(context, grpc.StatusCode.INVALID_ARGUMENT, "Rating must be between 1 and 5")
                return review_pb2.UpdateReviewResponse(success=False, message="Invalid rating")
            
            # Create update data
            update_data = ReviewUpdate(
                rating=request.rating,
                review_text=request.review_text if request.review_text else None
            )
            
            # Update review in database
            review = await self.repository.update_review(request.review_id, update_data)
            
            if review:
                proto_review = self._convert_to_proto_review(review)
                return review_pb2.UpdateReviewResponse(
                    review=proto_review,
                    success=True,
                    message="Review updated successfully"
                )
            else:
                self._set_error(context, grpc.StatusCode.NOT_FOUND, "Review not found")
                return review_pb2.UpdateReviewResponse(success=False, message="Review not found")
            
        except Exception as e:
            logger.error(f"Error updating review: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.UpdateReviewResponse(success=False, message=str(e))
    
    async def DeleteReview(self, request, context):
        """Delete a review."""
        try:
            await self._ensure_repository()
            
            # Delete review from database
            success = await self.repository.delete_review(request.review_id)
            
            if success:
                return review_pb2.DeleteReviewResponse(
                    success=True,
                    message="Review deleted successfully"
                )
            else:
                self._set_error(context, grpc.StatusCode.NOT_FOUND, "Review not found")
                return review_pb2.DeleteReviewResponse(success=False, message="Review not found")
            
        except Exception as e:
            logger.error(f"Error deleting review: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.DeleteReviewResponse(success=False, message=str(e))
    
    async def GetProductReviewSummary(self, request, context):
        """Get review summary statistics for a product."""
        try:
            await self._ensure_repository()
            
            # Get summary from database
            summary = await self.repository.get_product_review_summary(request.product_id)
            
            # Convert rating distribution to map
            rating_dist = {}
            for rating_str, count in summary['rating_distribution'].items():
                rating_dist[rating_str] = count
            
            return review_pb2.ProductReviewSummary(
                product_id=summary['product_id'],
                total_reviews=summary['total_reviews'],
                average_rating=summary['average_rating'],
                rating_distribution=rating_dist
            )
            
        except Exception as e:
            logger.error(f"Error getting product review summary: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return review_pb2.ProductReviewSummary()
    
    async def Check(self, request, context):
        """Health check endpoint."""
        return review_pb2.HealthCheckResponse(
            status=review_pb2.HealthCheckResponse.ServingStatus.SERVING
        )

def create_grpc_server():
    """Create and configure gRPC server."""
    # Create server with thread pool
    server = grpc.aio.server()
    
    # Add servicer
    review_servicer = ReviewServicer()
    review_pb2_grpc.add_ReviewServiceServicer_to_server(review_servicer, server)
    
    # Add health service
    hs = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(hs, server)
    hs.set("", health_pb2.HealthCheckResponse.SERVING)              # overall
    hs.set("review.ReviewService", health_pb2.HealthCheckResponse.SERVING)  # named
    
    # Configure server address
    port = os.getenv("PORT", "8080")
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    
    logger.info(f"🚀 Starting Review Service gRPC server on {listen_addr}")
    
    return server

async def serve():
    """Start the gRPC server."""
    server = create_grpc_server()
    
    # Start server
    await server.start()
    logger.info("✅ Review Service gRPC server started successfully")
    
    # Wait for server termination
    try:
        await server.wait_for_termination()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await server.stop(grace=5)  # Await this to ensure shutdown is clean

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {str(e)}")
        sys.exit(1) 