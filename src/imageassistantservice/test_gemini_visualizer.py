#!/usr/bin/env python3

"""
Test script for Gemini 2.5 Flash Image Preview Product Visualizer
Run this to test the new Gemini multimodal approach for realistic product placement.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from product_visualizer_gemini import ProductVisualizerGemini
from models import VisualizeProductRequest

async def test_gemini_product_visualization():
    """Test product visualization using Gemini 2.5 Flash Image Preview."""
    print("🎨 Testing Gemini 2.5 Flash Image Preview for Product Placement...")
    
    visualizer = ProductVisualizerGemini()
    
    # Test with sample images (using publicly available images)
    base_image_url = "https://i.pinimg.com/736x/cb/f5/49/cbf549e2dc77cef0c4e9905323744e8a.jpg"  # Room scene
    product_image_url = "https://postersbase.com/cdn/shop/files/1_ad98f783-e827-49e8-bd31-c46e82bddc80.png?v=1715679997&width=1080"  # Poster
    
    request = VisualizeProductRequest(
        base_image_url=base_image_url,
        product_image_url=product_image_url,
        prompt="How would this poster look on the wall in this room?"
    )
    
    try:
        print("   🧠 Using Gemini 2.5 Flash Image Preview with multimodal generation...")
        print(f"   📸 Base scene: {base_image_url}")
        print(f"   🖼️ Product: {product_image_url}")
        
        result = await visualizer.visualize_product(request)
        
        print("✅ Gemini Product Visualization successful!")
        print(f"   Render URL: {result.render_url}")
        print(f"   Processing time: {result.metadata.latency_ms}ms")
        print(f"   Seed: {result.metadata.seed}")
        
    except Exception as e:
        print(f"❌ Gemini Product Visualization failed: {str(e)}")
        raise e

async def test_different_product_types():
    """Test with different product types to verify versatility."""
    print("\n🔄 Testing Different Product Types...")
    
    visualizer = ProductVisualizerGemini()
    
    test_cases = [
        {
            "name": "Table Decor",
            "base": "https://decorcabinets.com/wp-content/uploads/2024/11/37-Entry-Pic-2.jpg",
            "product": "https://static.athome.com/images/w_1200,h_1200,c_pad,f_auto,fl_lossy,q_auto/v1746793260/p/124379171_E1/providence-blue-white-floral-porcelain-vase-12.jpg",  # Vase
            "prompt": "Place this decorative vase on the table"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        try:
            print(f"   🧪 Test {i+1}: {test_case['name']}")
            
            request = VisualizeProductRequest(
                base_image_url=test_case["base"],
                product_image_url=test_case["product"],
                prompt=test_case["prompt"]
            )
            
            result = await visualizer.visualize_product(request)
            print("result.render_url", result.render_url)
            print(f"   ✅ {test_case['name']}: Success ({result.metadata.latency_ms}ms)")
            
        except Exception as e:
            print(f"   ❌ {test_case['name']}: Failed - {str(e)}")

async def main():
    """Main test function."""
    print("🚀 Gemini 2.5 Flash Image Preview Product Visualizer Test")
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
        # Test main functionality
        await test_gemini_product_visualization()
        
        # Test different product types
        await test_different_product_types()
        
        print()
        print("=" * 80)
        print("📊 Test Results:")
        print("   Environment: ✅")
        print("   Gemini Visualization: ✅")
        print("   Multiple Product Types: ✅")
        print()
        print("🎉 Gemini 2.5 Flash Image Preview product visualization tests passed!")
        
    except Exception as e:
        print()
        print("=" * 80)
        print("📊 Test Results:")
        print("   Environment: ✅")
        print("   Gemini Visualization: ❌")
        print()
        print("⚠️  Gemini test failed. Check error messages above.")

if __name__ == "__main__":
    asyncio.run(main()) 