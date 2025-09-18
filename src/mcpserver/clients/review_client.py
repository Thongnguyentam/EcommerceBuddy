import grpc

# Import from genproto package
from genproto import review_pb2, review_pb2_grpc


class ReviewServiceClient:
    """gRPC client for the Review Service."""
    
    def __init__(self, host: str = "reviewservice:8080"):
        """
        Initialize the Review Service client.
        
        Args:
            host: The gRPC server address (host:port)
        """
        self.host = host
        self.channel = grpc.insecure_channel(host)
        self.stub = review_pb2_grpc.ReviewServiceStub(self.channel)
    
    def create_review(self, user_id: str, product_id: str, rating: int, review_text: str = ""):
        """Create a new review."""
        request = review_pb2.CreateReviewRequest(
            user_id=user_id,
            product_id=product_id,
            rating=rating,
            review_text=review_text
        )
        return self.stub.CreateReview(request)
    
    def get_product_reviews(self, product_id: str, limit: int = 50, offset: int = 0):
        """Get reviews for a specific product."""
        request = review_pb2.GetProductReviewsRequest(
            product_id=product_id,
            limit=limit,
            offset=offset
        )
        return self.stub.GetProductReviews(request)
    
    def get_user_reviews(self, user_id: str, limit: int = 50, offset: int = 0):
        """Get reviews by a specific user."""
        request = review_pb2.GetUserReviewsRequest(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return self.stub.GetUserReviews(request)
    
    def get_review(self, review_id: int):
        """Get a specific review by ID."""
        request = review_pb2.GetReviewRequest(review_id=review_id)
        return self.stub.GetReview(request)
    
    def update_review(self, review_id: int, rating: int, review_text: str = ""):
        """Update an existing review."""
        request = review_pb2.UpdateReviewRequest(
            review_id=review_id,
            rating=rating,
            review_text=review_text
        )
        return self.stub.UpdateReview(request)
    
    def delete_review(self, review_id: int):
        """Delete a review."""
        request = review_pb2.DeleteReviewRequest(review_id=review_id)
        return self.stub.DeleteReview(request)
    
    def get_product_review_summary(self, product_id: str):
        """Get review summary for a product."""
        request = review_pb2.GetProductReviewSummaryRequest(product_id=product_id)
        return self.stub.GetProductReviewSummary(request)
    
    def close(self):
        """Close the gRPC channel."""
        if self.channel:
            self.channel.close() 