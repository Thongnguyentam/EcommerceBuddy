import os
import logging
import asyncio
import time
import uuid
from typing import Optional
from datetime import datetime, timedelta
import vertexai
from vertexai.preview.vision_models import Image as VertexImage, ImageGenerationModel
from google.cloud import storage
from google import genai

from models import (
    VisualizeProductRequest, VisualizeProductResponse, 
    ProductPlacement, RenderMetadata, Position
)

logger = logging.getLogger(__name__)

class ProductVisualizerSimple:
    """Service for visualizing products using Vertex AI Imagen 3 direct product placement."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.renders_bucket = os.getenv("GCS_RENDERS_BUCKET")
        self.storage_client = None
        self.imagen_model = None
        self.gemini_client = None
        
        # Initialize services
        if self.project_id:
            try:
                # Initialize Vertex AI
                vertexai.init(project=self.project_id, location=self.location)
                
                # Initialize Imagen model for product placement
                self.imagen_model = ImageGenerationModel.from_pretrained("imagegeneration@006")
                logger.info("✅ Initialized Imagen model for product placement")
                
                # Initialize Gemini for placement analysis
                self.gemini_client = genai.Client(vertexai=True, project=self.project_id, location=self.location)
                logger.info("✅ Initialized Gemini client for placement analysis")
                
                # Initialize GCS client for render storage
                self.storage_client = storage.Client()
                logger.info("✅ Initialized GCS client for render storage")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vertex AI services: {str(e)}")
    
    async def _upload_to_gcs_and_get_signed_url(self, image_data: bytes) -> str:
        """Upload generated image to GCS renders bucket and return a signed URL."""
        if not self.storage_client or not self.renders_bucket:
            raise Exception("GCS storage not configured. Please ensure GCS_RENDERS_BUCKET is set.")
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"simple_renders/{timestamp}_{unique_id}.jpg"
            
            # Get bucket and create blob
            bucket = self.storage_client.bucket(self.renders_bucket)
            blob = bucket.blob(filename)
            
            # Upload image data
            blob.upload_from_string(image_data, content_type='image/jpeg')
            logger.info(f"✅ Uploaded simple render to GCS: gs://{self.renders_bucket}/{filename}")
            
            # Generate signed URL (valid for 1 hour)
            signed_url = blob.generate_signed_url(
                expiration=datetime.utcnow() + timedelta(hours=1),
                method='GET'
            )
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {str(e)}")
            raise Exception(f"Failed to upload generated image to storage: {str(e)}")
    
    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL."""
        try:
            import requests
            def _download():
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                return response.content
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _download)
        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {str(e)}")
            raise Exception(f"Failed to download image: {str(e)}")

    async def _create_placement_prompt(self, base_image_url: str, product_image_url: str, 
                                     context: Optional[str] = None,
                                     base_dimensions: tuple = None, product_dimensions: tuple = None) -> str:
        """Use Gemini to create an intelligent placement prompt."""
        if not self.gemini_client:
            logger.warning("Gemini client not available, using generic prompt")
            return "Place the product naturally in the scene with realistic lighting and shadows."
        
        try:
            # Prepare dimension information
            dimension_info = ""
            if base_dimensions and product_dimensions:
                base_w, base_h = base_dimensions
                prod_w, prod_h = product_dimensions
                size_ratio = (prod_w * prod_h) / (base_w * base_h)
                
                dimension_info = f"""
                
            Image Analysis:
            - Base scene: {base_w}x{base_h} pixels
            - Product: {prod_w}x{prod_h} pixels  
            - Size ratio: {size_ratio:.2f}x
            """
            
            # Create prompt for Gemini to analyze placement
            analysis_prompt = f"""
            You are an expert in product placement and scene composition. Analyze these images and create a detailed prompt for placing the product realistically in the base scene.

            Base scene: {base_image_url}
            Product: {product_image_url}
            Context: {context or "Product placement for realistic visualization"}
            {dimension_info}

            Consider:
            1. Scene lighting and atmosphere
            2. Appropriate surfaces and placement locations
            3. Scale and proportions
            4. Shadows and reflections
            5. Perspective and depth
            6. Overall composition and balance

            Create a detailed placement prompt that describes:
            - WHERE the product should be placed
            - HOW it should look (lighting, shadows, scale)
            - WHAT adjustments are needed for realism

            Return only the placement prompt text, no additional formatting.
            """

            def _call_gemini():
                return self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=analysis_prompt
                )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call_gemini)
            
            placement_prompt = response.text.strip()
            logger.info(f"Generated intelligent placement prompt: {placement_prompt[:100]}...")
            return placement_prompt
            
        except Exception as e:
            logger.warning(f"Gemini prompt generation failed: {str(e)}, using fallback")
            return "Place the product naturally in the scene with realistic lighting, appropriate shadows, and proper scale to match the environment."

    async def _generate_with_imagen_product_placement(self, base_image_url: str, product_image_url: str, 
                                                    placement_prompt: str) -> str:
        """Generate product visualization using Imagen 3 with simple prompt-based generation."""
        if not self.imagen_model:
            raise Exception("Imagen model not available. Please ensure Vertex AI is properly configured.")
        
        try:
            # Download base image
            base_image_bytes = await self._download_image(base_image_url)
            
            # Create Vertex AI Image object for base image
            base_vertex_image = VertexImage(base_image_bytes)
            
            # Create comprehensive prompt that includes product description
            comprehensive_prompt = f"""
            {placement_prompt}
            
            Add the product from this reference naturally into the scene.
            Product reference: {product_image_url}
            
            Place the product with:
            - Realistic lighting that matches the scene
            - Appropriate shadows and reflections
            - Proper scale and perspective
            - Natural positioning that fits the environment
            - Photorealistic integration
            """
            
            # Use Imagen 3 for image generation with prompt
            def _call_imagen():
                return self.imagen_model.generate_images(
                    prompt=comprehensive_prompt,
                    base_image=base_vertex_image,
                    number_of_images=1
                )
            
            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(None, _call_imagen)
            
            # Extract generated image data
            if not images or len(images) == 0:
                raise Exception("No images generated by Imagen")
            
            generated_image = images[0]
            image_data = generated_image._image_bytes
            
            logger.info(f"Generated product placement using {len(image_data)} bytes")
            
            # Upload to GCS and get signed URL
            render_url = await self._upload_to_gcs_and_get_signed_url(image_data)
            logger.info(f"Generated and uploaded image with Imagen: {render_url}")
            return render_url
                
        except Exception as e:
            logger.error(f"Imagen generation failed: {str(e)}")
            raise Exception(f"Failed to generate visualization with Imagen: {str(e)}")
    
    async def visualize_product(self, request: VisualizeProductRequest) -> VisualizeProductResponse:
        """Visualize product using Imagen 3 direct product placement."""
        try:
            start_time = time.time()
            
            # Get image dimensions for better prompt generation
            logger.info("Analyzing image dimensions...")
            base_image_bytes = await self._download_image(request.base_image_url)
            product_image_bytes = await self._download_image(request.product_image_url)
            
            from PIL import Image
            import io
            base_img = Image.open(io.BytesIO(base_image_bytes))
            product_img = Image.open(io.BytesIO(product_image_bytes))
            base_dimensions = base_img.size
            product_dimensions = product_img.size
            
            logger.info(f"Base image dimensions: {base_dimensions[0]}x{base_dimensions[1]}")
            logger.info(f"Product image dimensions: {product_dimensions[0]}x{product_dimensions[1]}")
            
            # Generate intelligent placement prompt using Gemini
            logger.info("Creating intelligent placement prompt...")
            if request.prompt:
                # Use user's prompt as context for Gemini analysis
                placement_prompt = await self._create_placement_prompt(
                    request.base_image_url,
                    request.product_image_url,
                    request.prompt,
                    base_dimensions,
                    product_dimensions
                )
            else:
                # Generate generic placement prompt
                placement_prompt = "Place the product naturally in the scene with realistic lighting, appropriate shadows, proper scale, and natural positioning that fits the environment and perspective."
            
            # Generate visualization using Imagen 3 product placement
            logger.info("Generating visualization with Imagen 3 product placement...")
            render_url = await self._generate_with_imagen_product_placement(
                request.base_image_url,
                request.product_image_url,
                placement_prompt
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            metadata = RenderMetadata(
                latency_ms=latency_ms,
                seed=None
            )
            
            logger.info(f"Imagen 3 product placement completed in {latency_ms}ms")
            
            return VisualizeProductResponse(
                render_url=render_url,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error visualizing product with Imagen 3 product placement: {str(e)}")
            raise

    async def get_capabilities(self) -> dict:
        """Get information about this visualizer's capabilities."""
        return {
            "method": "imagen_3_product_placement",
            "model": "imagegeneration@006",
            "features": [
                "Direct product placement",
                "Automatic lighting harmonization",
                "Built-in shadow generation", 
                "Perspective correction",
                "No manual masking required",
                "Preserves base scene integrity"
            ],
            "advantages": [
                "Simplest API - single edit_image call",
                "Automatic scene understanding",
                "Professional quality results",
                "Minimal preprocessing needed"
            ],
            "use_cases": [
                "E-commerce product visualization",
                "Advertising and marketing",
                "Interior design previews",
                "Product catalog generation"
            ]
        } 