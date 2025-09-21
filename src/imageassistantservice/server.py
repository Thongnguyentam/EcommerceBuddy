#!/usr/bin/env python3

import os
import sys
import logging
import asyncio

from dotenv import load_dotenv
import grpc

# Load environment variables from .env file
load_dotenv()
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from genproto import imageassistant_pb2, imageassistant_pb2_grpc
from image_analyzer import ImageAnalyzer
from product_visualizer import ProductVisualizer
from models import AnalyzeImageRequest, VisualizeProductRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImageAssistantServicer(imageassistant_pb2_grpc.ImageAssistantServiceServicer):
    """gRPC servicer for image assistant operations."""
    
    def __init__(self):
        self.image_analyzer = ImageAnalyzer()
        self.product_visualizer = ProductVisualizer()
    
    def _set_error(self, context, code, details):
        """Set error code and details if context is available."""
        if context:
            context.set_code(code)
            context.set_details(details)
    
    def _convert_to_proto_objects(self, objects):
        """Convert Pydantic objects to protobuf objects."""
        proto_objects = []
        for obj in objects:
            proto_box = imageassistant_pb2.BoundingBox(
                x=obj.box.x,
                y=obj.box.y,
                w=obj.box.w,
                h=obj.box.h
            )
            proto_obj = imageassistant_pb2.DetectedObject(
                label=obj.label,
                confidence=obj.confidence,
                box=proto_box
            )
            proto_objects.append(proto_obj)
        return proto_objects
    

    
    async def AnalyzeImage(self, request, context):
        """Analyze image for objects, scene type, styles, colors."""
        try:
            # Convert protobuf request to Pydantic model
            analyze_request = AnalyzeImageRequest(
                image_url=request.image_url,
                context=request.context if request.context else None
            )
            
            # Analyze image
            result = await self.image_analyzer.analyze_image(analyze_request)
            
            # Convert to protobuf response
            proto_objects = self._convert_to_proto_objects(result.objects)
            
            return imageassistant_pb2.AnalyzeImageResponse(
                objects=proto_objects,
                scene_type=result.scene_type or "",
                styles=result.styles or [],
                colors=result.colors or [],
                tags=result.tags or [],
                success=True,
                message="Image analyzed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return imageassistant_pb2.AnalyzeImageResponse(
                success=False,
                message=str(e)
            )
    
    async def VisualizeProduct(self, request, context):
        """Visualize product inside a user photo using Gemini placement inference."""
        try:
            # Convert protobuf request to Pydantic model (no placement - Gemini handles it)
            visualize_request = VisualizeProductRequest(
                base_image_url=request.base_image_url,
                product_image_url=request.product_image_url,
                prompt=request.prompt if request.prompt else None
            )
            
            # Visualize product
            result = await self.product_visualizer.visualize_product(visualize_request)
            
            # Convert to protobuf response
            proto_metadata = None
            if result.metadata:
                proto_metadata = imageassistant_pb2.RenderMetadata(
                    latency_ms=result.metadata.latency_ms or 0,
                    seed=result.metadata.seed or 0
                )
            
            return imageassistant_pb2.VisualizeProductResponse(
                render_url=result.render_url,
                metadata=proto_metadata,
                success=True,
                message="Product visualization completed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error visualizing product: {str(e)}")
            self._set_error(context, grpc.StatusCode.INTERNAL, f"Internal server error: {str(e)}")
            return imageassistant_pb2.VisualizeProductResponse(
                success=False,
                message=str(e)
            )
    
    async def Check(self, request, context):
        """Health check endpoint."""
        return imageassistant_pb2.HealthCheckResponse(
            status=imageassistant_pb2.HealthCheckResponse.ServingStatus.SERVING
        )

def create_grpc_server():
    """Create and configure gRPC server."""
    # Create server with thread pool
    server = grpc.aio.server()
    
    # Add servicer
    image_servicer = ImageAssistantServicer()
    imageassistant_pb2_grpc.add_ImageAssistantServiceServicer_to_server(image_servicer, server)
    
    # Add health service
    hs = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(hs, server)
    hs.set("", health_pb2.HealthCheckResponse.SERVING)              # overall
    hs.set("imageassistant.ImageAssistantService", health_pb2.HealthCheckResponse.SERVING)  # named
    
    # Configure server address
    port = os.getenv("PORT", "8080")
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    
    logger.info(f"🚀 Starting Image Assistant Service gRPC server on {listen_addr}")
    
    return server

async def serve():
    """Start the gRPC server."""
    server = create_grpc_server()
    
    # Start server
    await server.start()
    logger.info("✅ Image Assistant Service gRPC server started successfully")
    
    # Wait for server termination
    try:
        await server.wait_for_termination()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await server.stop(grace=5)  # Await this to ensure shutdown is clean

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {str(e)}")
        sys.exit(1) 