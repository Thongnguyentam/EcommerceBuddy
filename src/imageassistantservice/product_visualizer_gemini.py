import os
import logging
import asyncio
import time
import json
import uuid
import mimetypes
from typing import Optional
from datetime import datetime, timedelta
import vertexai
from google.cloud import storage

from google import genai
from google.genai import types
import requests
from PIL import Image
import io

from models import (
    VisualizeProductRequest, VisualizeProductResponse, 
    ProductPlacement, RenderMetadata, Position
)

logger = logging.getLogger(__name__)

class ProductVisualizerGemini:
    """Service for visualizing products in user photos using Gemini 2.5 Flash Image Preview."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.renders_bucket = os.getenv("GCS_RENDERS_BUCKET")
        self.storage_client = None
        self.gemini_client = None
        
        # Gemini model configuration for image generation
        self.gemini_model = "gemini-2.5-flash-image-preview"
        
        # Initialize services
        if self.project_id:
            try:
                # Initialize Vertex AI
                vertexai.init(project=self.project_id, location=self.location)
                
                # Initialize GenAI client for Gemini image generation
                self.gemini_client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location="global"  # Gemini models are typically in global location
                )
                logger.info("✅ Initialized Gemini 2.5 Flash Image Preview client")
                
                # Initialize GCS client for render storage
                self.storage_client = storage.Client()
                logger.info("✅ Initialized GCS client for render storage")
                
                logger.info(f"✅ Initialized Gemini model: {self.gemini_model}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini services: {str(e)}")

    def _load_image_bytes_from_data(self, image_bytes: bytes) -> tuple[bytes, str]:
        """Determine MIME type from image bytes."""
        # Try to determine MIME type from image header
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return image_bytes, 'image/jpeg'
        elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return image_bytes, 'image/png'
        elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
            return image_bytes, 'image/gif'
        elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
            return image_bytes, 'image/webp'
        else:
            # Default to JPEG if we can't determine
            return image_bytes, 'image/jpeg'

    async def _upload_to_gcs_and_get_signed_url(self, image_data: bytes) -> str:
        """Upload generated image to GCS renders bucket and return a signed URL."""
        if not self.storage_client or not self.renders_bucket:
            raise Exception("GCS storage not configured. Please ensure GCS_RENDERS_BUCKET is set.")
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"gemini_renders/{timestamp}_{unique_id}.jpg"
            
            # Get bucket and create blob
            bucket = self.storage_client.bucket(self.renders_bucket)
            blob = bucket.blob(filename)
            
            # Upload image data
            blob.upload_from_string(image_data, content_type='image/jpeg')
            logger.info(f"✅ Uploaded Gemini render to GCS: gs://{self.renders_bucket}/{filename}")
            
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
            def _download():
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                return response.content
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _download)
        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {str(e)}")
            raise Exception(f"Failed to download image: {str(e)}")

    async def _analyze_scene_for_placement(self, base_image_bytes: bytes, product_image_bytes: bytes, 
                                         context: Optional[str] = None) -> dict:
        """Use Gemini to analyze the scene and determine optimal placement strategy."""
        if not self.gemini_client:
            raise Exception("Gemini client not available. Please ensure Vertex AI is properly configured.")
        
        try:
            # Get image dimensions for context
            base_image = Image.open(io.BytesIO(base_image_bytes))
            product_image = Image.open(io.BytesIO(product_image_bytes))
            
            base_width, base_height = base_image.size
            product_width, product_height = product_image.size
            
            # Determine MIME types
            base_bytes, base_mime = self._load_image_bytes_from_data(base_image_bytes)
            product_bytes, product_mime = self._load_image_bytes_from_data(product_image_bytes)
            
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze these two images for optimal product placement strategy:
            
            Image 1 (Base Scene): {base_width}x{base_height} pixels
            Image 2 (Product): {product_width}x{product_height} pixels
            Context: {context or "Product placement for realistic visualization"}
            
            Provide detailed analysis in JSON format:
            {{
                "scene_analysis": {{
                    "lighting": "description of lighting conditions",
                    "surfaces": ["list of available placement surfaces"],
                    "perspective": "description of camera angle and depth",
                    "style": "description of scene style/aesthetic"
                }},
                "product_analysis": {{
                    "type": "product category",
                    "size_category": "small/medium/large",
                    "mounting_type": "wall/table/floor/hanging",
                    "aspect_ratio": {product_width/product_height:.2f}
                }},
                "placement_strategy": {{
                    "recommended_surface": "best surface for placement",
                    "size_guidance": "how large the product should appear",
                    "positioning": "where exactly to place it",
                    "lighting_match": "how to match lighting conditions"
                }}
            }}
            """
            
            # Create contents for multimodal analysis
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=base_bytes, mime_type=base_mime),
                        types.Part.from_bytes(data=product_bytes, mime_type=product_mime),
                        types.Part.from_text(text=analysis_prompt),
                    ],
                ),
            ]
            
            # Generate analysis
            def _call_gemini_analysis():
                return self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",  # Use text model for analysis
                    contents=contents
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call_gemini_analysis)
            
            # Parse the response
            text = response.text.strip()
            
            # Clean markdown formatting
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            analysis_data = json.loads(text)
            logger.info(f"Scene analysis completed: {analysis_data.get('placement_strategy', {}).get('recommended_surface', 'N/A')}")
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"Scene analysis failed: {str(e)}")
            # Return default analysis if parsing fails
            return {
                "scene_analysis": {"lighting": "natural", "surfaces": ["wall", "table"], "perspective": "eye level", "style": "modern"},
                "product_analysis": {"type": "artwork", "size_category": "medium", "mounting_type": "wall", "aspect_ratio": 1.0},
                "placement_strategy": {"recommended_surface": "wall", "size_guidance": "medium", "positioning": "center", "lighting_match": "match ambient"}
            }

    async def _create_comprehensive_placement_prompt(self, analysis: dict, user_prompt: str) -> str:
        """Create a comprehensive prompt for realistic product placement."""
        
        scene_info = analysis.get("scene_analysis", {})
        product_info = analysis.get("product_analysis", {})
        strategy = analysis.get("placement_strategy", {})
        
        comprehensive_prompt = f"""
        {user_prompt}
        
        REALISTIC PRODUCT PLACEMENT INSTRUCTIONS:
        
        SCENE CONTEXT:
        - Lighting: {scene_info.get('lighting', 'natural ambient')}
        - Available surfaces: {', '.join(scene_info.get('surfaces', ['wall', 'table']))}
        - Perspective: {scene_info.get('perspective', 'eye level')}
        - Style: {scene_info.get('style', 'modern')}
        
        PRODUCT SPECIFICATIONS:
        - Type: {product_info.get('type', 'product')}
        - Size category: {product_info.get('size_category', 'medium')}
        - Best mounting: {product_info.get('mounting_type', 'wall')}
        - Aspect ratio: {product_info.get('aspect_ratio', 1.0)}
        
        PLACEMENT STRATEGY:
        - Surface: {strategy.get('recommended_surface', 'wall')}
        - Size: {strategy.get('size_guidance', 'appropriately sized for the space')}
        - Position: {strategy.get('positioning', 'naturally positioned')}
        - Lighting: {strategy.get('lighting_match', 'match scene lighting')}
        
        CRITICAL REQUIREMENTS FOR PHOTOREALISTIC INTEGRATION:
        1. EXACT PRODUCT PRESERVATION:
           - Maintain ALL original colors, textures, patterns, and details from the product image
           - Preserve any text, logos, branding, or graphic elements exactly as shown
           - Do not alter, stylize, or reinterpret the product design in any way
        
        2. REALISTIC PHYSICAL INTEGRATION:
           - Scale the product appropriately for the space and viewing distance
           - Position on the recommended surface: {strategy.get('recommended_surface', 'wall')}
           - Match the perspective and viewing angle of the base scene
           - Ensure proper depth and spatial relationships
        
        3. LIGHTING AND SHADOWS:
           - Match the lighting conditions: {scene_info.get('lighting', 'natural ambient')}
           - Add realistic shadows that match the scene's light sources
           - Create proper contact shadows where the product meets surfaces
           - Add subtle reflections or highlights as appropriate for the material
        
        4. SEAMLESS COMPOSITION:
           - Blend edges naturally without visible borders or artifacts
           - Maintain the original scene's atmosphere and mood
           - Ensure the product looks like it was photographed in the original scene
           - Preserve all existing elements and decor in the base scene
        
        5. HIGH QUALITY OUTPUT:
           - Generate at high resolution with sharp details
           - Maintain photographic quality throughout the composition
           - Ensure smooth gradients and natural color transitions
           - Avoid any artificial or computer-generated appearance
        
        FINAL INSTRUCTION: Create a seamless, photorealistic composite where the product from Image 2 
        appears naturally integrated into the scene from Image 1, as if it was always part of the original photograph.
        """
        
        return comprehensive_prompt

    async def _generate_with_gemini_image(self, base_image_url: str, product_image_url: str, 
                                        prompt: str) -> str:
        """Generate product visualization using Gemini 2.5 Flash Image Preview."""
        if not self.gemini_client:
            raise Exception("Gemini client not available. Please ensure Vertex AI is properly configured.")
        
        try:
            # Download images
            base_image_bytes = await self._download_image(base_image_url)
            product_image_bytes = await self._download_image(product_image_url)
            
            # Analyze scene for optimal placement
            logger.info("Analyzing scene for optimal placement...")
            analysis = await self._analyze_scene_for_placement(base_image_bytes, product_image_bytes, prompt)
            
            # Create comprehensive placement prompt
            comprehensive_prompt = await self._create_comprehensive_placement_prompt(analysis, prompt)
            
            # Determine MIME types
            base_bytes, base_mime = self._load_image_bytes_from_data(base_image_bytes)
            product_bytes, product_mime = self._load_image_bytes_from_data(product_image_bytes)
            
            # Create multimodal contents for image generation
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        # Provide the base scene as first image
                        types.Part.from_bytes(data=base_bytes, mime_type=base_mime),
                        # Provide the product as second image
                        types.Part.from_bytes(data=product_bytes, mime_type=product_mime),
                        # Provide the comprehensive placement prompt
                        types.Part.from_text(text=comprehensive_prompt),
                    ],
                ),
            ]
            
            # Configure for image generation
            generate_content_config = types.GenerateContentConfig(
                response_modalities=[
                    "IMAGE",
                    "TEXT",
                ],
            )
            
            # Generate the composite image
            def _call_gemini_image():
                return self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=contents,
                    config=generate_content_config
                )
            
            logger.info("Generating realistic product placement with Gemini 2.5 Flash Image Preview...")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call_gemini_image)
            
            # Extract the generated image
            if not response.candidates or len(response.candidates) == 0:
                raise Exception("No image candidates generated by Gemini")
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise Exception("No content parts in Gemini response")
            
            # Find the image part
            image_part = None
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_part = part
                    break
            
            if not image_part:
                raise Exception("No image data found in Gemini response")
            
            # Extract image bytes
            image_data = image_part.inline_data.data
            
            logger.info(f"Generated realistic product placement using {len(image_data)} bytes")
            
            # Upload to GCS and get signed URL
            render_url = await self._upload_to_gcs_and_get_signed_url(image_data)
            logger.info(f"Generated and uploaded image with Gemini: {render_url}")
            return render_url
                
        except Exception as e:
            logger.error(f"Gemini image generation failed: {str(e)}")
            raise Exception(f"Failed to generate visualization with Gemini: {str(e)}")

    async def visualize_product(self, request: VisualizeProductRequest) -> VisualizeProductResponse:
        """Visualize product in user photo using Gemini 2.5 Flash Image Preview."""
        try:
            start_time = time.time()
            
            # Generate the visualization using Gemini 2.5 Flash Image Preview
            logger.info("Generating visualization with Gemini 2.5 Flash Image Preview...")
            render_url = await self._generate_with_gemini_image(
                request.base_image_url,
                request.product_image_url,
                request.prompt
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            metadata = RenderMetadata(
                latency_ms=latency_ms,
                seed=None  # Gemini doesn't use seeds
            )
            
            logger.info(f"Gemini visualization completed in {latency_ms}ms")
            
            return VisualizeProductResponse(
                render_url=render_url,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error visualizing product with Gemini: {str(e)}")
            raise 