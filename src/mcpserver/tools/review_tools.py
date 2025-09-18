from typing import Dict, Any, List
from clients.review_client import ReviewServiceClient
import datetime


class ReviewTools:
    """
    High-level tools for review service operations.
    
    These methods provide business logic, validation, and user-friendly responses
    for MCP (Model Context Protocol) integration.
    """
    
    def __init__(self, client: ReviewServiceClient | None = None) -> None:
        self._client = client or ReviewServiceClient()
    
    def create_review(self, user_id: str, product_id: str, rating: int, review_text: str = "") -> Dict[str, Any]:
        """
        Create a new review for a product.
        
        Args:
            user_id: ID of the user creating the review
            product_id: ID of the product being reviewed
            rating: Rating from 1-5 stars
            review_text: Optional review text/comment
            
        Returns:
            Dict with status and review details
        """
        # Validation
        if not user_id or not user_id.strip():
            return {
                "status": "error",
                "message": "User ID cannot be empty",
                "review": None
            }
        
        if not product_id or not product_id.strip():
            return {
                "status": "error", 
                "message": "Product ID cannot be empty",
                "review": None
            }
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return {
                "status": "error",
                "message": "Rating must be an integer between 1 and 5",
                "review": None
            }
        
        try:
            response = self._client.create_review(
                user_id=user_id.strip(),
                product_id=product_id.strip(), 
                rating=rating,
                review_text=review_text.strip() if review_text else ""
            )
            
            if response.success:
                review_data = self._format_review(response.review)
                return {
                    "status": "ok",
                    "review": review_data,
                    "message": f"Review created successfully for product '{product_id}'"
                }
            else:
                return {
                    "status": "error",
                    "message": response.message,
                    "review": None
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create review: {str(e)}",
                "review": None
            }
    
    def get_product_reviews(self, product_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get all reviews for a specific product.
        
        Args:
            product_id: ID of the product
            limit: Maximum number of reviews to return
            offset: Number of reviews to skip
            
        Returns:
            Dict with status, reviews list, and metadata
        """
        if not product_id or not product_id.strip():
            return {
                "status": "error",
                "message": "Product ID cannot be empty",
                "reviews": [],
                "total_count": 0
            }
        
        try:
            response = self._client.get_product_reviews(
                product_id=product_id.strip(),
                limit=max(1, min(100, limit)),  # Limit between 1-100
                offset=max(0, offset)
            )
            
            reviews = [self._format_review(review) for review in response.reviews]
            
            return {
                "status": "ok",
                "reviews": reviews,
                "total_count": len(reviews),
                "product_id": product_id.strip(),
                "message": f"Retrieved {len(reviews)} reviews for product '{product_id}'"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get product reviews: {str(e)}",
                "reviews": [],
                "total_count": 0,
                "product_id": product_id.strip()
            }
    
    def get_user_reviews(self, user_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get all reviews by a specific user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of reviews to return
            offset: Number of reviews to skip
            
        Returns:
            Dict with status, reviews list, and metadata
        """
        if not user_id or not user_id.strip():
            return {
                "status": "error",
                "message": "User ID cannot be empty", 
                "reviews": [],
                "total_count": 0
            }
        
        try:
            response = self._client.get_user_reviews(
                user_id=user_id.strip(),
                limit=max(1, min(100, limit)),
                offset=max(0, offset)
            )
            
            reviews = [self._format_review(review) for review in response.reviews]
            
            return {
                "status": "ok",
                "reviews": reviews,
                "total_count": len(reviews),
                "user_id": user_id.strip(),
                "message": f"Retrieved {len(reviews)} reviews by user '{user_id}'"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get user reviews: {str(e)}",
                "reviews": [],
                "total_count": 0,
                "user_id": user_id.strip()
            }
    
    def update_review(self, review_id: int, rating: int, review_text: str = "") -> Dict[str, Any]:
        """
        Update an existing review.
        
        Args:
            review_id: ID of the review to update
            rating: New rating from 1-5 stars
            review_text: New review text
            
        Returns:
            Dict with status and updated review details
        """
        if not isinstance(review_id, int) or review_id <= 0:
            return {
                "status": "error",
                "message": "Review ID must be a positive integer",
                "review": None
            }
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return {
                "status": "error",
                "message": "Rating must be an integer between 1 and 5",
                "review": None
            }
        
        try:
            response = self._client.update_review(
                review_id=review_id,
                rating=rating,
                review_text=review_text.strip() if review_text else ""
            )
            
            if response.success:
                review_data = self._format_review(response.review)
                return {
                    "status": "ok",
                    "review": review_data,
                    "message": f"Review {review_id} updated successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": response.message,
                    "review": None
                }
                
        except Exception as e:
            if "NOT_FOUND" in str(e) or "not found" in str(e).lower():
                return {
                    "status": "not_found",
                    "message": f"Review with ID {review_id} not found",
                    "review": None
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update review: {str(e)}",
                    "review": None
                }
    
    def delete_review(self, review_id: int) -> Dict[str, Any]:
        """
        Delete a review.
        
        Args:
            review_id: ID of the review to delete
            
        Returns:
            Dict with status and message
        """
        if not isinstance(review_id, int) or review_id <= 0:
            return {
                "status": "error",
                "message": "Review ID must be a positive integer"
            }
        
        try:
            response = self._client.delete_review(review_id=review_id)
            
            if response.success:
                return {
                    "status": "ok",
                    "message": f"Review {review_id} deleted successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": response.message
                }
                
        except Exception as e:
            if "NOT_FOUND" in str(e) or "not found" in str(e).lower():
                return {
                    "status": "not_found",
                    "message": f"Review with ID {review_id} not found"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to delete review: {str(e)}"
                }
    
    def get_product_review_summary(self, product_id: str) -> Dict[str, Any]:
        """
        Get review summary statistics for a product.
        
        Args:
            product_id: ID of the product
            
        Returns:
            Dict with status and summary statistics
        """
        if not product_id or not product_id.strip():
            return {
                "status": "error",
                "message": "Product ID cannot be empty",
                "summary": None
            }
        
        try:
            response = self._client.get_product_review_summary(product_id=product_id.strip())
            
            summary = {
                "product_id": response.product_id,
                "total_reviews": response.total_reviews,
                "average_rating": round(response.average_rating, 2),
                "rating_distribution": dict(response.rating_distribution)
            }
            
            return {
                "status": "ok",
                "summary": summary,
                "message": f"Retrieved review summary for product '{product_id}'"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get review summary: {str(e)}",
                "summary": None
            }
    
    def _format_review(self, review) -> Dict[str, Any]:
        """
        Convert a protobuf Review to a user-friendly dict.
        
        Args:
            review: The protobuf Review object
            
        Returns:
            Dict representation of the review
        """
        # Format timestamps
        created_at = None
        updated_at = None
        
        if review.created_at > 0:
            created_at = datetime.datetime.fromtimestamp(review.created_at).isoformat()
        
        if review.updated_at > 0:
            updated_at = datetime.datetime.fromtimestamp(review.updated_at).isoformat()
        
        return {
            "id": review.id,
            "user_id": review.user_id,
            "product_id": review.product_id,
            "rating": review.rating,
            "review_text": review.review_text,
            "created_at": created_at,
            "updated_at": updated_at
        } 