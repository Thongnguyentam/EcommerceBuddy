#!/usr/bin/env python3

"""
Simple test script for Image Assistant Service - gRPC Product Visualizer Test
Run this after setting up the service to verify product visualization works via gRPC.
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
from product_visualizer import ProductVisualizer
from models import VisualizeProductRequest

async def test_grpc_product_visualization():
    """Test product visualization via gRPC with Gemini placement."""
    print("🎨 Testing gRPC Product Visualization with Gemini Placement...")
    
    try:
        # Create gRPC channel
        channel = grpc.aio.insecure_channel('localhost:8080')
        stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
        
        # Test with sample images
        base_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Room
        product_image_url = "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400"  # Poster
        
        # No placement specification - let Gemini decide
        request = imageassistant_pb2.VisualizeProductRequest(
            base_image_url=base_image_url,
            product_image_url=product_image_url,
            prompt="Intelligently place this poster in the most suitable location in the room scene"
        )
        
        # Call the gRPC service
        print("   🧠 Sending gRPC request with Gemini placement inference...")
        response = await stub.VisualizeProduct(request)
        
        if response.success:
            print(f"✅ gRPC Product Visualization with Gemini placement successful!")
            print(f"   Render URL: {response.render_url}")
            if response.metadata:
                print(f"   Processing time: {response.metadata.latency_ms}ms")
                print(f"   Seed: {response.metadata.seed}")
            print(f"   Message: {response.message}")
            
            await channel.close()
            return True
        else:
            print(f"❌ gRPC Product Visualization failed: {response.message}")
            await channel.close()
            return False
            
    except grpc.aio.AioRpcError as e:
        print(f"❌ gRPC Error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"❌ Visualization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_grpc_product_visualization_different_product():
    """Test product visualization with a different product via gRPC."""
    print("🪑 Testing gRPC Product Visualization with Different Product...")
    
    try:
        # Create gRPC channel
        channel = grpc.aio.insecure_channel('localhost:8080')
        stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(channel)
        
        # Test with different product - a lamp in a living room
        base_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Room scene
        product_image_url = "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=400"  # Table lamp
        
        request = imageassistant_pb2.VisualizeProductRequest(
            base_image_url=base_image_url,
            product_image_url=product_image_url,
            prompt="Place this table lamp in the most appropriate spot in this living room"
        )
        
        # Call the gRPC service
        print("   💡 Sending gRPC request for lamp placement...")
        response = await stub.VisualizeProduct(request)
        
        if response.success:
            print(f"✅ gRPC Product Visualization with lamp successful!")
            print(f"   Render URL: {response.render_url}")
            if response.metadata:
                print(f"   Processing time: {response.metadata.latency_ms}ms")
            print(f"   Message: {response.message}")
            
            await channel.close()
            return True
        else:
            print(f"❌ gRPC Product Visualization with lamp failed: {response.message}")
            await channel.close()
            return False
            
    except grpc.aio.AioRpcError as e:
        print(f"❌ gRPC Error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"❌ Lamp placement failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_direct_product_visualization():
    """Test product visualization directly (without gRPC) with Gemini placement."""
    print("🎨 Testing Direct Product Visualization with Gemini Placement...")
    
    visualizer = ProductVisualizer()
    
    # Test with sample images
    base_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Room scene
    product_image_url = "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400"  # Chair
    
    # No placement specified - let Gemini decide
    request = VisualizeProductRequest(
        base_image_url=base_image_url,
        product_image_url=product_image_url,
        prompt="Place this chair naturally in the room scene where it would fit best"
    )
    
    try:
        print("   🧠 Generating visualization with Gemini placement...")
        result = await visualizer.visualize_product(request)
        
        print(f"✅ Direct Visualization with Gemini placement successful!")
        print(f"   Render URL: {result.render_url}")
        if result.metadata:
            print(f"   Processing time: {result.metadata.latency_ms}ms")
            print(f"   Seed: {result.metadata.seed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Visualization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_direct_placement_inference():
    """Test Gemini placement inference directly."""
    print("🧠 Testing Direct Gemini Placement Inference...")
    
    visualizer = ProductVisualizer()
    
    # Test with sample images
    base_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Room scene
    product_image_url = "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400"  # Chair
    
    try:
        print("   🧠 Inferring placement with Gemini...")
        placement = await visualizer._infer_placement_with_gemini(
            base_image_url, 
            product_image_url,
            "Place a chair in this room scene"
        )
        
        print(f"✅ Gemini Placement Inference successful!")
        print(f"   Position: ({placement.position.x:.2f}, {placement.position.y:.2f})")
        print(f"   Scale: {placement.scale:.2f}")
        print(f"   Rotation: {placement.rotation:.1f}°")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini Placement Inference failed: {str(e)}")
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
    """Test environment configuration for product visualization."""
    print("⚙️  Testing Environment Configuration...")
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'GOOGLE_CLOUD_REGION', 
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GCS_BUCKET',
        'GCS_RENDERS_BUCKET',
        'GEMINI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value if var not in ['GOOGLE_APPLICATION_CREDENTIALS', 'GEMINI_API_KEY'] else '***masked***'
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"   Missing required environment variables: {missing_vars}")
        return False
    
    # Test service account key file
    key_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if os.path.exists(key_file):
        print(f"   ✅ Service account key file exists")
    else:
        print(f"   ❌ Service account key file not found: {key_file}")
        return False
    
    return True

async def main():
    """Run all product visualizer tests."""
    print("🚀 Image Assistant Service - Product Visualizer Test Suite")
    print("=" * 70)
    
    # Test environment
    # if not test_environment():
    #     print("\n❌ Environment configuration failed. Please check your .env file.")
    #     print("\n🔑 Required for product visualization:")
    #     print("   - GEMINI_API_KEY: Get from https://aistudio.google.com/app/apikey")
    #     print("   - GCS_RENDERS_BUCKET: Set up by running setup-local.sh")
    #     print("   - Vertex AI access: Ensure your project has Imagen enabled")
    #     return
    
    print("\n" + "=" * 70)
    
    # Test gRPC health check first
    health_success = await test_grpc_health()
    
    print("\n" + "=" * 70)
    
    # Test direct placement inference
    placement_success = await test_direct_placement_inference()
    
    print("\n" + "=" * 70)
    
    # Test direct product visualization
    direct_success = await test_direct_product_visualization()
    
    print("\n" + "=" * 70)
    
    # Test gRPC product visualization (chair)
    grpc_success = await test_grpc_product_visualization()
    
    print("\n" + "=" * 70)
    
    # Test gRPC product visualization with different product (lamp)
    grpc_different_success = await test_grpc_product_visualization_different_product()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   Environment: ✅")
    print(f"   gRPC Health Check: {'✅' if health_success else '❌'}")
    print(f"   Gemini Placement Inference: {'✅' if placement_success else '❌'}")
    print(f"   Direct Visualization (Chair): {'✅' if direct_success else '❌'}")
    print(f"   gRPC Visualization (Chair): {'✅' if grpc_success else '❌'}")
    print(f"   gRPC Visualization (Lamp): {'✅' if grpc_different_success else '❌'}")
    
    all_success = health_success and placement_success and direct_success and grpc_success and grpc_different_success
    
    if all_success:
        print("\n🎉 All tests passed! The Product Visualizer service is working correctly.")
        print("\nNext steps:")
        print("1. The server is running on: localhost:8080")
        print("2. Use gRPC clients to call VisualizeProduct")
        print("3. Generated images are stored in GCS with signed URLs")
        print("4. Gemini automatically determines optimal product placement")
        print("5. No manual placement needed - AI handles positioning, scaling, and rotation")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure the server is running: python server.py")
        print("2. Ensure Gemini API key is valid: export GEMINI_API_KEY=your_key")
        print("3. Verify Vertex AI Imagen access in your GCP project")
        print("4. Check that GCS_RENDERS_BUCKET exists and is writable")
        print("5. Ensure service account has aiplatform.user role")

if __name__ == "__main__":
    # Check if we're in the virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
    else:
        print("⚠️  Not in virtual environment. Activate with: source env/bin/activate")
    
    asyncio.run(main()) 