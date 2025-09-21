import os
import logging
from typing import List, Optional, Dict, Any
import asyncio
import re

from google.cloud import vision
from google.cloud import storage

from models import (
    DetectedObject, BoundingBox, AnalyzeImageRequest, AnalyzeImageResponse
)
from style_analyzer import StyleAnalyzer

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """Service for analyzing images using Google Cloud Vision API and Vertex AI."""
    
    def __init__(self):
        self.vision_client = None
        self.storage_client = None
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.bucket_name = os.getenv("GCS_BUCKET", f"{self.project_id}-image-analysis")
        self.style_analyzer = StyleAnalyzer()
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Google Cloud clients."""
        try:
            # Initialize Vision API client
            self.vision_client = vision.ImageAnnotatorClient()
            
            # Initialize Storage client
            self.storage_client = storage.Client(project=self.project_id)
            
            logger.info(f"✅ Initialized clients for project: {self.project_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Cloud clients: {str(e)}")
            raise
    
    def _is_gcs_url(self, url: str) -> bool:
        """Check if URL is a Google Cloud Storage URL."""
        return url.startswith('gs://') or 'storage.googleapis.com' in url
    
    def _convert_to_gcs_uri(self, url: str) -> str:
        """Convert storage.googleapis.com URL to gs:// URI."""
        if url.startswith('gs://'):
            return url
        
        # Convert https://storage.googleapis.com/bucket/path to gs://bucket/path
        match = re.match(r'https?://storage\.googleapis\.com/([^/]+)/(.+)', url)
        if match:
            bucket, path = match.groups()
            return f"gs://{bucket}/{path}"
        
        return url  # Return as-is if not a GCS URL
    
    async def _create_vision_image(self, image_url: str) -> vision.Image:
        """Create Vision API image object"""
        if self._is_gcs_url(image_url):
            # Use GCS URI directly - no download needed!
            gcs_uri = self._convert_to_gcs_uri(image_url)
            return vision.Image(source=vision.ImageSource(gcs_image_uri=gcs_uri))
        else:
            # For non-GCS URLs, we still need to download
            # In production, consider uploading to GCS first
            logger.warning(f"Non-GCS URL detected: {image_url}. Consider using GCS for better performance.")
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return vision.Image(content=image_data)
                    else:
                        raise Exception(f"Failed to download image: HTTP {response.status}")
    
    def _extract_colors(self, image_properties) -> List[str]:
        """Extract dominant colors from image properties."""
        colors = []
        if image_properties and image_properties.dominant_colors:
            for color_info in image_properties.dominant_colors.colors:
                color = color_info.color
                # Convert RGB to hex (Vision API returns float values 0-1, convert to 0-255)
                red = int(color.red * 255) if color.red <= 1.0 else int(color.red)
                green = int(color.green * 255) if color.green <= 1.0 else int(color.green)
                blue = int(color.blue * 255) if color.blue <= 1.0 else int(color.blue)
                hex_color = f"#{red:02x}{green:02x}{blue:02x}"
                colors.append(hex_color)
        return colors[:5]  # Limit to top 5 colors
    
    async def analyze_image(self, request: AnalyzeImageRequest) -> AnalyzeImageResponse:
        """Analyze image for objects, scene type, styles, and colors."""
        try:
            # Create Vision API image object (preferring GCS URLs)
            vision_image = await self._create_vision_image(request.image_url)
            
            # Perform multiple analyses in parallel
            tasks = [
                asyncio.create_task(self._detect_objects(vision_image)),
                asyncio.create_task(self._detect_labels(vision_image)),
                asyncio.create_task(self._detect_image_properties(vision_image))
            ]
            
            objects, labels, image_properties = await asyncio.gather(*tasks)
            
            # Extract basic information
            colors = self._extract_colors(image_properties)
            label_descriptions = [label.description for label in labels]
            
            # Use StyleAnalyzer for intelligent style and scene detection
            style_analysis = await self.style_analyzer.analyze_styles_and_scene(
                labels=label_descriptions,
                colors=colors,
                context=request.context
            )
            
            return AnalyzeImageResponse(
                objects=objects,
                scene_type=style_analysis.get("scene_type"),
                styles=style_analysis.get("styles", []),
                colors=colors,
                tags=style_analysis.get("tags", label_descriptions[:10])
            )
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise
    
    async def _detect_objects(self, vision_image) -> List[DetectedObject]:
        """Detect objects in image using Vision API."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.vision_client.object_localization(image=vision_image)
            )
            
            objects = []
            for obj in response.localized_object_annotations:
                # Get bounding box
                vertices = obj.bounding_poly.normalized_vertices
                if vertices:
                    min_x = min(v.x for v in vertices)
                    min_y = min(v.y for v in vertices)
                    max_x = max(v.x for v in vertices)
                    max_y = max(v.y for v in vertices)
                    
                    bbox = BoundingBox(
                        x=min_x,
                        y=min_y,
                        w=max_x - min_x,
                        h=max_y - min_y
                    )
                    
                    objects.append(DetectedObject(
                        label=obj.name,
                        confidence=obj.score,
                        box=bbox
                    ))
            
            return objects
            
        except Exception as e:
            logger.error(f"Error detecting objects: {str(e)}")
            return []
    
    async def _detect_labels(self, vision_image):
        """Detect labels in image using Vision API."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.vision_client.label_detection(image=vision_image)
            )
            return response.label_annotations
        except Exception as e:
            logger.error(f"Error detecting labels: {str(e)}")
            return []
    
    async def _detect_image_properties(self, vision_image):
        """Detect image properties using Vision API."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.vision_client.image_properties(image=vision_image)
            )
            return response.image_properties_annotation
        except Exception as e:
            logger.error(f"Error detecting image properties: {str(e)}")
            return None 