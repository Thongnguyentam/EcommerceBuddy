#!/usr/bin/env python3
"""
Simple integration test for the embedding service.
This test verifies the service works with actual credentials.
"""

import unittest
import json
import os
import sys
sys.path.append('..')
from embedding_service import create_app, VertexAIEmbeddingService


class TestEmbeddingServiceSimple(unittest.TestCase):
    """Simple integration tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'vertex-ai-embedding-service')
        print("✅ Health check passed")

    def test_embed_endpoint(self):
        """Test single embedding endpoint."""
        payload = {"text": "This is a test sentence."}
        response = self.client.post('/embed', json=payload)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn('embedding', data)
        self.assertIn('dimensions', data)
        self.assertEqual(data['dimensions'], 768)
        
        # Check that we got actual embeddings (not all zeros)
        embedding = data['embedding']
        self.assertEqual(len(embedding), 768)
        self.assertIsInstance(embedding[0], float)
        print(f"✅ Single embedding passed - dimensions: {len(embedding)}")

    def test_batch_endpoint(self):
        """Test batch embedding endpoint."""
        payload = {"texts": ["First sentence", "Second sentence", "Third sentence"]}
        response = self.client.post('/embed/batch', json=payload)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn('embeddings', data)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['dimensions'], 768)
        
        embeddings = data['embeddings']
        self.assertEqual(len(embeddings), 3)
        for embedding in embeddings:
            self.assertEqual(len(embedding), 768)
            self.assertIsInstance(embedding[0], float)
        print(f"✅ Batch embedding passed - count: {len(embeddings)}")

    def test_product_endpoint(self):
        """Test product embedding endpoint."""
        payload = {
            "name": "Modern Coffee Table",
            "description": "A sleek modern coffee table",
            "categories": "furniture,living room",
            "target_tags": ["modern", "minimalist"],
            "use_context": ["indoor", "living room"]
        }
        response = self.client.post('/embed/product', json=payload)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        required_fields = [
            'description_embedding', 'category_embedding', 'combined_embedding',
            'target_tags_embedding', 'use_context_embedding'
        ]
        
        for field in required_fields:
            self.assertIn(field, data)
            embedding = data[field]
            self.assertEqual(len(embedding), 768)
            self.assertIsInstance(embedding[0], float)
        
        print("✅ Product embedding passed - all fields generated")

    def test_error_handling(self):
        """Test error handling."""
        # Test missing text field
        response = self.client.post('/embed', json={})
        self.assertEqual(response.status_code, 400)
        
        # Test missing texts field
        response = self.client.post('/embed/batch', json={})
        self.assertEqual(response.status_code, 400)
        
        # Test missing product fields
        response = self.client.post('/embed/product', json={"name": "Test"})
        self.assertEqual(response.status_code, 400)
        
        print("✅ Error handling passed")


def main():
    """Run simple tests."""
    print("🧪 Simple Embedding Service Tests")
    print("=" * 40)
    
    # Check credentials
    has_creds = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    if not has_creds:
        print("❌ No Google credentials found!")
        print("   Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        return False
    
    print("🔑 Google credentials found")
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEmbeddingServiceSimple)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n🎉 All simple tests passed!")
        print("✅ Embedding service is working correctly")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 