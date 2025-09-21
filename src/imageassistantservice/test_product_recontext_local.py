#!/usr/bin/env python3

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from product_visualizer_recontext import ProductVisualizerRecontext
from models import VisualizeProductRequest

async def test_direct_product_recontext():
    """Test product visualization using Vertex AI Imagen 3.0 Editing & Customization."""
    print("🎨 Testing Direct Imagen 3.0 Editing Visualization...")
    
    visualizer = ProductVisualizerRecontext()
    
    # Test with sample images (using publicly available images)
    base_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Room scene
    product_image_url = "https://postersbase.com/cdn/shop/files/1_ad98f783-e827-49e8-bd31-c46e82bddc80.png?v=1715679997&width=1080"  # Chair
    
    request = VisualizeProductRequest(
        base_image_url=base_image_url,
        product_image_url=product_image_url,
        prompt="Seamlessly integrate this poster into the room scene with natural placement and realistic lighting"
    )
    
    try:
        print("   🧠 Generating visualization with Imagen 3.0 Editing...")
        print(f"   📸 Base scene: {base_image_url}")
        print(f"   🪑 Product: {product_image_url}")
        
        result = await visualizer.visualize_product(request)
        
        print(f"✅ Imagen 3.0 Editing Visualization successful!")
        print(f"   Render URL: {result.render_url}")
        if result.metadata:
            print(f"   Processing time: {result.metadata.latency_ms}ms")
            print(f"   Seed: {result.metadata.seed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Imagen 3.0 Editing Visualization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """Test environment configuration for Product Recontext."""
    print("⚙️  Testing Environment Configuration for Product Recontext...")
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'GOOGLE_CLOUD_REGION', 
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GCS_RENDERS_BUCKET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value if var not in ['GOOGLE_APPLICATION_CREDENTIALS'] else '***masked***'
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
    """Run Imagen 3.0 Editing test."""
    print("🚀 Image Assistant Service - Imagen 3.0 Editing Test")
    print("=" * 70)
    print("🧪 Testing Vertex AI Imagen 3.0 Editing vs Gemini+Imagen approach")
    print("=" * 70)
    
    # Test environment
    if not test_environment():
        print("\n❌ Environment configuration failed. Please check your .env file.")
        print("\n🔧 Setup requirements:")
        print("   1. Run setup-local.sh to configure GCP resources")
        print("   2. Ensure Vertex AI API is enabled")
        print("   3. Request access to Product Recontext preview model")
        print("   4. Upload test images to GCS for testing")
        return
    
    print("\n" + "=" * 70)
    
    # Test Imagen 3.0 Editing visualization
    recontext_success = await test_direct_product_recontext()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   Environment: ✅")
    print(f"   Imagen 3.0 Editing Visualization: {'✅' if recontext_success else '❌'}")
    
    if recontext_success:
        print("\n🎉 Imagen 3.0 Editing test passed!")

    else:
        print("\n⚠️  Product Recontext test failed. Check error messages above.")


if __name__ == "__main__":
    # Check if we're in the virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
    else:
        print("⚠️  Not in virtual environment. Activate with: source env/bin/activate")
    
    asyncio.run(main()) 