from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    """Model for creating a new review."""
    user_id: str = Field(..., description="User ID who wrote the review")
    product_id: str = Field(..., description="Product ID being reviewed")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    review_text: Optional[str] = Field(None, description="Optional review text")

class ReviewUpdate(BaseModel):
    """Model for updating an existing review."""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    review_text: Optional[str] = Field(None, description="Optional review text")

class ReviewResponse(BaseModel):
    """Model for review response data."""
    id: int
    user_id: str
    product_id: str
    rating: int
    review_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductReviewsSummary(BaseModel):
    """Model for product review summary statistics."""
    product_id: str
    total_reviews: int
    average_rating: float
    rating_distribution: dict = Field(description="Count of reviews per rating (1-5)")

class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str
    service: str 