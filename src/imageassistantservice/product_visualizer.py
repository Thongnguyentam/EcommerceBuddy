import os
import logging
import asyncio
import time
import json
import uuid
from typing import Optional
from datetime import datetime, timedelta
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google import genai
from google.cloud import storage
from google.genai.types import HttpOptions

from models import (
    AnalyzeImageResponse, VisualizeProductRequest, VisualizeProductResponse, 
    ProductPlacement, RenderMetadata, Position
)

logger = logging.getLogger(__name__)

class ProductVisualizer:
    """Service for visualizing products in user photos using Vertex AI and Gemini."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.renders_bucket = os.getenv("GCS_RENDERS_BUCKET")
        self.gemini_client = None
        self.imagen_model = None
        self.storage_client = None
        
        # Initialize Vertex AI
        if self.project_id:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                
                # Initialize Imagen model for image generation
                self.imagen_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
                logger.info("✅ Initialized Vertex AI Imagen model")
                
                # Initialize Gemini for placement inference
                self.gemini_client = genai.Client(vertexai=True, project=self.project_id, location=self.location)
                logger.info("✅ Initialized Gemini client for placement inference")
                
                # Initialize GCS client for render storage
                self.storage_client = storage.Client()
                logger.info("✅ Initialized GCS client for render storage")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vertex AI services: {str(e)}")
    
    async def _infer_placement_with_gemini(self, base_image_url: str, product_image_url: str, 
                                         context: Optional[str] = None) -> ProductPlacement:
        """Use Gemini to intelligently infer product placement."""
        # if not self.gemini_client:
        #     raise Exception("Gemini client not available. Please ensure GEMINI_API_KEY is set and valid.")
        
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
    
    async def _upload_to_gcs_and_get_signed_url(self, image_data: bytes) -> str:
        """Upload generated image to GCS renders bucket and return a signed URL."""
        if not self.storage_client or not self.renders_bucket:
            raise Exception("GCS storage not configured. Please ensure GCS_RENDERS_BUCKET is set.")
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"renders/{timestamp}_{unique_id}.jpg"
            
            # Get bucket and create blob
            bucket = self.storage_client.bucket(self.renders_bucket)
            blob = bucket.blob(filename)
            
            # Upload image data
            blob.upload_from_string(image_data, content_type='image/jpeg')
            logger.info(f"✅ Uploaded render to GCS: gs://{self.renders_bucket}/{filename}")
            
            # Generate signed URL (valid for 1 hour)
            signed_url = blob.generate_signed_url(
                expiration=datetime.utcnow() + timedelta(hours=1),
                method='GET'
            )
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {str(e)}")
            raise Exception(f"Failed to upload generated image to storage: {str(e)}")
    
    async def _generate_with_imagen(self, base_image_url: str, product_image_url: str, 
                                  placement: ProductPlacement, prompt: str) -> str:
        """Generate product visualization using Vertex AI Imagen."""
        if not self.imagen_model:
            raise Exception("Imagen model not available. Please ensure Vertex AI is properly configured and the project has access to Imagen.")
        
        try:
            # Create comprehensive prompt for Imagen
            imagen_prompt = f"""
            {prompt}
            
            Placement instructions:
            - Position the product at coordinates ({placement.position.x:.2f}, {placement.position.y:.2f})
            - Scale the product to {placement.scale:.2f} relative size
            - Rotate the product {placement.rotation:.1f} degrees
            - Ensure realistic lighting, shadows, and perspective
            - Maintain photorealistic quality and natural integration
            - Preserve the original scene's atmosphere and style
            
            Base scene: {base_image_url}
            Product: {product_image_url}
            """
            
            # Generate image using Imagen
            def _call_imagen():
                return self.imagen_model.generate_images(
                    prompt=imagen_prompt,
                    number_of_images=1,
                    guidance_scale=7.5,
                    # Remove seed parameter as it's not supported with watermarks
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call_imagen)
            
            # Extract the generated image and upload to GCS
            if response and len(response.images) > 0:
                generated_image = response.images[0]
                
                # Convert the generated image to bytes (assuming it has image data)
                # Note: The exact method depends on the Imagen response format
                image_data = generated_image._image_bytes if hasattr(generated_image, '_image_bytes') else generated_image.data
                
                # Upload to GCS and get signed URL
                render_url = await self._upload_to_gcs_and_get_signed_url(image_data)
                logger.info(f"Generated and uploaded image with Imagen: {render_url}")
                return render_url
            else:
                raise Exception("No images generated by Imagen")
                
        except Exception as e:
            logger.error(f"Imagen generation failed: {str(e)}")
            raise Exception(f"Failed to generate visualization with Imagen: {str(e)}")
    
    async def visualize_product(self, request: VisualizeProductRequest) -> VisualizeProductResponse:
        """Visualize product in user photo using Gemini + Vertex AI Imagen."""
        try:
            start_time = time.time()
            
            # Step 1: Always use Gemini to infer optimal placement
            logger.info("Inferring optimal placement using Gemini...")
            placement = await self._infer_placement_with_gemini(
                request.base_image_url,
                request.product_image_url,
                request.prompt
            )
            
            # Step 2: Generate the visualization using Imagen
            prompt = request.prompt or f"""
            Seamlessly integrate the product into the base scene. 
            Make it look natural and realistic, matching the lighting and perspective 
            of the original scene. Ensure the product fits naturally into the environment.
            """
            
            logger.info("Generating visualization with Vertex AI Imagen...")
            render_url = await self._generate_with_imagen(
                request.base_image_url,
                request.product_image_url,
                placement,
                prompt
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            metadata = RenderMetadata(
                latency_ms=latency_ms,
                seed=None  # Seed not used with Imagen watermarks
            )
            
            logger.info(f"Product visualization completed in {latency_ms}ms")
            
            return VisualizeProductResponse(
                render_url=render_url,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error visualizing product: {str(e)}")
            raise
