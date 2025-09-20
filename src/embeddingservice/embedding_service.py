#!/usr/bin/env python3
"""
Google Vertex AI Embedding Service

This service provides embeddings using Google Vertex AI's text embedding models.
It runs as a standalone HTTP service that the Go product catalog service calls.
"""

import os
import json
import logging
from typing import List, Dict, Any
from flask import Flask, request, jsonify
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.environ.get("PROJECT_ID", "gke-hack-471804")
REGION = os.environ.get("REGION", "us-central1")
MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")

# Check for authentication
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set. Service may fail in production.")
    logger.info("For local testing, set GOOGLE_APPLICATION_CREDENTIALS to your service account key file path")
    logger.info("For Kubernetes, ensure the service account has Vertex AI permissions")

# Initialize Vertex AI
try:
    aiplatform.init(project=PROJECT_ID, location=REGION)
    logger.info(f"Initialized Vertex AI for project {PROJECT_ID} in region {REGION}")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI: {e}")
    logger.error("Make sure you have proper authentication and permissions for Vertex AI")

class VertexAIEmbeddingService:
    def __init__(self):
        self.model = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of the Vertex AI model."""
        if not self._initialized:
            try:
                self.model = TextEmbeddingModel.from_pretrained(MODEL_NAME)
                logger.info(f"Initialized Vertex AI embedding model: {MODEL_NAME}")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI model: {e}")
                self._initialized = True  # Mark as initialized to avoid retrying
                raise RuntimeError(f"Cannot initialize Vertex AI embedding model: {e}") from e

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 768
        
        # Ensure model is initialized
        self._ensure_initialized()
        
        if not self.model:
            raise RuntimeError("Vertex AI model is not initialized")
        
        try:
            # Clean and truncate text if needed (Vertex AI has input limits)
            text = text.strip()[:8000]  # Limit to ~8000 characters
            
            embeddings = self.model.get_embeddings([text])
            if embeddings and len(embeddings) > 0:
                return embeddings[0].values
            else:
                raise RuntimeError(f"No embedding returned from Vertex AI for text: {text[:50]}...")
                
        except Exception as e:
            logger.error(f"Failed to generate embedding for text '{text[:50]}...': {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        # Ensure model is initialized
        self._ensure_initialized()
        
        if not self.model:
            raise RuntimeError("Vertex AI model is not initialized")
        
        try:
            # Clean texts
            cleaned_texts = [text.strip()[:8000] if text else "" for text in texts]
            
            embeddings = self.model.get_embeddings(cleaned_texts)
            result = []
            for i, emb in enumerate(embeddings):
                if emb:
                    result.append(emb.values)
                else:
                    raise RuntimeError(f"No embedding returned for text {i}: {cleaned_texts[i][:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise RuntimeError(f"Batch embedding generation failed: {e}") from e

# Initialize the service (will be done lazily)
embedding_service = None

def create_app():
    global embedding_service
    if embedding_service is None:
        embedding_service = VertexAIEmbeddingService()
    
    app = Flask(__name__)
    
    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "service": "vertex-ai-embedding-service",
            "model": MODEL_NAME,
            "project": PROJECT_ID,
            "region": REGION
        })
    
    @app.route("/embed", methods=["POST"])
    def generate_embedding():
        """Generate embedding for a single text."""
        try:
            data = request.get_json()
            if not data or "text" not in data:
                return jsonify({"error": "Missing 'text' field in request"}), 400
            
            text = data["text"]
            embedding = embedding_service.generate_embedding(text)
            
            return jsonify({
                "embedding": embedding,
                "dimensions": len(embedding),
                "model": MODEL_NAME
            })
            
        except RuntimeError as e:
            logger.error(f"Runtime error in /embed endpoint: {e}")
            return jsonify({"error": f"Service error: {str(e)}"}), 503
        except Exception as e:
            logger.error(f"Unexpected error in /embed endpoint: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @app.route("/embed/batch", methods=["POST"])
    def generate_embeddings_batch():
        """Generate embeddings for multiple texts."""
        try:
            data = request.get_json()
            if not data or "texts" not in data:
                return jsonify({"error": "Missing 'texts' field in request"}), 400
            
            texts = data["texts"]
            if not isinstance(texts, list):
                return jsonify({"error": "'texts' must be a list"}), 400
            
            embeddings = embedding_service.generate_embeddings_batch(texts)
            
            return jsonify({
                "embeddings": embeddings,
                "count": len(embeddings),
                "dimensions": len(embeddings[0]) if embeddings else 0,
                "model": MODEL_NAME
            })
            
        except RuntimeError as e:
            logger.error(f"Runtime error in /embed/batch endpoint: {e}")
            return jsonify({"error": f"Service error: {str(e)}"}), 503
        except Exception as e:
            logger.error(f"Unexpected error in /embed/batch endpoint: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    @app.route("/embed/product", methods=["POST"])
    def generate_product_embeddings():
        """Generate all embeddings needed for a product."""
        try:
            data = request.get_json()
            required_fields = ["name", "description", "categories", "target_tags", "use_context"]
            
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing '{field}' field in request"}), 400
            
            # Prepare texts for embedding
            texts = [
                data["description"],
                data["categories"],
                f"{data['name']} {data['description']} {data['categories']}",  # combined
                " ".join(data["target_tags"]) if data["target_tags"] else "",
                " ".join(data["use_context"]) if data["use_context"] else ""
            ]
            
            embeddings = embedding_service.generate_embeddings_batch(texts)
            
            return jsonify({
                "description_embedding": embeddings[0],
                "category_embedding": embeddings[1],
                "combined_embedding": embeddings[2],
                "target_tags_embedding": embeddings[3],
                "use_context_embedding": embeddings[4],
                "model": MODEL_NAME,
                "dimensions": len(embeddings[0]) if embeddings else 0
            })
            
        except RuntimeError as e:
            logger.error(f"Runtime error in /embed/product endpoint: {e}")
            return jsonify({"error": f"Service error: {str(e)}"}), 503
        except Exception as e:
            logger.error(f"Unexpected error in /embed/product endpoint: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8081))
    app.run(host="0.0.0.0", port=port, debug=False) 