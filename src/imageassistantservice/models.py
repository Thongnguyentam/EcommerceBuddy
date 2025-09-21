from typing import Optional, List, Dict
from pydantic import BaseModel, Field, HttpUrl

class BoundingBox(BaseModel):
    """Bounding box coordinates for detected objects."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate") 
    w: float = Field(..., description="Width")
    h: float = Field(..., description="Height")

class DetectedObject(BaseModel):
    """Model for detected object in image analysis."""
    label: str = Field(..., description="Object label/class")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    box: BoundingBox = Field(..., description="Bounding box coordinates")

class Position(BaseModel):
    """Position coordinates for product placement."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")

class ProductPlacement(BaseModel):
    """Configuration for product placement in visualization."""
    position: Position = Field(..., description="Position coordinates")
    scale: float = Field(1.0, gt=0, description="Scale factor")
    rotation: Optional[float] = Field(0.0, description="Rotation angle in degrees")
    occlusion_mask_url: Optional[str] = Field(None, description="URL to occlusion mask")

class RenderMetadata(BaseModel):
    """Metadata for rendered visualization."""
    latency_ms: Optional[int] = Field(None, description="Processing latency in milliseconds")
    seed: Optional[int] = Field(None, description="Random seed used for generation")

class AnalyzeImageRequest(BaseModel):
    """Model for image analysis request."""
    image_url: str = Field(..., description="URL of image to analyze")
    context: Optional[str] = Field(None, description="Additional context for analysis")

class AnalyzeImageResponse(BaseModel):
    """Model for image analysis response."""
    objects: List[DetectedObject] = Field(default=[], description="Detected objects")
    scene_type: Optional[str] = Field(None, description="Scene type classification")
    styles: Optional[List[str]] = Field(default=[], description="Detected styles")
    colors: Optional[List[str]] = Field(default=[], description="Dominant colors")
    tags: Optional[List[str]] = Field(default=[], description="General tags")

class VisualizeProductRequest(BaseModel):
    """Model for product visualization request."""
    base_image_url: str = Field(..., description="Base image URL")
    product_image_url: str = Field(..., description="Product image URL")
    placement: Optional[ProductPlacement] = Field(None, description="Product placement configuration")
    prompt: Optional[str] = Field(None, description="Additional prompt for visualization")

class VisualizeProductResponse(BaseModel):
    """Model for product visualization response."""
    render_url: str = Field(..., description="URL of rendered visualization")
    metadata: Optional[RenderMetadata] = Field(None, description="Render metadata")

class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str
    service: str 