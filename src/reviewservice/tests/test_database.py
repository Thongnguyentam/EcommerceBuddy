import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, ProductReview, DatabaseManager, ReviewRepository
from models import ReviewCreate, ReviewUpdate

@pytest_asyncio.fixture
async def test_db_manager():
    """Create a test database manager with in-memory SQLite."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create database manager
    db_manager = DatabaseManager()
    db_manager.engine = engine
    db_manager.async_session = async_session
    
    yield db_manager
    
    # Cleanup
    await engine.dispose()

@pytest_asyncio.fixture
async def review_repo(test_db_manager):
    """Create a review repository for testing."""
    return ReviewRepository(test_db_manager)

class TestReviewRepository:
    """Test ReviewRepository database operations."""
    
    @pytest.mark.asyncio
    async def test_create_review(self, review_repo):
        """Test creating a new review."""
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=5,
            review_text="Great product!"
        )
        
        created_review = await review_repo.create_review(review_data)
        assert created_review is not None
        assert isinstance(created_review, dict)
        assert 'id' in created_review
        assert created_review['user_id'] == "user123"
        assert created_review['product_id'] == "prod456"
        assert created_review['rating'] == 5
    
    @pytest.mark.asyncio
    async def test_create_duplicate_review_fails(self, review_repo):
        """Test that creating duplicate review fails."""
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=5,
            review_text="Great product!"
        )
        
        # Create first review
        await review_repo.create_review(review_data)
        
        # Try to create duplicate - should fail
        with pytest.raises(ValueError, match="User has already reviewed this product"):
            await review_repo.create_review(review_data)
    
    @pytest.mark.asyncio
    async def test_get_review_by_id(self, review_repo):
        """Test retrieving a review by ID."""
        # Create a review
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=4,
            review_text="Good product"
        )
        created_review = await review_repo.create_review(review_data)
        review_id = created_review['id']
        
        # Retrieve the review
        retrieved_review = await review_repo.get_review_by_id(review_id)
        
        assert retrieved_review is not None
        assert retrieved_review['id'] == review_id
        assert retrieved_review['user_id'] == "user123"
        assert retrieved_review['product_id'] == "prod456"
        assert retrieved_review['rating'] == 4
        assert retrieved_review['review_text'] == "Good product"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_review(self, review_repo):
        """Test retrieving a non-existent review returns None."""
        review = await review_repo.get_review_by_id(999)
        assert review is None
    
    @pytest.mark.asyncio
    async def test_get_user_product_review(self, review_repo):
        """Test retrieving a user's review for a specific product."""
        # Create a review
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=3
        )
        await review_repo.create_review(review_data)
        
        # Retrieve the review
        retrieved_review = await review_repo.get_user_product_review("user123", "prod456")
        
        assert retrieved_review is not None
        assert retrieved_review['user_id'] == "user123"
        assert retrieved_review['product_id'] == "prod456"
        
        # Test non-existent combination
        no_review = await review_repo.get_user_product_review("user123", "prod999")
        assert no_review is None
    
    @pytest.mark.asyncio
    async def test_get_product_reviews(self, review_repo):
        """Test retrieving all reviews for a product."""
        product_id = "prod123"
        
        # Create multiple reviews for the same product
        for i in range(3):
            review_data = ReviewCreate(
                user_id=f"user{i}",
                product_id=product_id,
                rating=i + 3,  # ratings 3, 4, 5
                review_text=f"Review {i}"
            )
            await review_repo.create_review(review_data)
        
        # Retrieve all reviews
        reviews = await review_repo.get_product_reviews(product_id)
        
        assert len(reviews) == 3
        # Should be ordered by created_at DESC
        for review in reviews:
            assert review['product_id'] == product_id
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_pagination(self, review_repo):
        """Test pagination for product reviews."""
        product_id = "prod123"
        
        # Create 5 reviews
        for i in range(5):
            review_data = ReviewCreate(
                user_id=f"user{i}",
                product_id=product_id,
                rating=5
            )
            await review_repo.create_review(review_data)
        
        # Test pagination
        first_page = await review_repo.get_product_reviews(product_id, limit=2, offset=0)
        second_page = await review_repo.get_product_reviews(product_id, limit=2, offset=2)
        
        assert len(first_page) == 2
        assert len(second_page) == 2
        
        # Ensure different reviews
        first_ids = {r['id'] for r in first_page}
        second_ids = {r['id'] for r in second_page}
        assert first_ids.isdisjoint(second_ids)
    
    @pytest.mark.asyncio
    async def test_get_user_reviews(self, review_repo):
        """Test retrieving all reviews by a user."""
        user_id = "user123"
        
        # Create reviews for different products
        for i in range(3):
            review_data = ReviewCreate(
                user_id=user_id,
                product_id=f"prod{i}",
                rating=4,
                review_text=f"Review for product {i}"
            )
            await review_repo.create_review(review_data)
        
        # Retrieve user's reviews
        reviews = await review_repo.get_user_reviews(user_id)
        
        assert len(reviews) == 3
        for review in reviews:
            assert review['user_id'] == user_id
    
    @pytest.mark.asyncio
    async def test_get_product_review_summary(self, review_repo):
        """Test getting review summary statistics."""
        product_id = "prod123"
        
        # Create reviews with different ratings
        ratings = [5, 4, 4, 3, 3, 3, 2, 1]
        for i, rating in enumerate(ratings):
            review_data = ReviewCreate(
                user_id=f"user{i}",
                product_id=product_id,
                rating=rating
            )
            await review_repo.create_review(review_data)
        
        # Get summary
        summary = await review_repo.get_product_review_summary(product_id)
        
        assert summary['product_id'] == product_id
        assert summary['total_reviews'] == 8
        assert summary['average_rating'] == sum(ratings) / len(ratings)
        
        # Check rating distribution
        distribution = summary['rating_distribution']
        assert distribution['1'] == 1
        assert distribution['2'] == 1
        assert distribution['3'] == 3
        assert distribution['4'] == 2
        assert distribution['5'] == 1
    
    @pytest.mark.asyncio
    async def test_get_product_review_summary_no_reviews(self, review_repo):
        """Test summary for product with no reviews."""
        summary = await review_repo.get_product_review_summary("nonexistent_product")
        
        assert summary['product_id'] == "nonexistent_product"
        assert summary['total_reviews'] == 0
        assert summary['average_rating'] == 0.0
        assert all(count == 0 for count in summary['rating_distribution'].values())
    
    @pytest.mark.asyncio
    async def test_update_review(self, review_repo):
        """Test updating a review."""
        # Create a review
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=3,
            review_text="Original review"
        )
        created_review = await review_repo.create_review(review_data)
        review_id = created_review['id']
        
        # Update the review
        update_data = ReviewUpdate(
            rating=5,
            review_text="Updated review"
        )
        await review_repo.update_review(review_id, update_data)
        
        # Verify update
        updated_review = await review_repo.get_review_by_id(review_id)
        assert updated_review['rating'] == 5
        assert updated_review['review_text'] == "Updated review"
    
    @pytest.mark.asyncio
    async def test_update_review_partial(self, review_repo):
        """Test partially updating a review."""
        # Create a review
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=3,
            review_text="Original review"
        )
        created_review = await review_repo.create_review(review_data)

        review_id = created_review["id"]
        
        # Update only rating
        update_data = ReviewUpdate(rating=4)
        await review_repo.update_review(review_id, update_data)
        
        # Verify update
        updated_review = await review_repo.get_review_by_id(review_id)
        assert updated_review['rating'] == 4
        assert updated_review['review_text'] == "Original review"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_review(self, review_repo):
        """Test updating a non-existent review returns None."""
        update_data = ReviewUpdate(rating=5)

        result = await review_repo.update_review(999, update_data)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_review(self, review_repo):
        """Test deleting a review."""
        # Create a review
        review_data = ReviewCreate(
            user_id="user123",
            product_id="prod456",
            rating=4
        )
        created_review = await review_repo.create_review(review_data)

        review_id = created_review["id"]
        
        # Verify it exists
        review = await review_repo.get_review_by_id(review_id)
        assert review is not None
        
        # Delete the review
        await review_repo.delete_review(review_id)
        
        # Verify it's gone
        deleted_review = await review_repo.get_review_by_id(review_id)
        assert deleted_review is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_review(self, review_repo):
        """Test deleting a non-existent review returns False."""
        result = await review_repo.delete_review(999)
        assert result is False 