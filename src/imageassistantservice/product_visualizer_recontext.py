import os
import logging
import asyncio
import time
import json
import uuid
from typing import Optional
from datetime import datetime, timedelta
import vertexai
from google.cloud import storage

from google import genai
from google.genai.types import (
    RawReferenceImage,
    MaskReferenceImage,
    MaskReferenceConfig,
    EditImageConfig,
    Image as GenAIImage,
)
import requests
from PIL import Image, ImageDraw
import io

from models import (
    VisualizeProductRequest, VisualizeProductResponse, 
    ProductPlacement, RenderMetadata, Position
)

logger = logging.getLogger(__name__)

class ProductVisualizerRecontext:
    """Service for visualizing products in user photos using Vertex AI Imagen 3.0 Editing & Customization."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.renders_bucket = os.getenv("GCS_RENDERS_BUCKET")
        self.storage_client = None
        self.genai_client = None
        self.gemini_client = None
        
        # Imagen 3.0 Editing & Customization model configuration
        self.imagen_edit_model = "imagen-3.0-capability-001"
        
        # Initialize services
        if self.project_id:
            try:
                # Initialize Vertex AI
                vertexai.init(project=self.project_id, location=self.location)
                
                # Initialize GenAI client for Imagen editing (using Vertex AI)
                self.genai_client = genai.Client(vertexai=True, project=self.project_id, location=self.location)
                logger.info("✅ Initialized GenAI client for Imagen editing")
                
                # Use same client for Gemini placement inference
                self.gemini_client = self.genai_client
                logger.info("✅ Initialized Gemini client for placement inference")
                
                # Initialize GCS client for render storage
                self.storage_client = storage.Client()
                logger.info("✅ Initialized GCS client for render storage")
                
                logger.info(f"✅ Initialized Imagen 3.0 Editing model: {self.imagen_edit_model}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vertex AI Imagen Editing services: {str(e)}")
    
    async def _upload_to_gcs_and_get_signed_url(self, image_data: bytes) -> str:
        """Upload generated image to GCS renders bucket and return a signed URL."""
        if not self.storage_client or not self.renders_bucket:
            raise Exception("GCS storage not configured. Please ensure GCS_RENDERS_BUCKET is set.")
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"recontext_renders/{timestamp}_{unique_id}.jpg"
            
            # Get bucket and create blob
            bucket = self.storage_client.bucket(self.renders_bucket)
            blob = bucket.blob(filename)
            
            # Upload image data
            blob.upload_from_string(image_data, content_type='image/jpeg')
            logger.info(f"✅ Uploaded Product Recontext render to GCS: gs://{self.renders_bucket}/{filename}")
            
            # Generate signed URL (valid for 1 hour)
            signed_url = blob.generate_signed_url(
                expiration=datetime.utcnow() + timedelta(hours=1),
                method='GET'
            )
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {str(e)}")
            raise Exception(f"Failed to upload generated image to storage: {str(e)}")
    
    async def _infer_placement_with_gemini(self, base_image_url: str, product_image_url: str, 
                                         context: Optional[str] = None) -> ProductPlacement:
        """Use Gemini to intelligently infer product placement for mask generation."""
        if not self.gemini_client:
            raise Exception("Gemini client not available. Please ensure Vertex AI is properly configured.")
        
        try:
            # Create a comprehensive prompt for placement analysis
            placement_prompt = f"""
            You are an expert in product placement and 3D spatial reasoning. Analyze these two images and determine the optimal placement for the product in the base scene.

            Base scene image: {base_image_url}
            Product image: {product_image_url}
            Context: {context or "Product placement for realistic visualization"}

            Consider:
            1. Scene depth and perspective
            2. Available surfaces (tables, floors, counters)
            3. Lighting consistency
            4. Realistic scale proportions
            5. Occlusion and shadows
            6. Visual balance and composition

            Return a JSON response with this exact structure:
            {{
                "position": {{"x": 0.0, "y": 0.0}},
                "scale": 0.0,
                "rotation": 0.0,
                "reasoning": "explanation of placement choice",
                "confidence": 0.0
            }}

            Where:
            - position.x, position.y: normalized coordinates (0.0-1.0) for placement center
            - scale: relative size (0.1-2.0, where 1.0 = natural size)
            - rotation: rotation angle in degrees (-180 to 180)
            - reasoning: brief explanation of the placement logic
            - confidence: confidence score (0.0-1.0)

            Focus on realism and natural integration into the scene.
            """

            # Call Gemini for placement analysis
            def _call_gemini():
                return self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=placement_prompt
                )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call_gemini)
            
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
            
            print("============== TEXT: ", text)
            placement_data = json.loads(text)
            
            logger.info(f"Gemini placement reasoning: {placement_data.get('reasoning', 'N/A')}")
            logger.info(f"Gemini confidence: {placement_data.get('confidence', 0.0)}")
            
            return ProductPlacement(
                position=Position(
                    x=float(placement_data["position"]["x"]),
                    y=float(placement_data["position"]["y"])
                ),
                scale=float(placement_data["scale"]),
                rotation=float(placement_data.get("rotation", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Gemini placement inference failed: {str(e)}")
            raise Exception(f"Failed to infer placement with Gemini: {str(e)}")

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

    async def _create_mask(self, base_image_bytes: bytes, placement: ProductPlacement, 
                          product_image_bytes: bytes) -> bytes:
        """Create a mask for the product placement area."""
        try:
            # Load base image to get dimensions
            base_image = Image.open(io.BytesIO(base_image_bytes))
            width, height = base_image.size
            
            # Load product image to get aspect ratio
            product_image = Image.open(io.BytesIO(product_image_bytes))
            product_width, product_height = product_image.size
            product_aspect = product_width / product_height
            
            # Calculate mask dimensions based on placement
            mask_width = int(width * placement.scale * 0.3)  # 30% of image width at scale 1.0
            mask_height = int(mask_width / product_aspect)
            
            # Calculate position
            center_x = int(placement.position.x * width)
            center_y = int(placement.position.y * height)
            
            # Create mask image (white where product should be, black elsewhere)
            mask = Image.new('L', (width, height), 0)  # Black background
            draw = ImageDraw.Draw(mask)
            
            # Draw white rectangle for product area
            left = center_x - mask_width // 2
            top = center_y - mask_height // 2
            right = center_x + mask_width // 2
            bottom = center_y + mask_height // 2
            
            # Ensure bounds are within image
            left = max(0, left)
            top = max(0, top)
            right = min(width, right)
            bottom = min(height, bottom)
            
            draw.rectangle([left, top, right, bottom], fill=255)  # White rectangle
            
            # Convert to bytes
            mask_bytes = io.BytesIO()
            mask.save(mask_bytes, format='PNG')
            mask_bytes.seek(0)
            return mask_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create mask: {str(e)}")
            raise Exception(f"Failed to create mask: {str(e)}")

    async def _generate_with_imagen_editing(self, base_image_url: str, product_image_url: str, 
                                          placement: ProductPlacement, prompt: str) -> str:
        """Generate product visualization using Vertex AI Imagen 3.0 Editing & Customization via Python SDK."""
        if not self.genai_client or not self.project_id:
            raise Exception("GenAI client not available. Please ensure Vertex AI is properly configured.")
        
        try:
            # Download images
            base_image_bytes = await self._download_image(base_image_url)
            product_image_bytes = await self._download_image(product_image_url)
            
            # Create mask based on placement
            mask_bytes = await self._create_mask(base_image_bytes, placement, product_image_bytes)
            
            # Create comprehensive prompt for Imagen editing
            editing_prompt = f"""
{prompt}

Seamlessly integrate the product into the base scene at the masked location. 
Preserve all unmasked areas exactly as in the original image. 
Do not alter the product’s content, branding, or details. 
Blend only the edges to match the base scene’s lighting, perspective, and shadows. 
Ensure the product looks naturally placed while keeping the rest of the image unchanged.
            """
            
            # Create reference images using the Python SDK
            # First, save images to temporary files since SDK expects file paths
            import tempfile
            
            # Save base image to temp file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as base_temp:
                base_temp.write(base_image_bytes)
                base_temp_path = base_temp.name
            
            # Save mask image to temp file  
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as mask_temp:
                mask_temp.write(mask_bytes)
                mask_temp_path = mask_temp.name
            
            try:
                raw_ref = RawReferenceImage(
                    reference_image=GenAIImage.from_file(location=base_temp_path),
                    reference_id=0,
                )
                
                mask_ref = MaskReferenceImage(
                    reference_id=1,
                    reference_image=GenAIImage.from_file(location=mask_temp_path),
                    config=MaskReferenceConfig(
                        mask_mode="MASK_MODE_USER_PROVIDED",
                        mask_dilation=0.01,
                    ),
                )
                
                # Make the edit_image call using the Python SDK
                def _call_imagen():
                    return self.genai_client.models.edit_image(
                        model=self.imagen_edit_model,
                        prompt=prompt,
                        reference_images=[raw_ref, mask_ref],
                        config=EditImageConfig(
                            edit_mode="EDIT_MODE_INPAINT_INSERTION",
                        ),
                    )
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, _call_imagen)
                
                # Extract generated image data
                if not response.generated_images or len(response.generated_images) == 0:
                    raise Exception("No images generated by Imagen Editing API")
                
                generated_image = response.generated_images[0]
                image_data = generated_image.image.image_bytes
                
                logger.info(f"Generated image using {len(image_data)} bytes")
                
                # Upload to GCS and get signed URL
                render_url = await self._upload_to_gcs_and_get_signed_url(image_data)
                logger.info(f"Generated and uploaded image with Imagen Editing: {render_url}")
                return render_url
                
            finally:
                # Clean up temporary files
                import os
                try:
                    os.unlink(base_temp_path)
                    os.unlink(mask_temp_path)
                except:
                    pass  # Ignore cleanup errors
                
        except Exception as e:
            logger.error(f"Imagen Editing generation failed: {str(e)}")
            raise Exception(f"Failed to generate visualization with Imagen Editing: {str(e)}")
    
    async def visualize_product(self, request: VisualizeProductRequest) -> VisualizeProductResponse:
        """Visualize product in user photo using Vertex AI Imagen 3.0 Editing & Customization."""
        try:
            start_time = time.time()
            
            # Step 1: Use Gemini to infer optimal placement for mask generation
            logger.info("Inferring optimal placement using Gemini...")
            placement = await self._infer_placement_with_gemini(
                request.base_image_url,
                request.product_image_url,
                request.prompt
            )
            
            # Step 2: Generate the visualization using Imagen 3.0 Editing
            
            logger.info("Generating visualization with Vertex AI Imagen 3.0 Editing...")
            render_url = await self._generate_with_imagen_editing(
                request.base_image_url,
                request.product_image_url,
                placement,
                request.prompt
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            metadata = RenderMetadata(
                latency_ms=latency_ms,
                seed=None  # Imagen Editing doesn't use seeds
            )
            
            logger.info(f"Imagen 3.0 Editing visualization completed in {latency_ms}ms")
            
            return VisualizeProductResponse(
                render_url=render_url,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error visualizing product with Imagen 3.0 Editing: {str(e)}")
            raise
