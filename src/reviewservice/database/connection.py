import os
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from google.cloud import secretmanager

from .models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager using SQLAlchemy ORM for Cloud SQL PostgreSQL."""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.project_id = os.getenv("PROJECT_ID")
        self.secret_name = os.getenv("ALLOYDB_SECRET_NAME")
        self.database_name = os.getenv("ALLOYDB_DATABASE_NAME", "reviews")
        self.host = os.getenv("CLOUDSQL_HOST")

    async def initialize(self):
        """Initialize the database engine and session factory."""
        if not self.host:
            logger.info("CLOUDSQL_HOST not set - running without database")
            return
        
        logger.info("Initializing Cloud SQL connection for reviews...")
        
        # Get database password from Secret Manager
        password = await self._get_secret_payload(
            self.project_id, 
            self.secret_name, 
            "latest"
        )
        
        # Create async engine
        logger.info(f"Connecting to database URL: postgresql+asyncpg://postgres:***@{self.host}/{self.database_name}")
        database_url = f"postgresql+asyncpg://postgres:{password}@{self.host}/{self.database_name}"
        self.engine = create_async_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=True  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"Successfully connected to Cloud SQL for reviews - Database: {self.database_name}, Host: {self.host}")
        
        # Create tables if they don't exist
        await self._create_tables()
    
    async def close(self):
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
    
    async def _get_secret_payload(self, project_id: str, secret_id: str, version: str) -> str:
        """Retrieve secret from Google Secret Manager."""
        logger.info(f"Attempting to connect to Secret Manager for project={project_id}, secret={secret_id}")
        
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        
        response = client.access_secret_version(request={"name": name})
        logger.info("Successfully retrieved secret from Secret Manager")
        
        return response.payload.data.decode("UTF-8").strip()
    
    async def _create_tables(self):
        """Create database tables if they don't exist."""
        if not self.engine:
            return
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created/verified")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager."""
        if not self.async_session:
            raise Exception("Database not initialized")
        
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close() 