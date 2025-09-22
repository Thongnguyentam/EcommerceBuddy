import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from tools.image_assistant_tools import ImageAssistantTools

logger = logging.getLogger(__name__)

# Global tools instance
image_assistant_tools: Optional[ImageAssistantTools] = None

def set_image_assistant_tools(tools: ImageAssistantTools):
    """Set the global image assistant tools instance."""
    global image_assistant_tools
    image_assistant_tools = tools

# Create router
router = APIRouter(prefix="/image-assistant", tags=["image-assistant"])

# Request models
class AnalyzeImageRequest(BaseModel):
    image_url: str = Field(..., description="URL of the image to analyze")
    context: Optional[str] = Field(None, description="Optional context for better analysis")

class VisualizeProductRequest(BaseModel):
    base_image_url: str = Field(..., description="URL of the base scene/room image")
    product_image_url: str = Field(..., description="URL of the product image")
    prompt: str = Field(..., description="Description of how to place the product")

# Endpoints
@router.post("/analyze-image")
async def analyze_image_endpoint(request: AnalyzeImageRequest) -> Dict[str, Any]:
    """Analyze an image for objects, scene type, styles, and colors.
    
    This endpoint uses Google Cloud Vision API combined with Gemini-powered 
    style intelligence to provide comprehensive image analysis.
    """
    if not image_assistant_tools:
        raise HTTPException(status_code=503, detail="Image Assistant Service not available")
    
    try:
        result = await image_assistant_tools.analyze_image(
            image_url=request.image_url,
            context=request.context
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Analysis failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Image analysis endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/visualize-product")
async def visualize_product_endpoint(request: VisualizeProductRequest) -> Dict[str, Any]:
    """Visualize a product in a user photo using AI-powered image generation.
    
    This endpoint uses Gemini 2.5 Flash Image Preview (Nano Banana) to create 
    photorealistic product placements with intelligent scene analysis and 
    realistic lighting integration.
    """
    if not image_assistant_tools:
        raise HTTPException(status_code=503, detail="Image Assistant Service not available")
    
    try:
        result = await image_assistant_tools.visualize_product(
            base_image_url=request.base_image_url,
            product_image_url=request.product_image_url,
            prompt=request.prompt
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Visualization failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Product visualization endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check_endpoint() -> Dict[str, Any]:
    """Check the health of the Image Assistant Service."""
    if not image_assistant_tools:
        raise HTTPException(status_code=503, detail="Image Assistant Service not available")
    
    try:
        result = await image_assistant_tools.health_check()
        
        if not result["success"]:
            raise HTTPException(status_code=503, detail=result.get("message", "Service unhealthy"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Health check endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# MCP Tool endpoints (for direct tool access)
@router.post("/tools/analyze-image")
async def analyze_image_tool(request: AnalyzeImageRequest) -> Dict[str, Any]:
    """MCP Tool: Analyze image for objects, scene type, styles, and colors."""
    return await analyze_image_endpoint(request)

@router.post("/tools/visualize-product")
async def visualize_product_tool(request: VisualizeProductRequest) -> Dict[str, Any]:
    """MCP Tool: Visualize product in user photo using AI."""
    return await visualize_product_endpoint(request) 