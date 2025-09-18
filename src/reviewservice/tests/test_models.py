import pytest
from pydantic import ValidationError
from models import ReviewCreate, ReviewUpdate, ReviewResponse, ProductReviewsSummary
from datetime import datetime, timezone

class TestReviewCreate:
    """Test ReviewCreate model validation."""
    
    def test_valid_review_create(self):
        """Test creating a valid review."""
        review = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=5,
            review_text="Great product!"
        )
        assert review.user_id == "user123"
        assert review.product_id == "prod456"
        assert review.rating == 5
        assert review.review_text == "Great product!"
    
    def test_review_create_without_text(self):
        """Test creating a review without optional text."""
        review = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=4
        )
        assert review.review_text is None
    
    def test_invalid_rating_high(self):
        """Test validation fails for rating > 5."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewCreate(
                user_id="user123",
                product_id="prod456",
                rating=6
            )
        assert "Input should be less than or equal to 5" in str(exc_info.value)
    
    def test_invalid_rating_low(self):
        """Test validation fails for rating < 1."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewCreate(
                user_id="user123",
                product_id="prod456",
                rating=0
            )
        assert "Input should be greater than or equal to 1" in str(exc_info.value)
    
    def test_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewCreate(rating=5)
        
        errors = exc_info.value.errors()
        missing_fields = {error['loc'][0] for error in errors}
        assert 'user_id' in missing_fields
        assert 'product_id' in missing_fields

class TestReviewUpdate:
    """Test ReviewUpdate model validation."""
    
    def test_valid_review_update_partial(self):
        """Test updating only rating."""
        update = ReviewUpdate(rating=4)
        assert update.rating == 4
        assert update.review_text is None
    
    def test_valid_review_update_full(self):
        """Test updating both rating and text."""
        update = ReviewUpdate(
            rating=3,
            review_text="Updated review"
        )
        assert update.rating == 3
        assert update.review_text == "Updated review"
    
    def test_empty_update(self):
        """Test update with no fields."""
        update = ReviewUpdate()
        assert update.rating is None
        assert update.review_text is None
    
    def test_invalid_rating_update(self):
        """Test validation fails for invalid rating in update."""
        with pytest.raises(ValidationError):
            ReviewUpdate(rating=10)

class TestReviewResponse:
    """Test ReviewResponse model."""
    
    def test_review_response_creation(self):
        """Test creating a review response."""
        now = datetime.now(timezone.utc)
        response = ReviewResponse(
            id=1,
            user_id="user123",
            product_id="prod456",
            rating=5,
            review_text="Great!",
            created_at=now,
            updated_at=now
        )
        assert response.id == 1
        assert response.user_id == "user123"
        assert response.rating == 5

class TestProductReviewsSummary:
    """Test ProductReviewsSummary model."""
    
    def test_summary_creation(self):
        """Test creating a product reviews summary."""
        summary = ProductReviewsSummary(
            product_id="prod123",
            total_reviews=10,
            average_rating=4.2,
            rating_distribution={"1": 0, "2": 1, "3": 2, "4": 3, "5": 4}
        )
        assert summary.product_id == "prod123"
        assert summary.total_reviews == 10
        assert summary.average_rating == 4.2
        assert summary.rating_distribution["5"] == 4 