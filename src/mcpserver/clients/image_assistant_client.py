import grpc
import logging
from typing import Optional

# Import the generated protobuf files
from genproto import imageassistant_pb2
from genproto import imageassistant_pb2_grpc

logger = logging.getLogger(__name__)

class ImageAssistantServiceClient:
    """Client for Image Assistant Service gRPC API."""
    
    def __init__(self, address: str = "imageassistantservice:8080"):
        """Initialize the Image Assistant Service client.
        
        Args:
            address: The gRPC server address (host:port)
        """
        self.address = address
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """Establish connection to the gRPC server."""
        try:
            self.channel = grpc.insecure_channel(self.address)
            self.stub = imageassistant_pb2_grpc.ImageAssistantServiceStub(self.channel)
            logger.info(f"✅ Connected to Image Assistant Service at {self.address}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Image Assistant Service: {e}")
            raise
    
    def analyze_image(self, image_url: str, context: Optional[str] = None) -> imageassistant_pb2.AnalyzeImageResponse:
        """Analyze an image for objects, scene type, styles, and colors.
        
        Args:
            image_url: URL of the image to analyze
            context: Optional context for analysis
            
        Returns:
            AnalyzeImageResponse with analysis results
        """
        try:
            logger.info(f"🔍 Analyzing image: {image_url}")
            
            request = imageassistant_pb2.AnalyzeImageRequest(
                image_url=image_url,
                context=context or ""
            )
            
            response = self.stub.AnalyzeImage(request)
            return response
            
        except Exception as e:
            logger.error(f"❌ Image analysis failed: {e}")
            # Return error response
            return imageassistant_pb2.AnalyzeImageResponse(
                success=False,
                message=str(e)
            )
    
    def visualize_product(self, base_image_url: str, product_image_url: str, prompt: str) -> imageassistant_pb2.VisualizeProductResponse:
        """Visualize a product in a user photo using AI.
        
        Args:
            base_image_url: URL of the base scene image
            product_image_url: URL of the product image
            prompt: Description of how to place the product
            
        Returns:
            VisualizeProductResponse with generated image URL
        """
        try:
            logger.info(f"🎨 Visualizing product placement: {prompt}")
            
            request = imageassistant_pb2.VisualizeProductRequest(
                base_image_url=base_image_url,
                product_image_url=product_image_url,
                prompt=prompt
            )
            
            response = self.stub.VisualizeProduct(request)
            return response
            
        except Exception as e:
            logger.error(f"❌ Product visualization failed: {e}")
            # Return error response
            return imageassistant_pb2.VisualizeProductResponse(
                success=False,
                message=str(e)
            )
    
    def health_check(self) -> bool:
        """Check if the service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            request = imageassistant_pb2.HealthCheckRequest()
            response = self.stub.Check(request)
            return response.status == imageassistant_pb2.HealthCheckResponse.ServingStatus.SERVING
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    def close(self):
        """Close the gRPC connection."""
        if self.channel:
            self.channel.close()
            logger.info("🔌 Disconnected from Image Assistant Service") 