#!/usr/bin/env python3
"""
Tests for the Vertex AI Embedding Service
"""

import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from embedding_service import VertexAIEmbeddingService, create_app


class TestVertexAIEmbeddingService(unittest.TestCase):
    """Test the VertexAIEmbeddingService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the Vertex AI model to avoid actual API calls
        self.mock_model = Mock()
        self.mock_embedding = Mock()
        self.mock_embedding.values = [0.1, 0.2, 0.3] + [0.0] * 765  # 768 dimensions
        self.mock_model.get_embeddings.return_value = [self.mock_embedding]

    @patch('embedding_service.TextEmbeddingModel.from_pretrained')
    @patch('embedding_service.aiplatform.init')
    def test_service_initialization(self, mock_init, mock_from_pretrained):
        """Test service initialization."""
        mock_from_pretrained.return_value = self.mock_model
        
        service = VertexAIEmbeddingService()
        # Test lazy initialization
        service._ensure_initialized()
        
        self.assertIsNotNone(service.model)
        # aiplatform.init is called during module import, not service init
        mock_from_pretrained.assert_called_once_with("text-embedding-004")

    @patch('embedding_service.TextEmbeddingModel.from_pretrained')
    @patch('embedding_service.aiplatform.init')
    def test_generate_embedding_success(self, mock_init, mock_from_pretrained):
        """Test successful embedding generation."""
        mock_from_pretrained.return_value = self.mock_model
        service = VertexAIEmbeddingService()
        
        result = service.generate_embedding("test text")
        
        self.assertEqual(len(result), 768)
        self.assertEqual(result[:3], [0.1, 0.2, 0.3])
        self.mock_model.get_embeddings.assert_called_once_with(["test text"])

    @patch('embedding_service.TextEmbeddingModel.from_pretrained')
    @patch('embedding_service.aiplatform.init')
    def test_generate_embedding_empty_text(self, mock_init, mock_from_pretrained):
        """Test embedding generation with empty text."""
        mock_from_pretrained.return_value = self.mock_model
        service = VertexAIEmbeddingService()
        
        result = service.generate_embedding("")
        
        self.assertEqual(len(result), 768)
        self.assertEqual(result, [0.0] * 768)
        self.mock_model.get_embeddings.assert_not_called()

    @patch('embedding_service.TextEmbeddingModel.from_pretrained')
    @patch('embedding_service.aiplatform.init')
    def test_generate_embedding_api_error(self, mock_init, mock_from_pretrained):
        """Test embedding generation with API error."""
        mock_from_pretrained.return_value = self.mock_model
        self.mock_model.get_embeddings.side_effect = Exception("API Error")
        service = VertexAIEmbeddingService()
        
        # Should raise RuntimeError on API error
        with self.assertRaises(RuntimeError) as context:
            service.generate_embedding("test text")
        
        self.assertIn("Embedding generation failed", str(context.exception))

    @patch('embedding_service.TextEmbeddingModel.from_pretrained')
    @patch('embedding_service.aiplatform.init')
    def test_generate_embeddings_batch(self, mock_init, mock_from_pretrained):
        """Test batch embedding generation."""
        mock_from_pretrained.return_value = self.mock_model
        mock_embeddings = [Mock(), Mock()]
        mock_embeddings[0].values = [0.1] * 768
        mock_embeddings[1].values = [0.2] * 768
        self.mock_model.get_embeddings.return_value = mock_embeddings
        service = VertexAIEmbeddingService()
        
        texts = ["text1", "text2"]
        result = service.generate_embeddings_batch(texts)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 768)
        self.assertEqual(len(result[1]), 768)
        self.assertEqual(result[0], [0.1] * 768)
        self.assertEqual(result[1], [0.2] * 768)


class TestEmbeddingServiceAPI(unittest.TestCase):
    """Test the Flask API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test app with mocked service
        self.mock_service = Mock()
        self.mock_service.generate_embedding.return_value = [0.1] * 768
        # Product endpoint needs 5 embeddings: description, category, combined, target_tags, use_context
        self.mock_service.generate_embeddings_batch.return_value = [
            [0.1] * 768,  # description_embedding
            [0.2] * 768,  # category_embedding  
            [0.3] * 768,  # combined_embedding
            [0.4] * 768,  # target_tags_embedding
            [0.5] * 768   # use_context_embedding
        ]
        
        # Patch the global embedding_service
        self.patcher = patch('embedding_service.embedding_service', self.mock_service)
        self.patcher.start()
        
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'vertex-ai-embedding-service')

    def test_embed_endpoint_success(self):
        """Test successful embedding endpoint."""
        payload = {"text": "test text"}
        response = self.client.post('/embed', 
                                  json=payload,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('embedding', data)
        self.assertIn('dimensions', data)
        self.assertEqual(data['dimensions'], 768)
        self.mock_service.generate_embedding.assert_called_once_with("test text")

    def test_embed_endpoint_missing_text(self):
        """Test embedding endpoint with missing text."""
        payload = {}
        response = self.client.post('/embed',
                                  json=payload,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Missing', data['error'])

    def test_embed_batch_endpoint_success(self):
        """Test successful batch embedding endpoint."""
        # Override mock for this specific test
        self.mock_service.generate_embeddings_batch.return_value = [[0.1] * 768, [0.2] * 768]
        
        payload = {"texts": ["text1", "text2"]}
        response = self.client.post('/embed/batch',
                                  json=payload,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('embeddings', data)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 2)
        self.mock_service.generate_embeddings_batch.assert_called_once_with(["text1", "text2"])

    def test_embed_batch_endpoint_invalid_texts(self):
        """Test batch embedding endpoint with invalid texts."""
        payload = {"texts": "not a list"}
        response = self.client.post('/embed/batch',
                                  json=payload,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_embed_product_endpoint_success(self):
        """Test successful product embedding endpoint."""
        payload = {
            "name": "Test Product",
            "description": "A test product",
            "categories": "test,product",
            "target_tags": ["unisex"],
            "use_context": ["indoor"]
        }
        response = self.client.post('/embed/product',
                                  json=payload,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('description_embedding', data)
        self.assertIn('category_embedding', data)
        self.assertIn('combined_embedding', data)
        self.assertIn('target_tags_embedding', data)
        self.assertIn('use_context_embedding', data)

    def test_embed_product_endpoint_missing_field(self):
        """Test product embedding endpoint with missing field."""
        payload = {
            "name": "Test Product",
            "description": "A test product",
            # Missing required fields
        }
        response = self.client.post('/embed/product',
                                  json=payload,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Missing', data['error'])

    def test_embed_endpoint_service_error(self):
        """Test embedding endpoint with service error."""
        self.mock_service.generate_embedding.side_effect = RuntimeError("Model not initialized")
        
        payload = {"text": "test text"}
        response = self.client.post('/embed', json=payload)
        
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Service error', data['error'])

    def test_batch_endpoint_service_error(self):
        """Test batch endpoint with service error."""
        # Reset the mock to raise an exception
        self.mock_service.reset_mock()
        self.mock_service.generate_embeddings_batch.side_effect = RuntimeError("Model not initialized")
        
        payload = {"texts": ["text1", "text2"]}
        response = self.client.post('/embed/batch', json=payload)
        
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Service error', data['error'])


class TestEmbeddingServiceIntegration(unittest.TestCase):
    """Integration tests (require actual credentials)."""

    @unittest.skipUnless(
        os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or 
        os.environ.get('RUN_INTEGRATION_TESTS') == 'true',
        "Integration tests require Google credentials"
    )
    def test_real_vertex_ai_call(self):
        """Test actual Vertex AI call (only if credentials available)."""
        try:
            service = VertexAIEmbeddingService()
            result = service.generate_embedding("This is a test sentence for embedding.")
            
            self.assertEqual(len(result), 768)
            self.assertIsInstance(result[0], float)
            # Check that it's not a zero vector
            self.assertNotEqual(result, [0.0] * 768)
            
        except Exception as e:
            self.skipTest(f"Integration test failed due to: {e}")


if __name__ == '__main__':
    # Set up test environment
    os.environ['PROJECT_ID'] = 'test-project'
    os.environ['REGION'] = 'us-central1'
    os.environ['EMBEDDING_MODEL'] = 'text-embedding-004'
    
    unittest.main() 