import pytest
import pytest_asyncio
import grpc
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from server import ReviewServicer, create_grpc_server
from database import Base, DatabaseManager, ReviewRepository
from genproto import review_pb2

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
async def grpc_servicer(test_db_manager):
    """Create a gRPC servicer for testing."""
    servicer = ReviewServicer()
    servicer.db_manager = test_db_manager
    servicer.repository = ReviewRepository(test_db_manager)
    return servicer

class TestReviewGRPCService:
    """Test Review gRPC Service."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, grpc_servicer):
        """Test gRPC health check."""
        request = review_pb2.HealthCheckRequest(service="review.ReviewService")
        context = None  # Mock context for testing
        
        response = await grpc_servicer.Check(request, context)
        
        assert response.status == review_pb2.HealthCheckResponse.ServingStatus.SERVING
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_empty(self, grpc_servicer):
        """Test getting reviews for a product with no reviews."""
        request = review_pb2.GetProductReviewsRequest(
            product_id="nonexistent_product",
            limit=10,
            offset=0
        )
        context = None  # Mock context for testing
        
        response = await grpc_servicer.GetProductReviews(request, context)
        
        assert len(response.reviews) == 0
    
    @pytest.mark.asyncio
    async def test_get_product_review_summary_empty(self, grpc_servicer):
        """Test getting review summary for a product with no reviews."""
        request = review_pb2.GetProductReviewSummaryRequest(
            product_id="nonexistent_product"
        )
        context = None  # Mock context for testing
        
        response = await grpc_servicer.GetProductReviewSummary(request, context)
        
        assert response.product_id == "nonexistent_product"
        assert response.total_reviews == 0
        assert response.average_rating == 0.0
        
        # Check rating distribution
        assert response.rating_distribution["1"] == 0
        assert response.rating_distribution["2"] == 0
        assert response.rating_distribution["3"] == 0
        assert response.rating_distribution["4"] == 0
        assert response.rating_distribution["5"] == 0
    
    @pytest.mark.asyncio
    async def test_create_review(self, grpc_servicer):
        """Test creating a new review."""
        request = review_pb2.CreateReviewRequest(
            user_id="test_user",
            product_id="test_product",
            rating=5,
            review_text="Great product!"
        )
        context = None  # Mock context for testing
        
        response = await grpc_servicer.CreateReview(request, context)
        
        assert response.success is True
        assert "successfully" in response.message.lower()
        assert response.review.user_id == "test_user"
        assert response.review.product_id == "test_product"
        assert response.review.rating == 5
        assert response.review.review_text == "Great product!"
        assert response.review.id > 0
    
    @pytest.mark.asyncio
    async def test_create_review_invalid_rating(self, grpc_servicer):
        """Test creating a review with invalid rating."""
        request = review_pb2.CreateReviewRequest(
            user_id="test_user",
            product_id="test_product",
            rating=6,  # Invalid rating
            review_text="Test"
        )
        context = None
        
        response = await grpc_servicer.CreateReview(request, context)
        
        assert response.success is False
        assert "invalid rating" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_get_user_reviews(self, grpc_servicer):
        """Test getting reviews by user."""
        # First create a review
        create_request = review_pb2.CreateReviewRequest(
            user_id="test_user",
            product_id="test_product",
            rating=4,
            review_text="Good product"
        )
        await grpc_servicer.CreateReview(create_request, None)
        
        # Now get user reviews
        request = review_pb2.GetUserReviewsRequest(
            user_id="test_user",
            limit=10,
            offset=0
        )
        context = None
        
        response = await grpc_servicer.GetUserReviews(request, context)
        
        assert len(response.reviews) == 1
        assert response.reviews[0].user_id == "test_user"
        assert response.reviews[0].rating == 4
    
    @pytest.mark.asyncio
    async def test_get_review_by_id(self, grpc_servicer):
        """Test getting a specific review by ID."""
        # First create a review
        create_request = review_pb2.CreateReviewRequest(
            user_id="test_user",
            product_id="test_product",
            rating=3,
            review_text="Okay product"
        )
        create_response = await grpc_servicer.CreateReview(create_request, None)
        review_id = create_response.review.id
        
        # Now get the review by ID
        request = review_pb2.GetReviewRequest(review_id=review_id)
        context = None
        
        response = await grpc_servicer.GetReview(request, context)
        
        assert response.found is True
        assert response.review.id == review_id
        assert response.review.rating == 3
        assert response.review.review_text == "Okay product"
    
    @pytest.mark.asyncio
    async def test_update_review(self, grpc_servicer):
        """Test updating an existing review."""
        # First create a review
        create_request = review_pb2.CreateReviewRequest(
            user_id="test_user",
            product_id="test_product",
            rating=3,
            review_text="Okay product"
        )
        create_response = await grpc_servicer.CreateReview(create_request, None)
        review_id = create_response.review.id
        
        # Now update the review
        update_request = review_pb2.UpdateReviewRequest(
            review_id=review_id,
            rating=5,
            review_text="Actually, it's excellent!"
        )
        context = None
        
        response = await grpc_servicer.UpdateReview(update_request, context)
        
        assert response.success is True
        assert "successfully" in response.message.lower()
        assert response.review.rating == 5
        assert response.review.review_text == "Actually, it's excellent!"
    
    @pytest.mark.asyncio
    async def test_delete_review(self, grpc_servicer):
        """Test deleting a review."""
        # First create a review
        create_request = review_pb2.CreateReviewRequest(
            user_id="test_user",
            product_id="test_product",
            rating=2,
            review_text="Not great"
        )
        create_response = await grpc_servicer.CreateReview(create_request, None)
        review_id = create_response.review.id
        
        # Now delete the review
        delete_request = review_pb2.DeleteReviewRequest(review_id=review_id)
        context = None
        
        response = await grpc_servicer.DeleteReview(delete_request, context)
        
        assert response.success is True
        assert "successfully" in response.message.lower()
        
        # Verify it's actually deleted
        get_request = review_pb2.GetReviewRequest(review_id=review_id)
        get_response = await grpc_servicer.GetReview(get_request, None)
        assert get_response.found is False 