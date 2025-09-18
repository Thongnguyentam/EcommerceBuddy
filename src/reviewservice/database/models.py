from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ProductReview(Base):
    """SQLAlchemy model for product reviews."""
    __tablename__ = 'product_reviews'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    product_id = Column(String(255), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        UniqueConstraint('user_id', 'product_id', name='unique_user_product_review'),
        Index('idx_product_reviews_product_id', 'product_id'),
        Index('idx_product_reviews_user_id', 'user_id'),
        Index('idx_product_reviews_rating', 'rating'),
    )

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'rating': self.rating,
            'review_text': self.review_text,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        } 