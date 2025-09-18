import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, case, and_
from sqlalchemy.exc import IntegrityError

from .models import ProductReview
from .connection import DatabaseManager
from models import ReviewCreate, ReviewUpdate

logger = logging.getLogger(__name__)

class ReviewRepository:
    """Repository for review operations using SQLAlchemy ORM."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create_review(self, review: ReviewCreate) -> Dict[str, Any]:
        """Create a new review and return the review data."""
        async with self.db_manager.get_session() as session:
            db_review = ProductReview(
                user_id=review.user_id,
                product_id=review.product_id,
                rating=review.rating,
                review_text=review.review_text
            )
            
            try:
                session.add(db_review)
                await session.flush()  # Flush to get the ID
                await session.refresh(db_review)  # Refresh to get all fields
                return db_review.to_dict()
            except IntegrityError as e:
                if "UNIQUE constraint failed" in str(e) or "unique_user_product_review" in str(e):
                    raise ValueError("User has already reviewed this product")
                raise
    
    async def get_review_by_id(self, review_id: int) -> Optional[Dict[str, Any]]:
        """Get a review by its ID."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(ProductReview).where(ProductReview.id == review_id)
            )
            review = result.scalar_one_or_none()
            return review.to_dict() if review else None
    
    async def get_user_product_review(self, user_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's review for a specific product."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(ProductReview).where(
                    and_(ProductReview.user_id == user_id, ProductReview.product_id == product_id)
                )
            )
            review = result.scalar_one_or_none()
            return review.to_dict() if review else None
    
    async def get_product_reviews(self, product_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all reviews for a product with pagination."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(ProductReview)
                .where(ProductReview.product_id == product_id)
                .order_by(ProductReview.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            reviews = result.scalars().all()
            return [review.to_dict() for review in reviews]
    
    async def get_user_reviews(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all reviews by a user with pagination."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(ProductReview)
                .where(ProductReview.user_id == user_id)
                .order_by(ProductReview.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            reviews = result.scalars().all()
            return [review.to_dict() for review in reviews]
    
    async def get_product_review_summary(self, product_id: str) -> Dict[str, Any]:
        """Get review summary statistics for a product."""
        async with self.db_manager.get_session() as session:
            # Get summary statistics
            result = await session.execute(
                select(
                    func.count(ProductReview.id).label('total_reviews'),
                    func.avg(ProductReview.rating).label('average_rating'),
                    func.sum(case((ProductReview.rating == 1, 1), else_=0)).label('rating_1'),
                    func.sum(case((ProductReview.rating == 2, 1), else_=0)).label('rating_2'),
                    func.sum(case((ProductReview.rating == 3, 1), else_=0)).label('rating_3'),
                    func.sum(case((ProductReview.rating == 4, 1), else_=0)).label('rating_4'),
                    func.sum(case((ProductReview.rating == 5, 1), else_=0)).label('rating_5'),
                ).where(ProductReview.product_id == product_id)
            )
            
            row = result.first()
            
            if row and row.total_reviews > 0:
                return {
                    "product_id": product_id,
                    "total_reviews": row.total_reviews,
                    "average_rating": float(row.average_rating or 0),
                    "rating_distribution": {
                        "1": int(row.rating_1 or 0),
                        "2": int(row.rating_2 or 0),
                        "3": int(row.rating_3 or 0),
                        "4": int(row.rating_4 or 0),
                        "5": int(row.rating_5 or 0)
                    }
                }
            else:
                return {
                    "product_id": product_id,
                    "total_reviews": 0,
                    "average_rating": 0.0,
                    "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
                }
    
    async def update_review(self, review_id: int, review_update: ReviewUpdate) -> Optional[Dict[str, Any]]:
        """Update an existing review."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(ProductReview).where(ProductReview.id == review_id)
            )
            review = result.scalar_one_or_none()
            
            if not review:
                return None
            
            # Update fields if provided
            if review_update.rating is not None:
                review.rating = review_update.rating
            if review_update.review_text is not None:
                review.review_text = review_update.review_text
            
            # Commit the changes
            await session.commit()
            await session.refresh(review)
            
            return review.to_dict()
    
    async def delete_review(self, review_id: int) -> bool:
        """Delete a review."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(ProductReview).where(ProductReview.id == review_id)
            )
            review = result.scalar_one_or_none()
            
            if not review:
                return False
            
            await session.delete(review)
            await session.commit()
            return True 