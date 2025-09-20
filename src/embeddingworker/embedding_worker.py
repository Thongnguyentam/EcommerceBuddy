#!/usr/bin/env python3
"""
Embedding Worker Service
Listens to PostgreSQL notifications and processes embedding jobs by calling the embedding service
"""

import psycopg2
import psycopg2.extensions
import select
import json
import requests
import time
import logging
import os
import sys
from typing import Dict, List, Optional

from google.cloud import secretmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EmbeddingWorker:
    def __init__(self):
        # Database connection settings
        self.db_host = os.getenv('DB_HOST', '10.103.0.3')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_name = os.getenv('DB_NAME', 'products')
        self.secret_name = os.getenv('ALLOYDB_SECRET_NAME', 'cloudsql-secret-private')
        self.project_id = os.getenv('PROJECT_ID', 'gke-hack-471804')
        
        # Database password will be fetched from Secret Manager
        self.db_password = None
        
        # Embedding service settings
        self.embedding_service_url = os.getenv('EMBEDDING_SERVICE_URL', 'http://embeddingservice:8081')
        
        # Connection objects
        self.conn = None
        self.cursor = None
        
        # Statistics
        self.processed_jobs = 0
        self.failed_jobs = 0
    
    def get_database_password(self) -> str:
        """Retrieve database password from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/{self.secret_name}/versions/latest"
            logger.info(f"🔐 Accessing secret: {name}")
            response = client.access_secret_version(request={"name": name})
            password = response.payload.data.decode("UTF-8")
            logger.info(f"✅ Successfully retrieved password from Secret Manager (length: {len(password)})")
            return password.strip()
        except Exception as e:
            logger.error(f"❌ Failed to get database password from Secret Manager: {e}")
            raise
        
    def connect_to_database(self):
        """Establish connection to PostgreSQL database"""
        try:
            # Get password from Secret Manager if not already cached
            if self.db_password is None:
                logger.info("🔐 Retrieving database password from Secret Manager...")
                self.db_password = self.get_database_password()
            
            logger.info(f"🔌 Attempting database connection to {self.db_host}:{5432} as user '{self.db_user}' to database '{self.db_name}'")
            self.conn = psycopg2.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.conn.cursor()
            logger.info(f"✅ Connected to database at {self.db_host}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def test_embedding_service(self) -> bool:
        """Test if the embedding service is accessible"""
        try:
            response = requests.get(f"{self.embedding_service_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ Embedding service is healthy: {health_data}")
                return True
            else:
                logger.error(f"❌ Embedding service health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to embedding service: {e}")
            return False
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text"""
        if not text.strip():
            return None
            
        try:
            response = requests.post(
                f"{self.embedding_service_url}/embed",
                json={"text": text},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data["embedding"]
            else:
                logger.error(f"❌ Failed to get embedding for '{text[:50]}...': {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting embedding for '{text[:50]}...': {e}")
            return None
    
    def embedding_to_postgres_vector(self, embedding: List[float]) -> str:
        """Convert embedding list to PostgreSQL vector format"""
        return "[" + ",".join(map(str, embedding)) + "]"
    
    def process_embedding_job(self, payload: Dict):
        """Process a single embedding job"""
        try:
            product_id = payload['id']
            logger.info(f"🔄 Processing embedding job for product: {product_id}")
            
            # Prepare texts for embedding
            texts = {
                'description': payload.get('description', ''),
                'categories': payload.get('categories', ''),
                'combined': f"{payload.get('name', '')} {payload.get('description', '')} {payload.get('categories', '')}".strip(),
                'target_tags': payload.get('target_tags', ''),
                'use_context': payload.get('use_context', '')
            }
            
            # Generate embeddings
            embeddings = {}
            all_successful = True
            
            for field, text in texts.items():
                if text.strip():
                    embedding = self.get_embedding(text)
                    if embedding:
                        embeddings[f"{field}_embedding"] = self.embedding_to_postgres_vector(embedding)
                        logger.info(f"  ✅ Generated {field} embedding ({len(embedding)} dimensions)")
                    else:
                        logger.error(f"  ❌ Failed to generate {field} embedding")
                        all_successful = False
                        break
                else:
                    # Empty text gets NULL embedding
                    embeddings[f"{field}_embedding"] = None
                    logger.info(f"  ⚠️  Empty {field}, setting to NULL")
            
            if all_successful:
                # Update database with embeddings
                update_sql = """
                    UPDATE products SET 
                        description_embedding = %s::vector,
                        category_embedding = %s::vector,
                        combined_embedding = %s::vector,
                        target_tags_embedding = %s::vector,
                        use_context_embedding = %s::vector
                    WHERE id = %s
                """
                
                self.cursor.execute(update_sql, (
                    embeddings["description_embedding"],
                    embeddings["categories_embedding"],
                    embeddings["combined_embedding"],
                    embeddings["target_tags_embedding"],
                    embeddings["use_context_embedding"],
                    product_id
                ))
                
                self.processed_jobs += 1
                logger.info(f"  ✅ Updated embeddings for product {product_id}")
                
            else:
                self.failed_jobs += 1
                logger.error(f"  ❌ Failed to process embeddings for product {product_id}")
                
        except Exception as e:
            self.failed_jobs += 1
            logger.error(f"❌ Error processing embedding job: {e}")
    
    def listen_for_jobs(self):
        """Listen for PostgreSQL notifications and process embedding jobs"""
        try:
            # Start listening for notifications
            self.cursor.execute("LISTEN embedding_jobs;")
            logger.info("👂 Listening for embedding jobs...")
            
            while True:
                # Wait for notifications with 5-second timeout
                if select.select([self.conn], [], [], 5) == ([], [], []):
                    # Timeout - check connection health
                    continue
                
                # Poll for notifications
                self.conn.poll()
                
                # Process all pending notifications
                while self.conn.notifies:
                    notify = self.conn.notifies.pop(0)
                    try:
                        payload = json.loads(notify.payload)
                        self.process_embedding_job(payload)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON in notification: {e}")
                    except Exception as e:
                        logger.error(f"❌ Error processing notification: {e}")
                
                # Log statistics periodically
                if (self.processed_jobs + self.failed_jobs) % 10 == 0 and (self.processed_jobs + self.failed_jobs) > 0:
                    logger.info(f"📊 Stats - Processed: {self.processed_jobs}, Failed: {self.failed_jobs}")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"❌ Error in listen loop: {e}")
            raise
    
    def run(self):
        """Main worker loop"""
        logger.info("🚀 Starting Embedding Worker Service...")
        
        # Test embedding service
        if not self.test_embedding_service():
            logger.error("❌ Embedding service is not available. Exiting.")
            sys.exit(1)
        
        # Connect to database
        if not self.connect_to_database():
            logger.error("❌ Cannot connect to database. Exiting.")
            sys.exit(1)
        
        try:
            # Start listening for jobs
            self.listen_for_jobs()
        except Exception as e:
            logger.error(f"❌ Worker failed: {e}")
            sys.exit(1)
        finally:
            # Cleanup
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            logger.info(f"🎉 Worker stopped. Final stats - Processed: {self.processed_jobs}, Failed: {self.failed_jobs}")

if __name__ == "__main__":
    worker = EmbeddingWorker()
    worker.run() 