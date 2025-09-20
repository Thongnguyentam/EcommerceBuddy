#!/usr/bin/env python3
"""
Test error handling when credentials are not available.
"""

import unittest
import json
import os
import sys
sys.path.append('..')
from embedding_service import create_app, VertexAIEmbeddingService


class TestErrorHandling(unittest.TestCase):
    """Test error handling without credentials."""

    def setUp(self):
        """Set up test without credentials."""
        # Remove credentials from environment
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        # Set test environment
        os.environ['PROJECT_ID'] = 'test-project'
        os.environ['REGION'] = 'us-central1'
        os.environ['EMBEDDING_MODEL'] = 'text-embedding-004'

    def test_service_initialization_fails(self):
        """Test that service initialization fails without credentials."""
        service = VertexAIEmbeddingService()
        
        with self.assertRaises(RuntimeError) as context:
            service._ensure_initialized()
        
        self.assertIn("Cannot initialize Vertex AI embedding model", str(context.exception))
        print("✅ Service initialization properly fails without credentials")

    def test_embedding_generation_fails(self):
        """Test that embedding generation fails without credentials."""
        service = VertexAIEmbeddingService()
        
        with self.assertRaises(RuntimeError):
            service.generate_embedding("test text")
        
        print("✅ Embedding generation properly fails without credentials")

    def test_api_endpoint_returns_503(self):
        """Test that API endpoint returns 503 service unavailable."""
        app = create_app()
        client = app.test_client()
        
        payload = {"text": "test text"}
        response = client.post('/embed', json=payload)
        
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('Service error', data['error'])
        
        print("✅ API endpoint returns 503 without credentials")


def main():
    """Run error handling tests."""
    print("🧪 Error Handling Tests (No Credentials)")
    print("=" * 45)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n🎉 All error handling tests passed!")
        print("✅ Service properly handles missing credentials")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 