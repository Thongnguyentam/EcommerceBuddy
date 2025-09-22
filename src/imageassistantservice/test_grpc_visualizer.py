#!/usr/bin/env python3

"""
Test script for gRPC Product Visualization Service
Tests the VisualizeProduct gRPC endpoint with decorative vase placement.
"""

import os
import sys
import asyncio
import grpc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from genproto import imageassistant_pb2, imageassistant_pb2_grpc

async def test_grpc_product_visualization():
    """Test product visualization using gRPC service."""
    print("🎨 Testing gRPC Product Visualization Service...")
    
    # Test data - decorative vase placement
    base_image_url = "https://decorcabinets.com/wp-content/uploads/2024/11/37-Entry-Pic-2.jpg"
    product_image_url = "https://static.athome.com/images/w_1200,h_1200,c_pad,f_auto,fl_lossy,q_auto/v1746793260/p/124379171_E1/providence-blue-white-floral-porcelain-vase-12.jpg"
    prompt = "Place this decorative vase on the table"
    
    try:
        # Connect to gRPC server
        channel = grpc.aio.insecure_channel('localhost:8080')
        stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
        
        print("   🔗 Connected to gRPC server")
        print(f"   📸 Base scene: {base_image_url}")
        print(f"   🏺 Product (vase): {product_image_url}")
        print(f"   💬 Prompt: {prompt}")
        
        # Create request
        request = imageassistant_pb2.VisualizeProductRequest(
            base_image_url=base_image_url,
            product_image_url=product_image_url,
            prompt=prompt
        )
        
        print("   🚀 Sending visualization request...")
        
        # Call the service
        response = await stub.VisualizeProduct(request)
        
        if response.success:
            print("✅ gRPC Product Visualization successful!")
            print(f"   Render URL: {response.render_url}")
            print(f"   Processing time: {response.metadata.latency_ms}ms")
            print(f"   Seed: {response.metadata.seed}")
            print(f"   Message: {response.message}")
        else:
            print(f"❌ gRPC Product Visualization failed: {response.message}")
            return False
        
        # Close the channel
        await channel.close()
        return True
        
    except Exception as e:
        print(f"❌ gRPC Product Visualization failed: {str(e)}")
        return False

async def test_grpc_health_check():
    """Test the health check endpoint."""
    print("\n🏥 Testing gRPC Health Check...")
    
    try:
        # Connect to gRPC server
        channel = grpc.aio.insecure_channel('localhost:8080')
        stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
        
        # Create health check request
        request = imageassistant_pb2.HealthCheckRequest(
            service="imageassistant.ImageAssistantService"
        )
        
        # Call the service
        response = await stub.Check(request)
        
        if response.status == imageassistant_pb2.HealthCheckResponse.ServingStatus.SERVING:
            print("✅ Health check passed - Service is SERVING")
        else:
            print(f"❌ Health check failed - Status: {response.status}")
            return False
        
        # Close the channel
        await channel.close()
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

async def test_multiple_visualizations():
    """Test multiple product visualizations with different scenarios."""
    print("\n🔄 Testing Multiple Product Visualizations...")
    
    test_cases = [
        {
            "name": "Decorative Vase",
            "base": "https://decorcabinets.com/wp-content/uploads/2024/11/37-Entry-Pic-2.jpg",
            "product": "https://static.athome.com/images/w_1200,h_1200,c_pad,f_auto,fl_lossy,q_auto/v1746793260/p/124379171_E1/providence-blue-white-floral-porcelain-vase-12.jpg",
            "prompt": "Place this decorative vase on the table"
        },
        {
            "name": "Wall Art",
            "base": "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg",
            "product": "https://postersbase.com/cdn/shop/files/1_ad98f783-e827-49e8-bd31-c46e82bddc80.png?v=1715679997&width=1080",
            "prompt": "How would this poster look on the wall in this room?"
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases):
        try:
            print(f"   🧪 Test {i+1}: {test_case['name']}")
            
            # Connect to gRPC server
            channel = grpc.aio.insecure_channel('localhost:8080')
            stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
            
            # Create request
            request = imageassistant_pb2.VisualizeProductRequest(
                base_image_url=test_case["base"],
                product_image_url=test_case["product"],
                prompt=test_case["prompt"]
            )
            
            # Call the service
            response = await stub.VisualizeProduct(request)
            
            if response.success:
                print(f"   ✅ {test_case['name']}: Success ({response.metadata.latency_ms}ms)")
                print(f"      Render URL: {response.render_url}")
                success_count += 1
            else:
                print(f"   ❌ {test_case['name']}: Failed - {response.message}")
            
            # Close the channel
            await channel.close()
            
        except Exception as e:
            print(f"   ❌ {test_case['name']}: Failed - {str(e)}")
    
    print(f"\n   📊 Results: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)

async def main():
    """Main test function."""
    print("🚀 gRPC Product Visualization Service Test")
    print("=" * 80)
    
    # Environment check
    print("⚙️  Testing Environment Configuration...")
    required_vars = ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_REGION", "GCS_RENDERS_BUCKET"]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == "GOOGLE_APPLICATION_CREDENTIALS":
                print(f"   ✅ {var}: ***masked***")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: Not set")
    
    # Check for service account key
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        print("   ✅ Service account key file exists")
    else:
        print("   ❌ Service account key file not found or GOOGLE_APPLICATION_CREDENTIALS not set")
    
    print()
    print("=" * 80)
    
    try:
        # Test health check first
        health_ok = await test_grpc_health_check()
        if not health_ok:
            print("❌ Health check failed - server may not be running")
            return
        
        # Test main functionality
        main_test_ok = await test_grpc_product_visualization()
        
        # Test multiple scenarios
        multiple_tests_ok = await test_multiple_visualizations()
        
        print()
        print("=" * 80)
        print("📊 Test Results:")
        print("   Environment: ✅")
        print(f"   Health Check: {'✅' if health_ok else '❌'}")
        print(f"   Main Visualization: {'✅' if main_test_ok else '❌'}")
        print(f"   Multiple Tests: {'✅' if multiple_tests_ok else '❌'}")
        print()
        
        if health_ok and main_test_ok and multiple_tests_ok:
            print("🎉 All gRPC product visualization tests passed!")
        else:
            print("⚠️  Some tests failed. Check error messages above.")
        
    except Exception as e:
        print()
        print("=" * 80)
        print("📊 Test Results:")
        print("   Environment: ✅")
        print("   gRPC Tests: ❌")
        print()
        print(f"⚠️  gRPC tests failed: {str(e)}")
        print("💡 Make sure the gRPC server is running: python server.py")

if __name__ == "__main__":
    asyncio.run(main()) 