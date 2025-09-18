from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from tools.review_tools import ReviewTools

# Global variable to hold the review tools instance
review_tools: ReviewTools = None

def set_review_tools(tools: ReviewTools):
    """Set the review tools instance."""
    global review_tools
    review_tools = tools

# Create router
router = APIRouter(prefix="/tools/reviews", tags=["review-tools"])

# Request models
class CreateReviewRequest(BaseModel):
    user_id: str
    product_id: str
    rating: int
    review_text: Optional[str] = ""

class UpdateReviewRequest(BaseModel):
    review_id: int
    rating: int
    review_text: Optional[str] = ""

class GetProductReviewsRequest(BaseModel):
    product_id: str
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class GetUserReviewsRequest(BaseModel):
    user_id: str
    limit: Optional[int] = 50
    offset: Optional[int] = 0

class DeleteReviewRequest(BaseModel):
    review_id: int

class GetProductReviewSummaryRequest(BaseModel):
    product_id: str

# Endpoints
@router.post("/create")
async def create_review(request: CreateReviewRequest):
    """Create a new review."""
    if not review_tools:
        raise HTTPException(status_code=500, detail="Review tools not initialized")
    
    result = review_tools.create_review(
        user_id=request.user_id,
        product_id=request.product_id,
        rating=request.rating,
        review_text=request.review_text
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/product")
async def get_product_reviews(request: GetProductReviewsRequest):
    """Get reviews for a specific product."""
    if not review_tools:
        raise HTTPException(status_code=500, detail="Review tools not initialized")
    
    result = review_tools.get_product_reviews(
        product_id=request.product_id,
        limit=request.limit,
        offset=request.offset
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/user")
async def get_user_reviews(request: GetUserReviewsRequest):
    """Get reviews by a specific user."""
    if not review_tools:
        raise HTTPException(status_code=500, detail="Review tools not initialized")
    
    result = review_tools.get_user_reviews(
        user_id=request.user_id,
        limit=request.limit,
        offset=request.offset
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/update")
async def update_review(request: UpdateReviewRequest):
    """Update an existing review."""
    if not review_tools:
        raise HTTPException(status_code=500, detail="Review tools not initialized")
    
    result = review_tools.update_review(
        review_id=request.review_id,
        rating=request.rating,
        review_text=request.review_text
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    elif result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result

@router.post("/delete")
async def delete_review(request: DeleteReviewRequest):
    """Delete a review."""
    if not review_tools:
        raise HTTPException(status_code=500, detail="Review tools not initialized")
    
    result = review_tools.delete_review(review_id=request.review_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    elif result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result

@router.post("/summary")
async def get_product_review_summary(request: GetProductReviewSummaryRequest):
    """Get review summary for a product."""
    if not review_tools:
        raise HTTPException(status_code=500, detail="Review tools not initialized")
    
    result = review_tools.get_product_review_summary(product_id=request.product_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result 