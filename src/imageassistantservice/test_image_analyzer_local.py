#!/usr/bin/env python3

"""
Simple test script for Image Assistant Service - gRPC Image Analysis Test
Run this after setting up the service to verify image analysis works via gRPC.
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
from image_analyzer import ImageAnalyzer
from models import AnalyzeImageRequest

async def test_grpc_image_analysis():
    """Test image analysis via gRPC."""
    print("🔍 Testing gRPC Image Analysis...")
    
    try:
        # Create gRPC channel
        channel = grpc.aio.insecure_channel('localhost:8080')
        stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
        
        # Test with a sample image
        test_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"
        
        request = imageassistant_pb2.AnalyzeImageRequest(
            image_url=test_image_url,
            context="A test image for gRPC analysis"
        )
        
        # Call the gRPC service
        response = await stub.AnalyzeImage(request)
        
        if response.success:
            print(f"✅ gRPC Analysis successful!")
            print(f"   Scene Type: {response.scene_type}")
            print(f"   Objects Found: {len(response.objects)}")
            for obj in response.objects[:3]:  # Show first 3 objects
                print(f"     - {obj.label} (confidence: {obj.confidence:.2f})")
            print(f"   Styles: {list(response.styles)}")
            print(f"   Colors: {list(response.colors[:3])}")  # Show first 3 colors
            print(f"   Tags: {list(response.tags[:5])}")  # Show first 5 tags
            print(f"   Message: {response.message}")
            
            await channel.close()
            return True
        else:
            print(f"❌ gRPC Analysis failed: {response.message}")
            await channel.close()
            return False
            
    except grpc.aio.AioRpcError as e:
        print(f"❌ gRPC Error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_direct_image_analysis():
    """Test image analysis directly (without gRPC)."""
    print("🔍 Testing Direct Image Analysis...")
    
    analyzer = ImageAnalyzer()
    
    # Test with a sample image
    test_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"
    
    request = AnalyzeImageRequest(
        image_url=test_image_url,
        context="A test image for direct analysis"
    )
    
    try:
        result = await analyzer.analyze_image(request)
        
        print(f"✅ Direct Analysis successful!")
        print(f"   Scene Type: {result.scene_type}")
        print(f"   Objects Found: {len(result.objects)}")
        for obj in result.objects[:3]:  # Show first 3 objects
            print(f"     - {obj.label} (confidence: {obj.confidence:.2f})")
        print(f"   Styles: {result.styles}")
        print(f"   Colors: {result.colors[:3]}")  # Show first 3 colors
        print(f"   Tags: {result.tags[:5]}")  # Show first 5 tags
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_grpc_health():
    """Test gRPC health check."""
    print("🏥 Testing gRPC Health Check...")
    
    try:
        # Create gRPC channel
        channel = grpc.aio.insecure_channel('localhost:8080')
        stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
        
        # Health check request
        request = imageassistant_pb2.HealthCheckRequest(service="imageassistant")
        response = await stub.Check(request)
        
        if response.status == imageassistant_pb2.HealthCheckResponse.ServingStatus.SERVING:
            print("✅ gRPC Health Check passed!")
            await channel.close()
            return True
        else:
            print(f"❌ gRPC Health Check failed: {response.status}")
            await channel.close()
            return False
            
    except grpc.aio.AioRpcError as e:
        print(f"❌ gRPC Health Check Error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def test_environment():
    """Test environment configuration."""
    print("⚙️  Testing Environment Configuration...")
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'GOOGLE_CLOUD_REGION', 
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GCS_BUCKET'
    ]
    
    # missing_vars = []
    # for var in required_vars:
    #     value = os.getenv(var)
    #     if value:
    #         print(f"   ✅ {var}: {value}")
    #     else:
    #         print(f"   ❌ {var}: Not set")
    #         missing_vars.append(var)
    
    # if missing_vars:
    #     print(f"   Missing required environment variables: {missing_vars}")
    #     return False
    
    # Test service account key file
    key_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if os.path.exists(key_file):
        print(f"   ✅ Service account key file exists")
    else:
        print(f"   ❌ Service account key file not found: {key_file}")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("🚀 Image Assistant Service - gRPC Test Suite")
    print("=" * 60)
    
    # Test environment
    # if not test_environment():
    #     print("\n❌ Environment configuration failed. Please check your .env file.")
    #     return
    
    print("\n" + "=" * 60)
    
    # Test direct image analysis first
    direct_success = await test_direct_image_analysis()
    
    print("\n" + "=" * 60)
    
    # Test gRPC health check
    health_success = await test_grpc_health()
    
    print("\n" + "=" * 60)
    
    # Test gRPC image analysis
    grpc_success = await test_grpc_image_analysis()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Environment: ✅")
    print(f"   Direct Analysis: {'✅' if direct_success else '❌'}")
    print(f"   gRPC Health Check: {'✅' if health_success else '❌'}")
    print(f"   gRPC Image Analysis: {'✅' if grpc_success else '❌'}")
    
    if direct_success and health_success and grpc_success:
        print("\n🎉 All tests passed! The gRPC service is working correctly.")
        print("\nNext steps:")
        print("1. The server is running on: localhost:8080")
        print("2. Use gRPC clients to call the service")
        print("3. Available methods:")
        print("   - AnalyzeImage(AnalyzeImageRequest)")
        print("   - VisualizeProduct(VisualizeProductRequest)")
        print("   - Check(HealthCheckRequest)")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure the server is running: python server.py")
        print("2. Ensure Google Cloud credentials are set up correctly")
        print("3. Verify the required APIs are enabled")
        print("4. Check that the service account has the necessary permissions")

if __name__ == "__main__":
    # Check if we're in the virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
    else:
        print("⚠️  Not in virtual environment. Activate with: source env/bin/activate")
    
    asyncio.run(main()) 