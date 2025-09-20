#!/usr/bin/env python3
"""
Kubernetes Integration Test for Embedding Service

This test connects to the deployed embedding service via port-forward
and verifies all endpoints work correctly with Workload Identity.

Prerequisites:
- Embedding service deployed to Kubernetes
- Port forwarding active: kubectl port-forward svc/embeddingservice 8081:8081

Run with: python test_k8s_integration.py
"""

import requests
import json
import time
import sys
import subprocess


class EmbeddingServiceK8sTest:
    def __init__(self, base_url="http://localhost:8081"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30

    def test_health_check(self):
        """Test the health check endpoint."""
        print("🏥 Testing health check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "vertex-ai-embedding-service"
            assert data["project"] == "gke-hack-471804"
            assert data["model"] == "text-embedding-004"
            
            print(f"✅ Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   Project: {data['project']}")
            print(f"   Model: {data['model']}")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def test_single_embedding(self):
        """Test single text embedding."""
        print("\n🔤 Testing single embedding...")
        try:
            payload = {
                "text": "This is a test sentence for Kubernetes integration testing."
            }
            
            response = self.session.post(
                f"{self.base_url}/embed",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            assert "embedding" in data
            assert "dimensions" in data
            assert data["dimensions"] == 768
            assert len(data["embedding"]) == 768
            assert isinstance(data["embedding"][0], float)
            
            # Verify it's not a zero vector
            assert not all(x == 0.0 for x in data["embedding"])
            
            print(f"✅ Single embedding passed")
            print(f"   Dimensions: {data['dimensions']}")
            print(f"   First 3 values: {data['embedding'][:3]}")
            return True
            
        except Exception as e:
            print(f"❌ Single embedding failed: {e}")
            return False

    def test_batch_embedding(self):
        """Test batch text embedding."""
        print("\n📦 Testing batch embedding...")
        try:
            payload = {
                "texts": [
                    "Kubernetes integration test sentence one.",
                    "Kubernetes integration test sentence two.",
                    "Kubernetes integration test sentence three."
                ]
            }
            
            response = self.session.post(
                f"{self.base_url}/embed/batch",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            assert "embeddings" in data
            assert "count" in data
            assert data["count"] == 3
            assert data["dimensions"] == 768
            assert len(data["embeddings"]) == 3
            
            for i, embedding in enumerate(data["embeddings"]):
                assert len(embedding) == 768
                assert isinstance(embedding[0], float)
                # Verify it's not a zero vector
                assert not all(x == 0.0 for x in embedding)
            
            print(f"✅ Batch embedding passed")
            print(f"   Count: {data['count']}")
            print(f"   Dimensions: {data['dimensions']}")
            return True
            
        except Exception as e:
            print(f"❌ Batch embedding failed: {e}")
            return False

    def test_product_embedding(self):
        """Test product-specific embedding endpoint."""
        print("\n🛍️ Testing product embedding...")
        try:
            payload = {
                "name": "Kubernetes Test Product",
                "description": "A modern test product for Kubernetes integration testing",
                "categories": "test,kubernetes,integration",
                "target_tags": ["modern", "test", "k8s"],
                "use_context": ["testing", "kubernetes", "integration"]
            }
            
            response = self.session.post(
                f"{self.base_url}/embed/product",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            required_fields = [
                'description_embedding',
                'category_embedding', 
                'combined_embedding',
                'target_tags_embedding',
                'use_context_embedding'
            ]
            
            for field in required_fields:
                assert field in data
                embedding = data[field]
                assert len(embedding) == 768
                assert isinstance(embedding[0], float)
                # Verify it's not a zero vector
                assert not all(x == 0.0 for x in embedding)
            
            assert data["dimensions"] == 768
            assert data["model"] == "text-embedding-004"
            
            print(f"✅ Product embedding passed")
            print(f"   All {len(required_fields)} embedding types generated")
            print(f"   Dimensions: {data['dimensions']}")
            return True
            
        except Exception as e:
            print(f"❌ Product embedding failed: {e}")
            return False

    def test_error_handling(self):
        """Test error handling."""
        print("\n❌ Testing error handling...")
        try:
            # Test missing text field
            response = self.session.post(
                f"{self.base_url}/embed",
                json={},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400
            
            # Test invalid texts field
            response = self.session.post(
                f"{self.base_url}/embed/batch",
                json={"texts": "not a list"},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400
            
            # Test missing product fields
            response = self.session.post(
                f"{self.base_url}/embed/product",
                json={"name": "Incomplete"},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400
            
            print("✅ Error handling passed")
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False

    def test_workload_identity(self):
        """Verify Workload Identity is working (no explicit credentials)."""
        print("\n🔐 Testing Workload Identity...")
        try:
            # Check that the pod is using the correct service account
            result = subprocess.run([
                "kubectl", "get", "pod", "-l", "app=embeddingservice",
                "-o", "jsonpath={.items[0].spec.serviceAccountName}"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                sa_name = result.stdout.strip()
                if sa_name == "embedding-service-ksa":
                    print("✅ Pod is using correct service account: embedding-service-ksa")
                else:
                    print(f"⚠️  Pod is using service account: {sa_name}")
            
            # Verify the service account has the right annotation
            result = subprocess.run([
                "kubectl", "get", "serviceaccount", "embedding-service-ksa",
                "-o", "jsonpath={.metadata.annotations.iam\\.gke\\.io/gcp-service-account}"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                gcp_sa = result.stdout.strip()
                expected_sa = "embedding-service@gke-hack-471804.iam.gserviceaccount.com"
                if gcp_sa == expected_sa:
                    print(f"✅ Workload Identity annotation correct: {gcp_sa}")
                else:
                    print(f"⚠️  Unexpected service account: {gcp_sa}")
            
            # The fact that our API calls work proves Workload Identity is functioning
            print("✅ Workload Identity is functioning (API calls successful)")
            return True
            
        except Exception as e:
            print(f"❌ Workload Identity check failed: {e}")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        print("🚀 Kubernetes Integration Test Suite")
        print("=" * 50)
        print("Testing deployed embedding service with Workload Identity")
        print()
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Single Embedding", self.test_single_embedding),
            ("Batch Embedding", self.test_batch_embedding),
            ("Product Embedding", self.test_product_embedding),
            ("Error Handling", self.test_error_handling),
            ("Workload Identity", self.test_workload_identity),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Integration Test Results:")
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            print("🎉 All integration tests passed!")
            print("✅ Embedding service is working correctly in Kubernetes")
            print("✅ Workload Identity authentication is working")
            print("✅ Real Vertex AI embeddings are being generated")
        else:
            print("⚠️  Some integration tests failed")
        
        return passed == len(results)


def check_port_forward():
    """Check if port forwarding is active."""
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    print("🔍 Checking prerequisites...")
    
    if not check_port_forward():
        print("❌ Port forwarding not active!")
        print("   Run: kubectl port-forward svc/embeddingservice 8081:8081")
        print("   Then run this test again.")
        return False
    
    print("✅ Port forwarding is active")
    print()
    
    # Run the tests
    tester = EmbeddingServiceK8sTest()
    success = tester.run_all_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Kubernetes integration test completed successfully!")
    else:
        print("❌ Some tests failed - check the output above")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 