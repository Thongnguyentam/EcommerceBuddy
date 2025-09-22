import logging
from typing import Dict, Any, Optional
from clients.image_assistant_client import ImageAssistantServiceClient

logger = logging.getLogger(__name__)

class ImageAssistantTools:
    """Tools wrapper for Image Assistant Service operations."""
    
    def __init__(self, client: ImageAssistantServiceClient):
        """Initialize Image Assistant tools.
        
        Args:
            client: Image Assistant Service gRPC client
        """
        self.client = client
    
    async def analyze_image(self, image_url: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an image for objects, scene type, styles, and colors.
        
        Args:
            image_url: URL of the image to analyze
            context: Optional context for better analysis
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            logger.info(f"🔍 Analyzing image: {image_url}")
            
            response = self.client.analyze_image(image_url=image_url, context=context)
            
            if not response.success:
                return {
                    "success": False,
                    "error": response.message,
                    "message": "Failed to analyze image"
                }
            
            # Convert objects to dictionaries
            objects_data = []
            for obj in response.objects:
                objects_data.append({
                    "label": obj.label,
                    "confidence": obj.confidence,
                    "bounding_box": {
                        "x": obj.box.x,
                        "y": obj.box.y,
                        "w": obj.box.w,
                        "h": obj.box.h
                    }
                })
            
            result = {
                "success": True,
                "analysis": {
                    "objects": objects_data,
                    "scene_type": response.scene_type,
                    "styles": list(response.styles),
                    "colors": list(response.colors),
                    "tags": list(response.tags)
                },
                "message": "Image analysis completed successfully"
            }
            
            logger.info(f"✅ Image analysis completed: {len(objects_data)} objects detected, scene: {response.scene_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Image analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Image analysis failed due to an unexpected error"
            }
    
    async def visualize_product(self, base_image_url: str, product_image_url: str, prompt: str) -> Dict[str, Any]:
        """Visualize a product in a user photo using AI-powered image generation.
        
        Args:
            base_image_url: URL of the base scene/room image
            product_image_url: URL of the product image
            prompt: Description of how to place the product (e.g., "Place this vase on the table")
            
        Returns:
            Dictionary containing the generated image URL and metadata
        """
        try:
            logger.info(f"🎨 Visualizing product placement: {prompt}")
            logger.info(f"   📸 Base scene: {base_image_url}")
            logger.info(f"   🏺 Product: {product_image_url}")
            
            response = self.client.visualize_product(
                base_image_url=base_image_url,
                product_image_url=product_image_url,
                prompt=prompt
            )
            
            if not response.success:
                return {
                    "success": False,
                    "error": response.message,
                    "message": "Failed to generate product visualization"
                }
            
            result = {
                "success": True,
                "visualization": {
                    "render_url": response.render_url,
                    "processing_time_ms": response.metadata.latency_ms,
                    "seed": response.metadata.seed if response.metadata.seed else None
                },
                "message": "Product visualization completed successfully"
            }
            
            logger.info(f"✅ Product visualization completed in {response.metadata.latency_ms}ms")
            logger.info(f"   🖼️ Result: {response.render_url}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Product visualization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Product visualization failed due to an unexpected error"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Image Assistant Service.
        
        Returns:
            Dictionary containing health status
        """
        try:
            is_healthy = self.client.health_check()
            
            if is_healthy:
                return {
                    "success": True,
                    "status": "healthy",
                    "message": "Image Assistant Service is running and accessible"
                }
            else:
                return {
                    "success": False,
                    "status": "unhealthy",
                    "message": "Image Assistant Service is not responding"
                }
                
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "message": "Health check failed due to an unexpected error"
            } 